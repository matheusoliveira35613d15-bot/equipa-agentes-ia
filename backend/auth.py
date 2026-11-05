import hashlib
import hmac
import json
import os

from . import config

USERS_FILE = config.BASE_DIR / "data" / "users.json"
USERS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _carregar_utilizadores() -> dict:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _gravar_utilizadores(utilizadores: dict) -> None:
    USERS_FILE.write_text(json.dumps(utilizadores, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    derivado = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"{salt.hex()}${derivado.hex()}"


def _verificar_password(password: str, hash_guardado: str) -> bool:
    try:
        salt_hex, _ = hash_guardado.split("$", 1)
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    return hmac.compare_digest(_hash_password(password, salt), hash_guardado)


def utilizador_existe(username: str) -> bool:
    return username in _carregar_utilizadores()


def criar_utilizador(username: str, password: str) -> None:
    utilizadores = _carregar_utilizadores()
    utilizadores[username] = {"password_hash": _hash_password(password)}
    _gravar_utilizadores(utilizadores)


def autenticar(username: str, password: str) -> bool:
    registo = _carregar_utilizadores().get(username)
    if not registo:
        return False
    return _verificar_password(password, registo["password_hash"])
