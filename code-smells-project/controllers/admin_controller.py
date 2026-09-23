import logging

from models import database

logger = logging.getLogger(__name__)


def reset_database():
    database.limpar_dados(database.get_db())
    logger.warning("Banco de dados resetado via /admin/reset-db")
    return {"mensagem": "Banco de dados resetado", "sucesso": True}, 200
