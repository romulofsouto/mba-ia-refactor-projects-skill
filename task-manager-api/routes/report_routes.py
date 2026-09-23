from flask import Blueprint

from controllers import report_controller

report_bp = Blueprint("reports", __name__)


@report_bp.route("/reports/summary", methods=["GET"])
def summary_report():
    return report_controller.summary_report()


@report_bp.route("/reports/user/<int:user_id>", methods=["GET"])
def user_report(user_id):
    return report_controller.user_report(user_id)
