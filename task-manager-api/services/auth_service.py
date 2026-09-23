from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from config import settings
from models.errors import AuthenticationError

_SALT = "auth-token"


def _serializer():
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt=_SALT)


def issue_token(user):
    return _serializer().dumps({"user_id": user.id, "role": user.role})


def verify_token(token):
    try:
        return _serializer().loads(token, max_age=settings.AUTH_TOKEN_MAX_AGE)
    except SignatureExpired:
        raise AuthenticationError("Token expirado")
    except BadSignature:
        raise AuthenticationError("Token inválido")
