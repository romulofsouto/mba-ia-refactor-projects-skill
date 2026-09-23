from flask import Blueprint, request

from controllers import produto_controller
from routes.http import json_body, responder

produto_bp = Blueprint("produtos", __name__)


@produto_bp.get("/produtos")
def listar_produtos():
    return responder(produto_controller.listar_produtos())


@produto_bp.get("/produtos/busca")
def buscar_produtos():
    return responder(produto_controller.buscar_produtos(request.args))


@produto_bp.get("/produtos/<int:id>")
def buscar_produto(id):
    return responder(produto_controller.buscar_produto(id))


@produto_bp.post("/produtos")
def criar_produto():
    return responder(produto_controller.criar_produto(json_body()))


@produto_bp.put("/produtos/<int:id>")
def atualizar_produto(id):
    return responder(produto_controller.atualizar_produto(id, json_body()))


@produto_bp.delete("/produtos/<int:id>")
def deletar_produto(id):
    return responder(produto_controller.deletar_produto(id))
