import logging
import sqlite3

from flask import g
from werkzeug.security import generate_password_hash

from config import settings

logger = logging.getLogger(__name__)

HASH_PREFIXOS = ("scrypt:", "pbkdf2:")

SCHEMA = """
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        descricao TEXT,
        preco REAL,
        estoque INTEGER,
        categoria TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT,
        senha TEXT,
        tipo TEXT DEFAULT 'cliente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        status TEXT DEFAULT 'pendente',
        total REAL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER,
        produto_id INTEGER,
        quantidade INTEGER,
        preco_unitario REAL
    );
"""

PRODUTOS_EXEMPLO = [
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
]


def conectar():
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    """Conexão da requisição atual, aberta sob demanda e fechada no teardown."""
    if "db" not in g:
        g.db = conectar()
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)
    conn = conectar()
    try:
        _criar_schema(conn)
        _seed(conn)
        _migrar_senhas_texto_plano(conn)
    finally:
        conn.close()


def _criar_schema(conn):
    conn.executescript(SCHEMA)
    conn.commit()


def _seed(conn):
    if conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] > 0:
        return
    usuarios = [
        ("Admin", "admin@loja.com", settings.SEED_ADMIN_PASSWORD, "admin"),
        ("João Silva", "joao@email.com", settings.SEED_CLIENTE_PASSWORD, "cliente"),
        ("Maria Santos", "maria@email.com", settings.SEED_CLIENTE_PASSWORD, "cliente"),
    ]
    with conn:
        conn.executemany(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            PRODUTOS_EXEMPLO,
        )
        conn.executemany(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            [(nome, email, generate_password_hash(senha), tipo) for nome, email, senha, tipo in usuarios],
        )
    logger.info("Banco populado com dados de exemplo")


def _migrar_senhas_texto_plano(conn):
    """Bancos criados pela versão antiga guardam a senha pura; converte para hash."""
    rows = conn.execute("SELECT id, senha FROM usuarios").fetchall()
    pendentes = [
        (generate_password_hash(row["senha"]), row["id"])
        for row in rows
        if row["senha"] and not row["senha"].startswith(HASH_PREFIXOS)
    ]
    if pendentes:
        with conn:
            conn.executemany("UPDATE usuarios SET senha = ? WHERE id = ?", pendentes)
        logger.warning("%d senha(s) em texto plano convertida(s) para hash", len(pendentes))


def contar_registros(db):
    return {
        tabela: db.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        for tabela in ("produtos", "usuarios", "pedidos")
    }


def limpar_dados(db):
    with db:
        for tabela in ("itens_pedido", "pedidos", "produtos", "usuarios"):
            db.execute(f"DELETE FROM {tabela}")
