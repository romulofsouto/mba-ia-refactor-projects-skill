from models.errors import ValidationError


def require_payload(data):
    if not data:
        raise ValidationError("Dados inválidos")
    return data
