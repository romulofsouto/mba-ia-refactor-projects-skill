from flask import Blueprint

from controllers import relatorio_controller
from routes.http import responder

relatorio_bp = Blueprint("relatorios", __name__)


@relatorio_bp.get("/relatorios/vendas")
def relatorio_vendas():
    return responder(relatorio_controller.relatorio_vendas())
