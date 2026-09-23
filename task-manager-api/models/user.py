import hashlib
import hmac
import re

from werkzeug.security import check_password_hash, generate_password_hash

from models.database import CRUDMixin, db
from models.errors import ValidationError
from utils.dates import utc_now

VALID_ROLES = ("user", "admin", "manager")
MIN_PASSWORD_LENGTH = 4
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$")
# Hashes gravados pela versão antiga (MD5 hex, sem salt); são migrados no próximo login
LEGACY_MD5_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class User(CRUDMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="user")
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def set_password(self, pwd):
        self.password = generate_password_hash(pwd)

    def check_password(self, pwd):
        if self.has_legacy_password_hash():
            legacy = hashlib.md5(pwd.encode()).hexdigest()
            return hmac.compare_digest(self.password, legacy)
        return check_password_hash(self.password, pwd)

    def has_legacy_password_hash(self):
        return bool(LEGACY_MD5_PATTERN.match(self.password or ""))

    def is_admin(self):
        return self.role == "admin"

    @staticmethod
    def validate_email(email):
        if not isinstance(email, str) or not EMAIL_PATTERN.match(email):
            raise ValidationError("Email inválido")

    @staticmethod
    def validate_role(role):
        if role not in VALID_ROLES:
            raise ValidationError("Role inválido")

    @staticmethod
    def is_password_long_enough(pwd):
        return isinstance(pwd, str) and len(pwd) >= MIN_PASSWORD_LENGTH

    @classmethod
    def find_by_email(cls, email):
        return db.session.scalars(db.select(cls).filter_by(email=email)).first()

    @classmethod
    def all_with_task_count(cls):
        """[(entidade, nº de tasks)] em uma única query, sem N+1."""
        from models.task import Task

        query = (
            db.select(cls, db.func.count(Task.id))
            .outerjoin(Task, Task.user_id == cls.id)
            .group_by(cls.id)
            .order_by(cls.id)
        )
        return db.session.execute(query).all()

    def to_dict(self):
        # O hash de senha nunca sai da API
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "active": self.active,
            "created_at": str(self.created_at),
        }
