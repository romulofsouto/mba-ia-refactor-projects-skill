import datetime
import logging

from flask import Flask
from flask_cors import CORS

from config import settings
from middlewares.error_handler import register_error_handlers
from models import db
from routes import register_routes

logger = logging.getLogger(__name__)


def create_app():
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if settings.SECRET_KEY_GENERATED:
        logger.warning("SECRET_KEY não definida; usando chave aleatória (tokens não sobrevivem a restart)")

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["DEBUG"] = settings.DEBUG

    CORS(app)
    db.init_app(app)
    register_error_handlers(app)
    register_routes(app)

    @app.route("/health")
    def health():
        return {"status": "ok", "timestamp": str(datetime.datetime.now())}

    @app.route("/")
    def index():
        return {"message": "Task Manager API", "version": settings.APP_VERSION}

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    # Servidor de desenvolvimento. Em produção: gunicorn "app:app"
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
