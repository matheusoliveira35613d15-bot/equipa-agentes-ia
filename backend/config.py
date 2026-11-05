import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Pasta onde ficam os dados que precisam de sobreviver a reinícios (projetos, contas). Por
# omissão é a própria pasta do projeto; definir DATA_DIR (ex: para um disco persistente montado,
# como um Volume do Fly.io) faz os dados viverem aí em vez de serem apagados a cada reinício.
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR)))
DATA_DIR.mkdir(parents=True, exist_ok=True)

WORKSPACES_DIR = DATA_DIR / "workspaces"
WORKSPACES_DIR.mkdir(exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "16000"))
MAX_REVIEW_ITERATIONS = int(os.getenv("MAX_REVIEW_ITERATIONS", "3"))

REGISTO_CHAVE = os.getenv("REGISTO_CHAVE", "")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
AUTH_ATIVA = bool(REGISTO_CHAVE)
