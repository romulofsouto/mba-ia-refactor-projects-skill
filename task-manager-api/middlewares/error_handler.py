import logging

from werkzeug.exceptions import HTTPException

from models.database import db
from models.errors import (
    AuthenticationError,
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    PersistenceError,
    ValidationError,
)

logger = logging.getLogger(__name__)

STATUS_BY_ERROR = {
    ValidationError: 400,
    AuthenticationError: 401,
    ForbiddenError: 403,
    NotFoundError: 404,
    ConflictError: 409,
    PersistenceError: 500,
}


def register_error_handlers(app):
    @app.errorhandler(DomainError)
    def domain_error(exc):
        status = STATUS_BY_ERROR.get(type(exc), 400)
        if status >= 500:
            logger.error("%s", exc.message, exc_info=exc.__cause__ or exc)
        return {"error": exc.message}, status

    @app.errorhandler(HTTPException)
    def http_error(exc):
        return exc

    @app.errorhandler(Exception)
    def unexpected_error(exc):
        db.session.rollback()
        logger.exception("Erro não tratado")
        return {"error": "Erro interno"}, 500
