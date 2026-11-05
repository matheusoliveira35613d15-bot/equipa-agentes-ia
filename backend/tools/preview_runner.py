import atexit
import os
import socket
import subprocess
import time
from pathlib import Path

MAX_PREVIEWS_ATIVAS = 8

_previews: dict[str, dict] = {}


def detectar(workspace: Path) -> tuple[str, str] | None:
    """Deteta a tecnologia de uma execução pelos ficheiros que o Programador gera por convenção."""
    if (workspace / "server.js").exists():
        return "node", "server.js"
    if (workspace / "index.php").exists():
        return "php", "index.php"
    if (workspace / "index.html").exists():
        return "html", "index.html"
    return None


def _porta_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _porta_aberta(porta: int, tentativas: int = 20, intervalo: float = 0.25) -> bool:
    for _ in range(tentativas):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(intervalo)
            try:
                s.connect(("127.0.0.1", porta))
                return True
            except OSError:
                time.sleep(intervalo)
    return False


def _limpar_mais_antiga_se_necessario():
    vivos = {rid: info for rid, info in _previews.items() if info["processo"].poll() is None}
    _previews.clear()
    _previews.update(vivos)
    if len(_previews) >= MAX_PREVIEWS_ATIVAS:
        mais_antigo = min(_previews.items(), key=lambda item: item[1]["iniciado_em"])
        mais_antigo[1]["processo"].terminate()
        del _previews[mais_antigo[0]]


def iniciar(run_id: str, workspace: Path, linguagem: str, ficheiro_principal: str) -> dict:
    existente = _previews.get(run_id)
    if existente and existente["processo"].poll() is None:
        return {"url": existente["url"]}

    if linguagem not in ("node", "php"):
        raise ValueError(f"Pré-visualização com servidor não suportada para '{linguagem}'.")

    _limpar_mais_antiga_se_necessario()
    porta = _porta_livre()

    if linguagem == "node":
        processo = subprocess.Popen(
            ["node", ficheiro_principal],
            cwd=workspace,
            env={**os.environ, "PORT": str(porta)},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        processo = subprocess.Popen(
            ["php", "-S", f"127.0.0.1:{porta}", ficheiro_principal],
            cwd=workspace,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    if not _porta_aberta(porta):
        processo.kill()
        raise RuntimeError(
            "O servidor de pré-visualização não respondeu a tempo. "
            f"Verifique se o '{'Node.js' if linguagem == 'node' else 'PHP'}' está instalado."
        )

    url = f"http://127.0.0.1:{porta}/"
    _previews[run_id] = {"processo": processo, "url": url, "iniciado_em": time.time()}
    return {"url": url}


def parar(run_id: str):
    """Termina a pré-visualização de uma execução (chamar depois de editar os ficheiros, para a
    próxima pré-visualização arrancar já com o código atualizado)."""
    info = _previews.pop(run_id, None)
    if info:
        try:
            info["processo"].terminate()
        except Exception:
            pass


def parar_tudo():
    for info in _previews.values():
        try:
            info["processo"].terminate()
        except Exception:
            pass


atexit.register(parar_tudo)
