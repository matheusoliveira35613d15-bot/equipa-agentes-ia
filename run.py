import threading
import webbrowser

import uvicorn

from backend import config


def abrir_browser():
    webbrowser.open("http://127.0.0.1:8000")


def main():
    if not config.GEMINI_API_KEY:
        print("AVISO: GEMINI_API_KEY não está definida.")
        print("Copie .env.example para .env e preencha a sua chave antes de usar a equipa de agentes.")
    threading.Timer(1.5, abrir_browser).start()
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
