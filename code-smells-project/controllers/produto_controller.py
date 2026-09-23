import logging

from models import produto as produto_model
from models.database import get_db

logger = logging.getLogger(__name__)


def _preco_opcional(valor):
    return float(valor) if valor else None


def listar_produtos():
    produtos = produto_model.listar(get_db())
    logger.info("Listando %d produtos", len(produtos))
    return {"dados": [p.to_dict() for p in produtos], "sucesso": True}, 200


def buscar_produtos(args):
    try:
        preco_min = _preco_opcional(args.get("preco_min"))
        preco_max = _preco_opcional(args.get("preco_max"))
    except ValueError:
        return {"erro": "preco_min e preco_max devem ser numéricos"}, 400

    resultados = produto_model.buscar(
        get_db(), args.get("q", ""), args.get("categoria"), preco_min, preco_max
    )
    return {"dados": [p.to_dict() for p in resultados], "total": len(resultados), "sucesso": True}, 200


def buscar_produto(produto_id):
    produto = produto_model.buscar_por_id(get_db(), produto_id)
    if not produto:
        return {"erro": "Produto não encontrado", "sucesso": False}, 404
    return {"dados": produto.to_dict(), "sucesso": True}, 200


def criar_produto(dados):
    erro = produto_model.validar_dados(dados)
    if erro:
        return {"erro": erro}, 400
    produto_id = produto_model.criar(get_db(), dados)
    logger.info("Produto criado com ID %s", produto_id)
    return {"dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"}, 201


def atualizar_produto(produto_id, dados):
    db = get_db()
    if not produto_model.buscar_por_id(db, produto_id):
        return {"erro": "Produto não encontrado"}, 404
    erro = produto_model.validar_dados(dados)
    if erro:
        return {"erro": erro}, 400
    produto_model.atualizar(db, produto_id, dados)
    return {"sucesso": True, "mensagem": "Produto atualizado"}, 200


def deletar_produto(produto_id):
    db = get_db()
    if not produto_model.buscar_por_id(db, produto_id):
        return {"erro": "Produto não encontrado"}, 404
    produto_model.desativar(db, produto_id)
    logger.info("Produto %s deletado", produto_id)
    return {"sucesso": True, "mensagem": "Produto deletado"}, 200
