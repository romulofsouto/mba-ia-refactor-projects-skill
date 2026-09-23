import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _bool(name, default="false"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes")


APP_VERSION = "1.0"

SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
SECRET_KEY_GENERATED = not os.environ.get("SECRET_KEY")

DEBUG = _bool("DEBUG")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# Caminho relativo ao diretório instance/ do Flask (mesmo local do banco original)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///tasks.db")

# Validade do token devolvido por POST /login
AUTH_TOKEN_MAX_AGE = int(os.environ.get("AUTH_TOKEN_MAX_AGE", "86400"))

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
