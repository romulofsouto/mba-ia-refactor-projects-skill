from models import relatorio as relatorio_model
from models.database import get_db


def relatorio_vendas():
    return {"dados": relatorio_model.relatorio_vendas(get_db()), "sucesso": True}, 200
