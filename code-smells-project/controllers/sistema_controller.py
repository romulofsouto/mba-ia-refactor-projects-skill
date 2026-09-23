import logging
import sqlite3

from config import settings
from models import database

logger = logging.getLogger(__name__)


def index():
    return {
        "mensagem": "Bem-vindo à API da Loja",
        "versao": settings.APP_VERSION,
        "endpoints": {
            "produtos": "/produtos",
            "usuarios": "/usuarios",
            "pedidos": "/pedidos",
            "login": "/login",
            "relatorios": "/relatorios/vendas",
            "health": "/health",
        },
    }, 200


def health_check():
    try:
        counts = database.contar_registros(database.get_db())
    except sqlite3.Error:
        logger.exception("Health check falhou")
        return {"status": "erro", "database": "disconnected"}, 500
    return {
        "status": "ok",
        "database": "connected",
        "counts": counts,
        "versao": settings.APP_VERSION,
    }, 200
