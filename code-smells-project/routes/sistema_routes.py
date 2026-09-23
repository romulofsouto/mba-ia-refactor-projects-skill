from flask import Blueprint

from controllers import sistema_controller
from routes.http import responder

sistema_bp = Blueprint("sistema", __name__)


@sistema_bp.get("/")
def index():
    return responder(sistema_controller.index())


@sistema_bp.get("/health")
def health_check():
    return responder(sistema_controller.health_check())
