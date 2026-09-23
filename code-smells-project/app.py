import logging

from flask import Flask
from flask_cors import CORS

from config import settings
from middlewares.error_handler import register_error_handlers
from models import database
from routes import register_routes

logger = logging.getLogger(__name__)


def create_app():
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if settings.SECRET_KEY_GERADA:
        logger.warning("SECRET_KEY não definida; usando chave aleatória (sessões não sobrevivem a restart)")
    if not settings.ADMIN_TOKEN:
        logger.warning("ADMIN_TOKEN não definido; endpoints /admin desabilitados")

    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["DEBUG"] = settings.DEBUG
    CORS(app)

    database.init_app(app)
    register_error_handlers(app)
    register_routes(app)
    return app


app = create_app()

if __name__ == "__main__":
    # Servidor de desenvolvimento. Em produção: gunicorn "app:app"
    logger.info("Servidor iniciado em http://%s:%s", settings.HOST, settings.PORT)
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
