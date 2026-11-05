import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACES_DIR = BASE_DIR / "workspaces"
WORKSPACES_DIR.mkdir(exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "16000"))
MAX_REVIEW_ITERATIONS = int(os.getenv("MAX_REVIEW_ITERATIONS", "3"))

REGISTO_CHAVE = os.getenv("REGISTO_CHAVE", "")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
AUTH_ATIVA = bool(REGISTO_CHAVE)
