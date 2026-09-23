from flask import Blueprint

from controllers import pedido_controller
from routes.http import json_body, responder

pedido_bp = Blueprint("pedidos", __name__)


@pedido_bp.post("/pedidos")
def criar_pedido():
    return responder(pedido_controller.criar_pedido(json_body()))


@pedido_bp.get("/pedidos")
def listar_todos_pedidos():
    return responder(pedido_controller.listar_todos_pedidos())


@pedido_bp.get("/pedidos/usuario/<int:usuario_id>")
def listar_pedidos_usuario(usuario_id):
    return responder(pedido_controller.listar_pedidos_usuario(usuario_id))


@pedido_bp.put("/pedidos/<int:pedido_id>/status")
def atualizar_status_pedido(pedido_id):
    return responder(pedido_controller.atualizar_status_pedido(pedido_id, json_body()))
