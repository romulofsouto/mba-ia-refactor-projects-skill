import logging

from controllers import require_payload
from models.errors import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from models.task import Task
from models.user import User
from services import auth_service

logger = logging.getLogger(__name__)


def _get_user(user_id):
    user = User.find(user_id)
    if not user:
        raise NotFoundError("Usuário não encontrado")
    return user


def _ensure_email_available(email, user_id=None):
    existing = User.find_by_email(email)
    if existing and existing.id != user_id:
        raise ConflictError("Email já cadastrado")


def list_users():
    return [{**user.to_dict(), "task_count": count} for user, count in User.all_with_task_count()], 200


def get_user(user_id):
    user = _get_user(user_id)
    return {**user.to_dict(), "tasks": [task.to_dict() for task in Task.by_user(user_id)]}, 200


def create_user(data):
    require_payload(data)
    name, email, password = data.get("name"), data.get("email"), data.get("password")
    role = data.get("role", "user")

    if not name:
        raise ValidationError("Nome é obrigatório")
    if not email:
        raise ValidationError("Email é obrigatório")
    if not password:
        raise ValidationError("Senha é obrigatória")
    User.validate_email(email)
    if not User.is_password_long_enough(password):
        raise ValidationError("Senha deve ter no mínimo 4 caracteres")
    _ensure_email_available(email)
    User.validate_role(role)

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    user.save("Erro ao criar usuário")
    logger.info("Usuário criado: %s - %s", user.id, user.name)
    return user.to_dict(), 201


def update_user(user_id, data):
    user = _get_user(user_id)
    require_payload(data)

    changes = {}
    if "name" in data:
        changes["name"] = data["name"]
    if "email" in data:
        User.validate_email(data["email"])
        _ensure_email_available(data["email"], user_id)
        changes["email"] = data["email"]
    if "password" in data and not User.is_password_long_enough(data["password"]):
        raise ValidationError("Senha muito curta")
    if "role" in data:
        User.validate_role(data["role"])
        changes["role"] = data["role"]
    if "active" in data:
        changes["active"] = data["active"]

    for field, value in changes.items():
        setattr(user, field, value)
    if "password" in data:
        user.set_password(data["password"])
    user.save("Erro ao atualizar")
    return user.to_dict(), 200


def delete_user(user_id):
    user = _get_user(user_id)
    user.delete("Erro ao deletar")  # as tasks do usuário são removidas em cascata
    logger.info("Usuário deletado: %s", user_id)
    return {"message": "Usuário deletado com sucesso"}, 200


def get_user_tasks(user_id):
    _get_user(user_id)
    return [task.to_summary_dict() for task in Task.by_user(user_id)], 200


def login(data):
    require_payload(data)
    email, password = data.get("email"), data.get("password")
    if not email or not password:
        raise ValidationError("Email e senha são obrigatórios")

    user = User.find_by_email(email)
    if not user or not user.check_password(password):
        raise AuthenticationError("Credenciais inválidas")
    if not user.active:
        raise ForbiddenError("Usuário inativo")

    if user.has_legacy_password_hash():
        user.set_password(password)
        user.save("Erro ao atualizar")

    return {
        "message": "Login realizado com sucesso",
        "user": user.to_dict(),
        "token": auth_service.issue_token(user),
    }, 200
