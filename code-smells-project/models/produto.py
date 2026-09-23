from dataclasses import asdict, dataclass

CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]
CATEGORIA_PADRAO = "geral"
NOME_MIN = 2
NOME_MAX = 200

COLUNAS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"


@dataclass
class Produto:
    id: int
    nome: str
    descricao: str
    preco: float
    estoque: int
    categoria: str
    ativo: int
    criado_em: str

    @classmethod
    def from_row(cls, row):
        return cls(**dict(row))

    def tem_estoque_suficiente(self, quantidade):
        return self.estoque >= quantidade

    def to_dict(self):
        return asdict(self)


def _numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def validar_dados(dados):
    """Valida o payload de criação/atualização. Retorna a mensagem de erro ou None."""
    if not dados or not isinstance(dados, dict):
        return "Dados inválidos"
    if "nome" not in dados:
        return "Nome é obrigatório"
    if "preco" not in dados:
        return "Preço é obrigatório"
    if "estoque" not in dados:
        return "Estoque é obrigatório"

    nome, preco, estoque = dados["nome"], dados["preco"], dados["estoque"]
    if not isinstance(nome, str):
        return "Nome deve ser texto"
    if not _numero(preco):
        return "Preço deve ser numérico"
    if not isinstance(estoque, int) or isinstance(estoque, bool):
        return "Estoque deve ser um número inteiro"
    if preco < 0:
        return "Preço não pode ser negativo"
    if estoque < 0:
        return "Estoque não pode ser negativo"
    if len(nome) < NOME_MIN:
        return "Nome muito curto"
    if len(nome) > NOME_MAX:
        return "Nome muito longo"
    if not isinstance(dados.get("descricao", ""), str):
        return "Descrição deve ser texto"
    if dados.get("categoria", CATEGORIA_PADRAO) not in CATEGORIAS_VALIDAS:
        return "Categoria inválida. Válidas: " + str(CATEGORIAS_VALIDAS)
    return None


def _campos(dados):
    return (
        dados["nome"],
        dados.get("descricao", ""),
        dados["preco"],
        dados["estoque"],
        dados.get("categoria", CATEGORIA_PADRAO),
    )


def listar(db):
    rows = db.execute(f"SELECT {COLUNAS} FROM produtos WHERE ativo = 1 ORDER BY id").fetchall()
    return [Produto.from_row(row) for row in rows]


def buscar_por_id(db, produto_id):
    row = db.execute(
        f"SELECT {COLUNAS} FROM produtos WHERE id = ? AND ativo = 1", (produto_id,)
    ).fetchone()
    return Produto.from_row(row) if row else None


def buscar_por_ids(db, ids):
    ids = list(ids)
    if not ids:
        return {}
    marcadores = ", ".join("?" for _ in ids)
    rows = db.execute(
        f"SELECT {COLUNAS} FROM produtos WHERE ativo = 1 AND id IN ({marcadores})", ids
    ).fetchall()
    return {row["id"]: Produto.from_row(row) for row in rows}


def buscar(db, termo=None, categoria=None, preco_min=None, preco_max=None):
    filtros, params = ["ativo = 1"], []
    if termo:
        filtros.append("(nome LIKE ? OR descricao LIKE ?)")
        params += [f"%{termo}%", f"%{termo}%"]
    if categoria:
        filtros.append("categoria = ?")
        params.append(categoria)
    if preco_min is not None:
        filtros.append("preco >= ?")
        params.append(preco_min)
    if preco_max is not None:
        filtros.append("preco <= ?")
        params.append(preco_max)
    sql = f"SELECT {COLUNAS} FROM produtos WHERE {' AND '.join(filtros)} ORDER BY id"
    return [Produto.from_row(row) for row in db.execute(sql, params).fetchall()]


def criar(db, dados):
    with db:
        cursor = db.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            _campos(dados),
        )
    return cursor.lastrowid


def atualizar(db, produto_id, dados):
    with db:
        db.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
            (*_campos(dados), produto_id),
        )


def desativar(db, produto_id):
    """Soft delete: preserva o produto referenciado pelos itens de pedidos antigos."""
    with db:
        db.execute("UPDATE produtos SET ativo = 0 WHERE id = ?", (produto_id,))
