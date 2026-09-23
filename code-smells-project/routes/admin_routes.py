from flask import Blueprint

from controllers import admin_controller
from middlewares.auth import require_admin
from routes.http import responder

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.post("/reset-db")
@require_admin
def reset_database():
    return responder(admin_controller.reset_database())
