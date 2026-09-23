from dataclasses import dataclass, field

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_CANCELADO = "cancelado"
STATUS_VALIDOS = [STATUS_PENDENTE, STATUS_APROVADO, "enviado", "entregue", STATUS_CANCELADO]

PRODUTO_DESCONHECIDO = "Desconhecido"


class EstoqueInsuficienteError(Exception):
    pass


@dataclass
class ItemPedido:
    produto_id: int
    produto_nome: str
    quantidade: int
    preco_unitario: float

    def to_dict(self):
        return {
            "produto_id": self.produto_id,
            "produto_nome": self.produto_nome,
            "quantidade": self.quantidade,
            "preco_unitario": self.preco_unitario,
        }


@dataclass
class Pedido:
    id: int
    usuario_id: int
    status: str
    total: float
    criado_em: str
    itens: list = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "status": self.status,
            "total": self.total,
            "criado_em": self.criado_em,
            "itens": [item.to_dict() for item in self.itens],
        }


def status_valido(status):
    return status in STATUS_VALIDOS


def listar(db, usuario_id=None):
    """Pedidos com seus itens em uma única query (sem N+1)."""
    sql = """
        SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
               i.id AS item_id, i.produto_id, i.quantidade, i.preco_unitario,
               pr.nome AS produto_nome
        FROM pedidos p
        LEFT JOIN itens_pedido i ON i.pedido_id = p.id
        LEFT JOIN produtos pr ON pr.id = i.produto_id
    """
    params = ()
    if usuario_id is not None:
        sql += " WHERE p.usuario_id = ?"
        params = (usuario_id,)
    sql += " ORDER BY p.id, i.id"

    pedidos = {}
    for row in db.execute(sql, params).fetchall():
        pedido = pedidos.get(row["id"])
        if pedido is None:
            pedido = pedidos[row["id"]] = Pedido(
                row["id"], row["usuario_id"], row["status"], row["total"], row["criado_em"]
            )
        if row["item_id"] is not None:
            pedido.itens.append(ItemPedido(
                row["produto_id"],
                row["produto_nome"] or PRODUTO_DESCONHECIDO,
                row["quantidade"],
                row["preco_unitario"],
            ))
    return list(pedidos.values())


def existe(db, pedido_id):
    return db.execute("SELECT 1 FROM pedidos WHERE id = ?", (pedido_id,)).fetchone() is not None


def criar(db, usuario_id, total, itens):
    """Grava pedido, itens e baixa de estoque numa única transação.

    `itens` é uma lista de (produto_id, quantidade, preco_unitario). A baixa só
    acontece se ainda houver estoque no momento da escrita; caso contrário a
    transação inteira é desfeita.
    """
    with db:
        cursor = db.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, STATUS_PENDENTE, total),
        )
        pedido_id = cursor.lastrowid
        for produto_id, quantidade, preco_unitario in itens:
            db.execute(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                (pedido_id, produto_id, quantidade, preco_unitario),
            )
            baixa = db.execute(
                "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                (quantidade, produto_id, quantidade),
            )
            if baixa.rowcount == 0:
                raise EstoqueInsuficienteError(produto_id)
    return pedido_id


def atualizar_status(db, pedido_id, status):
    with db:
        db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))
