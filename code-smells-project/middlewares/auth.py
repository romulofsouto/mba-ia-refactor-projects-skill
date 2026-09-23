import hmac
from functools import wraps

from flask import jsonify, request

from config import settings

ADMIN_TOKEN_HEADER = "X-Admin-Token"


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not settings.ADMIN_TOKEN:
            return jsonify({"erro": "Endpoint administrativo desabilitado"}), 403
        token = request.headers.get(ADMIN_TOKEN_HEADER, "")
        if not hmac.compare_digest(token, settings.ADMIN_TOKEN):
            return jsonify({"erro": "Não autorizado"}), 401
        return view(*args, **kwargs)
    return wrapper
