import logging

from models import usuario as usuario_model
from models.database import get_db

logger = logging.getLogger(__name__)


def listar_usuarios():
    usuarios = usuario_model.listar(get_db())
    return {"dados": [u.to_dict() for u in usuarios], "sucesso": True}, 200


def buscar_usuario(usuario_id):
    usuario = usuario_model.buscar_por_id(get_db(), usuario_id)
    if not usuario:
        return {"erro": "Usuário não encontrado"}, 404
    return {"dados": usuario.to_dict(), "sucesso": True}, 200


def criar_usuario(dados):
    erro = usuario_model.validar_dados(dados)
    if erro:
        return {"erro": erro}, 400
    usuario_id = usuario_model.criar(get_db(), dados["nome"], dados["email"], dados["senha"])
    logger.info("Usuário criado com ID %s", usuario_id)
    return {"dados": {"id": usuario_id}, "sucesso": True}, 201


def login(dados):
    if not dados or not isinstance(dados, dict):
        return {"erro": "Dados inválidos"}, 400
    email, senha = dados.get("email", ""), dados.get("senha", "")
    if not email or not senha:
        return {"erro": "Email e senha são obrigatórios"}, 400
    if not isinstance(email, str) or not isinstance(senha, str):
        return {"erro": "Email e senha devem ser texto"}, 400

    usuario = usuario_model.autenticar(get_db(), email, senha)
    if not usuario:
        logger.info("Login falhou")
        return {"erro": "Email ou senha inválidos", "sucesso": False}, 401
    logger.info("Login bem-sucedido: usuario %s", usuario.id)
    return {"dados": usuario.to_sessao_dict(), "sucesso": True, "mensagem": "Login OK"}, 200
