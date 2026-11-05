import asyncio
import json
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from . import auth, config, orchestrator
from .teams import SOFTWARE_TEAM
from .tools import preview_runner, zipper

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY, same_site="lax")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


async def exigir_login(request: Request) -> None:
    """Exige sessão iniciada quando o sistema de contas está ativo (REGISTO_CHAVE definida no
    .env). Em uso local, sem essa variável, a app fica aberta como antes."""
    if not config.AUTH_ATIVA:
        return
    if not request.session.get("user"):
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})


def _pagina_auth(nome_ficheiro: str, erro: str | None = None) -> str:
    html = (FRONTEND_DIR / nome_ficheiro).read_text(encoding="utf-8")
    bloco_erro = f'<p class="erro-auth">{erro}</p>' if erro else ""
    return html.replace("<!--ERRO-->", bloco_erro)


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


# --- Autenticação ---


@app.get("/login")
async def login_pagina(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(_pagina_auth("login.html"))


@app.post("/login")
async def login_submeter(request: Request):
    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    if auth.autenticar(username, password):
        request.session["user"] = username
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(_pagina_auth("login.html", "Utilizador ou password incorretos."), status_code=401)


@app.get("/registar")
async def registar_pagina(request: Request):
    if not config.AUTH_ATIVA:
        return HTMLResponse("Registo não disponível nesta instalação.", status_code=404)
    if request.session.get("user"):
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(_pagina_auth("registar.html"))


@app.post("/registar")
async def registar_submeter(request: Request):
    if not config.AUTH_ATIVA:
        return HTMLResponse("Registo não disponível nesta instalação.", status_code=404)

    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    chave = str(form.get("chave", ""))

    erro = None
    if not username or not password:
        erro = "Preencha utilizador e password."
    elif len(password) < 6:
        erro = "A password deve ter pelo menos 6 caracteres."
    elif not secrets.compare_digest(chave, config.REGISTO_CHAVE):
        erro = "Chave de registo incorreta."
    elif auth.utilizador_existe(username):
        erro = "Esse utilizador já existe."

    if erro:
        return HTMLResponse(_pagina_auth("registar.html", erro), status_code=400)

    auth.criar_utilizador(username, password)
    request.session["user"] = username
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# --- App ---


@app.get("/")
async def index(_=Depends(exigir_login)):
    return HTMLResponse((FRONTEND_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/download/{filename}")
async def download(filename: str, _=Depends(exigir_login)):
    destino = (config.WORKSPACES_DIR / filename).resolve()
    if config.WORKSPACES_DIR.resolve() not in destino.parents or not destino.exists():
        return HTMLResponse("Ficheiro não encontrado.", status_code=404)
    return FileResponse(destino, filename=filename)


@app.post("/preview/{run_id}")
async def preview(run_id: str, _=Depends(exigir_login)):
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
async def listar_execucoes(_=Depends(exigir_login)):
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
async def editar(run_id: str, request: Request, _=Depends(exigir_login)):
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
    linguagem, _tecnologia = deteccao

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
async def preview_html(run_id: str, caminho: str = "index.html", _=Depends(exigir_login)):
    workspace = _workspace_de(run_id)
    if workspace is None:
        return HTMLResponse("Execução não encontrada.", status_code=404)
    destino = (workspace / caminho).resolve()
    if workspace not in destino.parents or not destino.exists():
        return HTMLResponse("Ficheiro não encontrado.", status_code=404)
    return FileResponse(destino)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    if config.AUTH_ATIVA and not ws.session.get("user"):
        await ws.close(code=1008)
        return

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
