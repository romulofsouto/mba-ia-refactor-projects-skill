import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _bool(nome, padrao="false"):
    return os.environ.get(nome, padrao).strip().lower() in ("1", "true", "yes")


APP_VERSION = "1.0.0"

SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
SECRET_KEY_GERADA = "SECRET_KEY" not in os.environ

DEBUG = _bool("DEBUG")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")

# Sem ADMIN_TOKEN, os endpoints administrativos ficam desabilitados.
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN") or None

# Senhas dos usuários de exemplo criados no primeiro boot. Sem elas, uma senha
# aleatória é usada (os usuários existem, mas não é possível logar com eles).
SEED_ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD") or secrets.token_urlsafe(16)
SEED_CLIENTE_PASSWORD = os.environ.get("SEED_CLIENTE_PASSWORD") or secrets.token_urlsafe(16)
