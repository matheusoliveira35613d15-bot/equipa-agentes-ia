import asyncio
import json
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from . import config, orchestrator
from .teams import SOFTWARE_TEAM
from .tools import preview_runner, zipper

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

_security = HTTPBasic(auto_error=False)


async def exigir_autenticacao(credenciais: HTTPBasicCredentials | None = Depends(_security)) -> None:
    """Protege a app com utilizador/password quando APP_USERNAME e APP_PASSWORD estão definidos
    (ex: quando a app está publicada online). Em uso local, sem essas variáveis, fica aberta."""
    if not config.APP_USERNAME or not config.APP_PASSWORD:
        return
    utilizador_ok = credenciais is not None and secrets.compare_digest(credenciais.username, config.APP_USERNAME)
    password_ok = credenciais is not None and secrets.compare_digest(credenciais.password, config.APP_PASSWORD)
    if not (utilizador_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
            headers={"WWW-Authenticate": "Basic"},
        )


app = FastAPI(dependencies=[Depends(exigir_autenticacao)])
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


def _workspace_de(run_id: str) -> Path | None:
    workspace = (config.WORKSPACES_DIR / run_id).resolve()
    if config.WORKSPACES_DIR.resolve() not in workspace.parents or not workspace.is_dir():
        return None
    return workspace


def _ler_meta(workspace: Path) -> dict:
    caminho = workspace / "_meta.json"
    if caminho.exists():
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {}


@app.get("/")
async def index():
    return HTMLResponse((FRONTEND_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/download/{filename}")
async def download(filename: str):
    destino = (config.WORKSPACES_DIR / filename).resolve()
    if config.WORKSPACES_DIR.resolve() not in destino.parents or not destino.exists():
        return HTMLResponse("Ficheiro não encontrado.", status_code=404)
    return FileResponse(destino, filename=filename)


@app.post("/preview/{run_id}")
async def preview(run_id: str):
    workspace = _workspace_de(run_id)
    if workspace is None:
        return JSONResponse({"erro": "Execução não encontrada."}, status_code=404)

    deteccao = preview_runner.detectar(workspace)
    if deteccao is None:
        return JSONResponse({"erro": "Nada para pré-visualizar nesta execução."}, status_code=404)

    linguagem, principal = deteccao
    if linguagem == "html":
        return {"url": f"/preview-html/{run_id}/index.html"}

    try:
        resultado = await asyncio.to_thread(preview_runner.iniciar, run_id, workspace, linguagem, principal)
    except Exception as e:
        return JSONResponse({"erro": str(e)}, status_code=500)
    return resultado


@app.get("/execucoes")
async def listar_execucoes():
    execucoes = []
    for item in sorted(config.WORKSPACES_DIR.iterdir(), reverse=True):
        if not item.is_dir():
            continue
        meta = _ler_meta(item)
        deteccao = preview_runner.detectar(item)
        zip_path = item.parent / f"{item.name}.zip"
        execucoes.append(
            {
                "run_id": item.name,
                "pedido": meta.get("pedido") or item.name.split("_", 2)[-1].replace("-", " "),
                "equipa_tipo": meta.get("equipa_tipo") or ("software" if deteccao else "relatorio"),
                "criado_em": meta.get("criado_em"),
                "editavel": deteccao is not None,
                "download": f"/download/{zip_path.name}" if zip_path.exists() else None,
            }
        )
    return execucoes


@app.post("/editar/{run_id}")
async def editar(run_id: str, request: Request):
    workspace = _workspace_de(run_id)
    if workspace is None:
        return JSONResponse({"erro": "Execução não encontrada."}, status_code=404)

    corpo = await request.json()
    pedido_edicao = (corpo or {}).get("pedido", "").strip()
    if not pedido_edicao:
        return JSONResponse({"erro": "Descreva a alteração pretendida."}, status_code=400)

    deteccao = preview_runner.detectar(workspace)
    if deteccao is None:
        return JSONResponse(
            {"erro": "Edição por IA disponível apenas para projetos de software/sites, por agora."},
            status_code=400,
        )
    linguagem, _ = deteccao

    ficheiros_atuais = [
        {"caminho": f.name, "conteudo": f.read_text(encoding="utf-8", errors="replace")}
        for f in sorted(workspace.iterdir())
        if f.is_file() and f.name != "_meta.json"
    ]
    codigo_concat = "\n\n".join(f"### {f['caminho']}\n{f['conteudo']}" for f in ficheiros_atuais)

    try:
        resultado = await asyncio.to_thread(
            SOFTWARE_TEAM["programador"].responder_json,
            f"Tecnologia: {linguagem}\n\nFicheiros atuais do projeto:\n{codigo_concat}\n\n"
            f"Pedido de alteração do utilizador: {pedido_edicao}\n\n"
            f"Devolve TODOS os ficheiros completos e atualizados do projeto (não apenas os que mudaram).",
        )
    except Exception as e:
        return JSONResponse({"erro": str(e)}, status_code=500)

    novos_ficheiros = resultado.get("ficheiros", [])
    if not novos_ficheiros:
        return JSONResponse({"erro": "O Programador não devolveu ficheiros atualizados."}, status_code=500)

    orchestrator.escrever_ficheiros(workspace, novos_ficheiros)
    preview_runner.parar(run_id)
    zip_path = zipper.zip_pasta(workspace, workspace.parent / run_id)

    return {
        "ficheiros": [f["caminho"] for f in novos_ficheiros],
        "download": f"/download/{zip_path.name}",
    }


@app.get("/preview-html/{run_id}/{caminho:path}")
async def preview_html(run_id: str, caminho: str = "index.html"):
    workspace = _workspace_de(run_id)
    if workspace is None:
        return HTMLResponse("Execução não encontrada.", status_code=404)
    destino = (workspace / caminho).resolve()
    if workspace not in destino.parents or not destino.exists():
        return HTMLResponse("Ficheiro não encontrado.", status_code=404)
    return FileResponse(destino)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            mensagem = await ws.receive_json()
            if mensagem.get("tipo") == "iniciar":
                try:
                    await orchestrator.correr(
                        ws, mensagem.get("equipa", "software"), mensagem.get("pedido", "")
                    )
                except Exception as e:
                    await ws.send_json({"tipo": "erro", "mensagem": str(e)})
    except WebSocketDisconnect:
        pass
