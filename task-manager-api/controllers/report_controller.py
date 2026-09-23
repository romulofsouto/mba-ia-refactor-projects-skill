from models.errors import NotFoundError
from models.user import User
from services import report_service


def summary_report():
    return report_service.summary(), 200


def user_report(user_id):
    user = User.find(user_id)
    if not user:
        raise NotFoundError("Usuário não encontrado")
    return report_service.user_report(user), 200
