import py_compile
import subprocess
import sys
from pathlib import Path


def testar_python(workspace: Path, ficheiro_principal: str, timeout: int = 10) -> tuple[bool, str]:
    caminho = workspace / ficheiro_principal
    if not caminho.exists():
        return False, f"Ficheiro principal '{ficheiro_principal}' não encontrado."

    try:
        py_compile.compile(str(caminho), doraise=True)
    except py_compile.PyCompileError as e:
        return False, f"Erro de sintaxe:\n{e}"

    try:
        resultado = subprocess.run(
            [sys.executable, str(caminho)],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
            input="",
        )
    except subprocess.TimeoutExpired:
        return False, f"Execução excedeu o limite de {timeout}s (pode estar à espera de input ou em ciclo infinito)."

    saida = (resultado.stdout or "") + (resultado.stderr or "")
    if resultado.returncode != 0:
        return False, f"Terminou com erro (código {resultado.returncode}):\n{saida[-2000:]}"
    return True, f"Execução concluída sem erros.\nSaída:\n{saida[-1000:] or '(sem saída)'}"


def testar_node(workspace: Path, ficheiro_principal: str, timeout: int = 10) -> tuple[bool, str]:
    """Valida apenas a sintaxe (--check): um servidor Node fica à escuta indefinidamente, por isso
    não o corremos de verdade aqui."""
    caminho = workspace / ficheiro_principal
    if not caminho.exists():
        return False, f"Ficheiro principal '{ficheiro_principal}' não encontrado."

    try:
        resultado = subprocess.run(
            ["node", "--check", str(caminho)],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return True, "Node.js não encontrado neste sistema — não foi possível validar automaticamente."
    except subprocess.TimeoutExpired:
        return False, f"Validação excedeu o limite de {timeout}s."

    if resultado.returncode != 0:
        return False, f"Erro de sintaxe:\n{(resultado.stderr or resultado.stdout)[-2000:]}"
    return True, "Sintaxe válida. Para testar o servidor, execute `node " + ficheiro_principal + "` manualmente."


def testar_php(workspace: Path, ficheiro_principal: str, timeout: int = 10) -> tuple[bool, str]:
    """Valida apenas a sintaxe (-l / lint), sem executar o ficheiro."""
    caminho = workspace / ficheiro_principal
    if not caminho.exists():
        return False, f"Ficheiro principal '{ficheiro_principal}' não encontrado."

    try:
        resultado = subprocess.run(
            ["php", "-l", str(caminho)],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return True, "PHP não encontrado neste sistema — não foi possível validar automaticamente."
    except subprocess.TimeoutExpired:
        return False, f"Validação excedeu o limite de {timeout}s."

    if resultado.returncode != 0:
        return False, f"Erro de sintaxe:\n{(resultado.stdout or resultado.stderr)[-2000:]}"
    return True, "Sintaxe válida. Para testar o servidor, execute `php -S localhost:8080` manualmente."
