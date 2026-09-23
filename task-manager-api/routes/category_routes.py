from flask import Blueprint, request

from controllers import category_controller

category_bp = Blueprint("categories", __name__)


@category_bp.route("/categories", methods=["GET"])
def get_categories():
    return category_controller.list_categories()


@category_bp.route("/categories", methods=["POST"])
def create_category():
    return category_controller.create_category(request.get_json(silent=True))


@category_bp.route("/categories/<int:cat_id>", methods=["PUT"])
def update_category(cat_id):
    return category_controller.update_category(cat_id, request.get_json(silent=True))


@category_bp.route("/categories/<int:cat_id>", methods=["DELETE"])
def delete_category(cat_id):
    return category_controller.delete_category(cat_id)
