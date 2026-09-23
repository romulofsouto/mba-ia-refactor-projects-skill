from functools import wraps

from flask import g, request

from models.errors import AuthenticationError, ForbiddenError
from services import auth_service


def _bearer_token():
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationError("Token ausente")
    return token


def require_auth(view):
    """Exige o token devolvido por POST /login no header Authorization: Bearer <token>."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        g.auth = auth_service.verify_token(_bearer_token())
        return view(*args, **kwargs)

    return wrapper


def require_admin(view):
    @wraps(view)
    @require_auth
    def wrapper(*args, **kwargs):
        if g.auth.get("role") != "admin":
            raise ForbiddenError("Acesso restrito a administradores")
        return view(*args, **kwargs)

    return wrapper
