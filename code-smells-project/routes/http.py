from flask import jsonify, request


def responder(resultado):
    body, status = resultado
    return jsonify(body), status


def json_body():
    return request.get_json(silent=True)
