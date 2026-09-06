from flask import Blueprint, jsonify


def create_health_blueprint(health_service):
    blueprint = Blueprint("health", __name__)

    @blueprint.get("/health")
    def health():
        result = health_service.check()
        status_code = 200 if result["status"] == "ok" else 503
        return jsonify(result), status_code

    return blueprint
