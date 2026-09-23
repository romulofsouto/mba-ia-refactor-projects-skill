from flask import Blueprint

from controllers import usuario_controller
from routes.http import json_body, responder

usuario_bp = Blueprint("usuarios", __name__)


@usuario_bp.get("/usuarios")
def listar_usuarios():
    return responder(usuario_controller.listar_usuarios())


@usuario_bp.get("/usuarios/<int:id>")
def buscar_usuario(id):
    return responder(usuario_controller.buscar_usuario(id))


@usuario_bp.post("/usuarios")
def criar_usuario():
    return responder(usuario_controller.criar_usuario(json_body()))


@usuario_bp.post("/login")
def login():
    return responder(usuario_controller.login(json_body()))
