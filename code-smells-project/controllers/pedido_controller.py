from models import pedido as pedido_model
from models.database import get_db
from services import pedido_service


def criar_pedido(dados):
    erro = pedido_service.validar_dados(dados)
    if erro:
        return {"erro": erro}, 400
    resultado, erro = pedido_service.criar_pedido(get_db(), dados["usuario_id"], dados["itens"])
    if erro:
        return {"erro": erro, "sucesso": False}, 400
    return {"dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"}, 201


def listar_todos_pedidos():
    pedidos = pedido_model.listar(get_db())
    return {"dados": [p.to_dict() for p in pedidos], "sucesso": True}, 200


def listar_pedidos_usuario(usuario_id):
    pedidos = pedido_model.listar(get_db(), usuario_id=usuario_id)
    return {"dados": [p.to_dict() for p in pedidos], "sucesso": True}, 200


def atualizar_status_pedido(pedido_id, dados):
    status = dados.get("status", "") if isinstance(dados, dict) else ""
    if not pedido_model.status_valido(status):
        return {"erro": "Status inválido"}, 400
    if not pedido_service.atualizar_status(get_db(), pedido_id, status):
        return {"erro": "Pedido não encontrado"}, 404
    return {"sucesso": True, "mensagem": "Status atualizado"}, 200
