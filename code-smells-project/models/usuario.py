from dataclasses import dataclass

from werkzeug.security import check_password_hash, generate_password_hash

TIPO_PADRAO = "cliente"

COLUNAS = "id, nome, email, senha, tipo, criado_em"


@dataclass
class Usuario:
    id: int
    nome: str
    email: str
    senha_hash: str
    tipo: str
    criado_em: str

    @classmethod
    def from_row(cls, row):
        return cls(row["id"], row["nome"], row["email"], row["senha"], row["tipo"], row["criado_em"])

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def to_dict(self):
        # O hash da senha nunca sai do Model.
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "tipo": self.tipo,
            "criado_em": self.criado_em,
        }

    def to_sessao_dict(self):
        return {"id": self.id, "nome": self.nome, "email": self.email, "tipo": self.tipo}


def validar_dados(dados):
    if not dados or not isinstance(dados, dict):
        return "Dados inválidos"
    campos = [dados.get("nome", ""), dados.get("email", ""), dados.get("senha", "")]
    if not all(campos):
        return "Nome, email e senha são obrigatórios"
    if not all(isinstance(campo, str) for campo in campos):
        return "Nome, email e senha devem ser texto"
    return None


def listar(db):
    rows = db.execute(f"SELECT {COLUNAS} FROM usuarios ORDER BY id").fetchall()
    return [Usuario.from_row(row) for row in rows]


def buscar_por_id(db, usuario_id):
    row = db.execute(f"SELECT {COLUNAS} FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return Usuario.from_row(row) if row else None


def criar(db, nome, email, senha, tipo=TIPO_PADRAO):
    with db:
        cursor = db.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, generate_password_hash(senha), tipo),
        )
    return cursor.lastrowid


def autenticar(db, email, senha):
    rows = db.execute(f"SELECT {COLUNAS} FROM usuarios WHERE email = ? ORDER BY id", (email,)).fetchall()
    for row in rows:
        usuario = Usuario.from_row(row)
        if usuario.verificar_senha(senha):
            return usuario
    return None
