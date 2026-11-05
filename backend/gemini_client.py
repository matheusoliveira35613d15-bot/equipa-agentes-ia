import re
import time

from google import genai
from google.genai import errors, types

from . import config

_TENTATIVAS_SOBRECARGA = 8
_ESPERA_MAXIMA = 30


def _tempo_de_espera(erro: errors.APIError, tentativa: int) -> float:
    """Tenta usar o retryDelay sugerido pela API (comum no erro 429 de quota); caso
    contrário, usa um atraso crescente (até _ESPERA_MAXIMA) para absorver picos de
    sobrecarga (erro 503) mais longos."""
    try:
        detalhes = erro.details.get("error", {}).get("details", [])
        for item in detalhes:
            if item.get("@type", "").endswith("RetryInfo"):
                segundos = re.match(r"([\d.]+)", item.get("retryDelay", ""))
                if segundos:
                    return min(float(segundos.group(1)) + 1, _ESPERA_MAXIMA)
    except (AttributeError, TypeError):
        pass
    return min(5 * (tentativa + 1), _ESPERA_MAXIMA)

_client = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY não configurada. Copie .env.example para .env e preencha a chave "
                "(gerada em aistudio.google.com/apikey)."
            )
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def _schema_para_gemini(schema: dict) -> dict:
    """Converte o nosso JSON Schema (tipos em minúsculas) para o formato que o Gemini espera
    (tipos em maiúsculas, ao estilo OpenAPI)."""
    convertido = {"type": schema["type"].upper()}
    if "description" in schema:
        convertido["description"] = schema["description"]
    if "enum" in schema:
        convertido["enum"] = schema["enum"]
    if "properties" in schema:
        convertido["properties"] = {
            nome: _schema_para_gemini(sub) for nome, sub in schema["properties"].items()
        }
    if "items" in schema:
        convertido["items"] = _schema_para_gemini(schema["items"])
    if "required" in schema:
        convertido["required"] = schema["required"]
    return convertido


def call_tool(system_prompt: str, user_prompt: str, tool_name: str, schema: dict) -> dict:
    """Pede ao modelo uma resposta estruturada através de function calling, em vez de JSON em
    texto livre (evita falhas de parsing quando o conteúdo gerado tem aspas/quebras de linha)."""
    client = get_client()
    tool = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name=tool_name,
                description="Entrega a resposta estruturada pedida.",
                parameters=_schema_para_gemini(schema),
            )
        ]
    )
    generate_config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=config.MAX_TOKENS,
        tools=[tool],
        tool_config=types.ToolConfig(function_calling_config=types.FunctionCallingConfig(mode="ANY")),
    )

    response = None
    for tentativa in range(_TENTATIVAS_SOBRECARGA):
        try:
            response = client.models.generate_content(
                model=config.MODEL, contents=user_prompt, config=generate_config
            )
            break
        except errors.APIError as erro:
            if erro.code not in (429, 503) or tentativa == _TENTATIVAS_SOBRECARGA - 1:
                raise
            time.sleep(_tempo_de_espera(erro, tentativa))

    candidato = response.candidates[0] if response.candidates else None
    if candidato is not None and candidato.finish_reason == "MAX_TOKENS":
        raise ValueError(
            "A resposta do modelo foi cortada por exceder o limite de tokens (GEMINI_MAX_TOKENS no .env). "
            "Tente um pedido mais simples ou aumente esse limite."
        )

    if candidato is not None and candidato.content and candidato.content.parts:
        for part in candidato.content.parts:
            if part.function_call is not None:
                return dict(part.function_call.args)

    raise ValueError("O modelo não devolveu uma resposta estruturada (function call).")
