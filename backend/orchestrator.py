import asyncio
import json
from datetime import datetime
from pathlib import Path

from fastapi import WebSocket

from . import config
from .teams import REPORT_TEAM, SOFTWARE_TEAM
from .tools import code_runner, docx_export, zipper


async def enviar(ws: WebSocket, **evento):
    await ws.send_json(evento)


_HEARTBEAT_SEGUNDOS = 15


async def _com_heartbeat(ws: WebSocket, agente: str, coro):
    """Corre uma chamada (potencialmente longa, por causa das novas tentativas do nível
    gratuito) enquanto envia sinais periódicos pelo WebSocket — evita que proxies (ex: Render)
    fechem a ligação por inatividade durante esperas longas, e mostra ao utilizador que a app
    continua a trabalhar."""
    tarefa = asyncio.ensure_future(coro)
    try:
        while True:
            concluidas, _ = await asyncio.wait({tarefa}, timeout=_HEARTBEAT_SEGUNDOS)
            if tarefa in concluidas:
                return tarefa.result()
            await enviar(ws, tipo="heartbeat", agente=agente)
    except BaseException:
        tarefa.cancel()
        raise


def slugify(texto: str, limite: int = 40) -> str:
    seguro = "".join(c if c.isalnum() or c in " -_" else "" for c in texto)
    seguro = seguro.strip().replace(" ", "-").lower()
    return seguro[:limite] or "pedido"


async def pedir_clarificacao(ws: WebSocket, perguntas: list[str]) -> str:
    await enviar(ws, tipo="clarificacao", perguntas=perguntas)
    resposta = await ws.receive_json()
    respostas = resposta.get("respostas", [])
    return "\n".join(f"P: {p}\nR: {r}" for p, r in zip(perguntas, respostas))


def escrever_ficheiros(workspace: Path, ficheiros: list[dict]):
    for f in ficheiros:
        caminho = workspace / f["caminho"]
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(f["conteudo"], encoding="utf-8")


async def correr(ws: WebSocket, equipa_tipo: str, pedido: str):
    run_id = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{slugify(pedido)}"
    workspace = config.WORKSPACES_DIR / run_id
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "_meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "pedido": pedido,
                "equipa_tipo": equipa_tipo,
                "criado_em": datetime.now().isoformat(),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    if equipa_tipo == "software":
        await correr_software(ws, pedido, workspace, run_id)
    else:
        await correr_relatorio(ws, pedido, workspace, run_id)


async def correr_software(ws: WebSocket, pedido: str, workspace: Path, run_id: str):
    equipa = SOFTWARE_TEAM

    await enviar(ws, tipo="status", agente="Coordenador", estado="a trabalhar")
    decisao = await _com_heartbeat(ws, "Coordenador", asyncio.to_thread(equipa["coordenador"].responder_json, pedido))

    if decisao.get("clarificar"):
        contexto = await pedir_clarificacao(ws, decisao["perguntas"])
        await enviar(ws, tipo="status", agente="Coordenador", estado="a trabalhar")
        decisao = await _com_heartbeat(
            ws,
            "Coordenador",
            asyncio.to_thread(
                equipa["coordenador"].responder_json,
                f"Pedido original: {pedido}\n\n{contexto}\n\n"
                f"Responde agora com a especificação final (clarificar deve ser false).",
            ),
        )

    linguagem = decisao.get("linguagem", "python")
    especificacao = decisao.get("especificacao", pedido)
    await enviar(ws, tipo="mensagem", agente="Coordenador", conteudo=especificacao)
    await enviar(ws, tipo="status", agente="Coordenador", estado="concluído")

    await enviar(ws, tipo="status", agente="Programador", estado="a trabalhar")
    resultado = await _com_heartbeat(
        ws,
        "Programador",
        asyncio.to_thread(
            equipa["programador"].responder_json,
            f"Pedido original: {pedido}\n\nTecnologia: {linguagem}\n\nEspecificação do Coordenador:\n{especificacao}",
        ),
    )
    ficheiros = resultado.get("ficheiros", [])
    if not ficheiros:
        raise RuntimeError("O Programador não produziu nenhum ficheiro.")
    escrever_ficheiros(workspace, ficheiros)
    await enviar(ws, tipo="mensagem", agente="Programador", conteudo=f"{len(ficheiros)} ficheiro(s) escrito(s).")
    await enviar(ws, tipo="ficheiros", ficheiros=[f["caminho"] for f in ficheiros])
    await enviar(ws, tipo="status", agente="Programador", estado="concluído")

    testadores = {
        "python": (code_runner.testar_python, "main.py"),
        "node": (code_runner.testar_node, "server.js"),
        "php": (code_runner.testar_php, "index.php"),
    }

    for iteracao in range(config.MAX_REVIEW_ITERATIONS):
        await enviar(ws, tipo="status", agente="Revisor", estado="a trabalhar")
        codigo_concat = "\n\n".join(f"### {f['caminho']}\n{f['conteudo']}" for f in ficheiros)
        revisao = await _com_heartbeat(ws, "Revisor", asyncio.to_thread(equipa["revisor"].responder_json, codigo_concat))
        await enviar(ws, tipo="mensagem", agente="Revisor", conteudo=revisao.get("comentarios", ""))
        await enviar(ws, tipo="status", agente="Revisor", estado="concluído")

        teste_ok, teste_feedback = True, "Página estática: sem execução automática, avaliação baseada na revisão."
        testador_info = testadores.get(linguagem)
        if testador_info:
            testar_fn, nome_padrao = testador_info
            await enviar(ws, tipo="status", agente="Testador", estado="a trabalhar")
            principal = next(
                (f["caminho"] for f in ficheiros if f["caminho"] == nome_padrao),
                ficheiros[0]["caminho"],
            )
            teste_ok, teste_feedback = await asyncio.to_thread(testar_fn, workspace, principal)
            await enviar(ws, tipo="mensagem", agente="Testador", conteudo=teste_feedback)
            await enviar(ws, tipo="status", agente="Testador", estado="concluído")

        if revisao.get("aprovado", True) and teste_ok:
            break
        if iteracao == config.MAX_REVIEW_ITERATIONS - 1:
            break

        await enviar(ws, tipo="status", agente="Programador", estado="a corrigir")
        feedback = (
            f"Tecnologia: {linguagem}\n\n"
            f"Comentários do Revisor: {revisao.get('comentarios', '')}\n\n"
            f"Resultado dos testes: {teste_feedback}\n\n"
            f"Corrige os ficheiros e devolve-os completos."
        )
        resultado = await _com_heartbeat(ws, "Programador", asyncio.to_thread(equipa["programador"].responder_json, feedback))
        ficheiros = resultado.get("ficheiros", ficheiros)
        escrever_ficheiros(workspace, ficheiros)
        await enviar(
            ws, tipo="mensagem", agente="Programador", conteudo=f"Correção aplicada ({len(ficheiros)} ficheiro(s))."
        )
        await enviar(ws, tipo="status", agente="Programador", estado="concluído")

    zip_path = zipper.zip_pasta(workspace, workspace.parent / run_id)
    await enviar(ws, tipo="concluido", run_id=run_id, download=f"/download/{zip_path.name}")


async def correr_relatorio(ws: WebSocket, pedido: str, workspace: Path, run_id: str):
    equipa = REPORT_TEAM

    await enviar(ws, tipo="status", agente="Coordenador", estado="a trabalhar")
    decisao = await _com_heartbeat(ws, "Coordenador", asyncio.to_thread(equipa["coordenador"].responder_json, pedido))

    if decisao.get("clarificar"):
        contexto = await pedir_clarificacao(ws, decisao["perguntas"])
        await enviar(ws, tipo="status", agente="Coordenador", estado="a trabalhar")
        decisao = await _com_heartbeat(
            ws,
            "Coordenador",
            asyncio.to_thread(
                equipa["coordenador"].responder_json,
                f"Pedido original: {pedido}\n\n{contexto}\n\n"
                f"Responde agora com o esboço final (clarificar deve ser false).",
            ),
        )

    titulo = decisao.get("titulo", "Relatório")
    seccoes = decisao.get("seccoes", ["Introdução", "Desenvolvimento", "Conclusão"])
    await enviar(ws, tipo="mensagem", agente="Coordenador", conteudo=f"{titulo} — secções: {', '.join(seccoes)}")
    await enviar(ws, tipo="status", agente="Coordenador", estado="concluído")

    partes_md = [f"# {titulo}\n"]
    for seccao in seccoes:
        await enviar(ws, tipo="status", agente="Analista", estado=f"a preparar: {seccao}")
        notas = await _com_heartbeat(
            ws,
            "Analista",
            asyncio.to_thread(
                equipa["analista"].responder_json,
                f"Pedido original: {pedido}\n\nSecção a preparar: {seccao}",
            ),
        )
        await enviar(ws, tipo="status", agente="Redator", estado=f"a escrever: {seccao}")
        texto = await _com_heartbeat(
            ws,
            "Redator",
            asyncio.to_thread(
                equipa["redator"].responder_json,
                f"Escreve a secção '{seccao}' em markdown.\n\nNotas do Analista:\n{notas.get('notas', '')}",
            ),
        )
        partes_md.append(texto.get("texto_markdown", f"## {seccao}\n"))
        await enviar(ws, tipo="mensagem", agente="Redator", conteudo=f"Secção '{seccao}' escrita.")

    await enviar(ws, tipo="status", agente="Analista", estado="concluído")
    await enviar(ws, tipo="status", agente="Redator", estado="concluído")

    documento_md = "\n\n".join(partes_md)

    for iteracao in range(config.MAX_REVIEW_ITERATIONS):
        await enviar(ws, tipo="status", agente="Revisor", estado="a trabalhar")
        revisao = await _com_heartbeat(ws, "Revisor", asyncio.to_thread(equipa["revisor"].responder_json, documento_md))
        await enviar(ws, tipo="mensagem", agente="Revisor", conteudo=revisao.get("comentarios", ""))
        await enviar(ws, tipo="status", agente="Revisor", estado="concluído")

        if revisao.get("aprovado", True) or iteracao == config.MAX_REVIEW_ITERATIONS - 1:
            break

        await enviar(ws, tipo="status", agente="Redator", estado="a corrigir")
        revisao_texto = await _com_heartbeat(
            ws,
            "Redator",
            asyncio.to_thread(
                equipa["redator"].responder_json,
                "Edita o relatório completo abaixo de acordo com os comentários do revisor. "
                "Devolve o documento inteiro revisto em 'texto_markdown'.\n\n"
                f"Comentários: {revisao.get('comentarios', '')}\n\nDocumento atual:\n{documento_md}",
            ),
        )
        documento_md = revisao_texto.get("texto_markdown", documento_md)
        await enviar(ws, tipo="status", agente="Redator", estado="concluído")

    md_path = workspace / "relatorio.md"
    md_path.write_text(documento_md, encoding="utf-8")
    docx_path = workspace / "relatorio.docx"
    docx_export.markdown_para_docx(documento_md, docx_path)
    await enviar(ws, tipo="ficheiros", ficheiros=["relatorio.md", "relatorio.docx"])

    zip_path = zipper.zip_pasta(workspace, workspace.parent / run_id)
    await enviar(ws, tipo="concluido", run_id=run_id, download=f"/download/{zip_path.name}")
