from collections import Counter

from models import pedido as pedido_model
from models import produto as produto_model
from services import notificacao_service


def _inteiro_positivo(valor):
    return isinstance(valor, int) and not isinstance(valor, bool) and valor > 0


def validar_dados(dados):
    if not dados or not isinstance(dados, dict):
        return "Dados inválidos"
    if not dados.get("usuario_id"):
        return "Usuario ID é obrigatório"
    if not _inteiro_positivo(dados["usuario_id"]):
        return "Usuario ID deve ser um inteiro positivo"
    itens = dados.get("itens")
    if not itens:
        return "Pedido deve ter pelo menos 1 item"
    if not isinstance(itens, list):
        return "Itens deve ser uma lista"
    for item in itens:
        if not isinstance(item, dict) or not _inteiro_positivo(item.get("produto_id")) \
                or not _inteiro_positivo(item.get("quantidade")):
            return "Cada item precisa de produto_id e quantidade inteiros e positivos"
    return None


def criar_pedido(db, usuario_id, itens):
    """Valida estoque, grava o pedido e dispara as notificações.

    Retorna (resultado, erro): exatamente um dos dois é None.
    """
    produtos = produto_model.buscar_por_ids(db, {item["produto_id"] for item in itens})
    quantidade_por_produto = Counter()
    for item in itens:
        quantidade_por_produto[item["produto_id"]] += item["quantidade"]

    total = 0
    linhas = []
    for item in itens:
        produto = produtos.get(item["produto_id"])
        if produto is None:
            return None, "Produto " + str(item["produto_id"]) + " não encontrado"
        if not produto.tem_estoque_suficiente(quantidade_por_produto[produto.id]):
            return None, "Estoque insuficiente para " + produto.nome
        total = total + (produto.preco * item["quantidade"])
        linhas.append((produto.id, item["quantidade"], produto.preco))

    try:
        pedido_id = pedido_model.criar(db, usuario_id, total, linhas)
    except pedido_model.EstoqueInsuficienteError as exc:
        return None, "Estoque insuficiente para " + produtos[exc.args[0]].nome

    notificacao_service.notificar_pedido_criado(pedido_id, usuario_id)
    return {"pedido_id": pedido_id, "total": total}, None


def atualizar_status(db, pedido_id, status):
    """Retorna False se o pedido não existe."""
    if not pedido_model.existe(db, pedido_id):
        return False
    pedido_model.atualizar_status(db, pedido_id, status)
    notificacao_service.notificar_mudanca_status(pedido_id, status)
    return True
