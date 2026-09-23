import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def http_error(exc):
        return jsonify({"erro": exc.description}), exc.code

    @app.errorhandler(Exception)
    def unexpected_error(exc):
        logger.exception("Erro não tratado")
        return jsonify({"erro": "Erro interno do servidor"}), 500
