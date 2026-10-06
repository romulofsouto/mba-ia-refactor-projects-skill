from functools import wraps

from flask import g, request

from models.errors import AuthenticationError, ForbiddenError
from models.user import User
from services import auth_service


def _bearer_token():
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def _authenticate(token):
    """Valida o token e relê o usuário, para que papel/status revogados valham antes de o token expirar."""
    claims = auth_service.verify_token(token)
    user = User.find(claims.get("user_id"))
    if not user:
        raise AuthenticationError("Token inválido")
    if not user.active:
        raise ForbiddenError("Usuário inativo")
    return {"user_id": user.id, "role": user.role}


def require_auth(view):
    """Exige o token devolvido por POST /login no header Authorization: Bearer <token>."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        token = _bearer_token()
        if not token:
            raise AuthenticationError("Token ausente")
        g.auth = _authenticate(token)
        return view(*args, **kwargs)

    return wrapper


def require_admin(view):
    @wraps(view)
    @require_auth
    def wrapper(*args, **kwargs):
        if g.auth["role"] != "admin":
            raise ForbiddenError("Acesso restrito a administradores")
        return view(*args, **kwargs)

    return wrapper


def optional_auth(view):
    """Rota pública que muda de comportamento para quem envia token (g.auth fica None sem token)."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        token = _bearer_token()
        g.auth = _authenticate(token) if token else None
        return view(*args, **kwargs)

    return wrapper
