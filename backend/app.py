import pymysql
import redis
from flask import Flask, g, jsonify, render_template, request

from backend.config import Settings
from backend.routes.auth import create_auth_blueprint
from backend.routes.health import create_health_blueprint
from backend.routes.project_api import create_project_api_blueprint
from backend.routes.projects import create_projects_blueprint
from backend.routes.site import create_site_blueprint
from backend.services.auth_service import build_auth_service
from backend.services.health_service import build_health_service
from backend.services.project_service import build_project_service


def _is_api_request() -> bool:
    return request.path == "/api" or request.path.startswith("/api/")


def _api_error_response(code: str, message: str, status_code: int):
    return jsonify({"error": {"code": code, "message": message}}), status_code


def create_app(settings=None):
    app = Flask(__name__, template_folder="templates")
    settings = settings or Settings.from_env()
    app.config["SETTINGS"] = settings
    auth_service = build_auth_service(settings)
    app.extensions["auth_service"] = auth_service
    project_service = build_project_service(settings)
    app.extensions["project_service"] = project_service

    @app.before_request
    def load_authenticated_user():
        session_key = request.cookies.get(settings.session_cookie_name)
        g.current_user, g.current_session = auth_service.authenticate_request(session_key)

    @app.context_processor
    def expose_request_identity():
        return {"current_user": getattr(g, "current_user", None)}

    @app.errorhandler(pymysql.MySQLError)
    @app.errorhandler(redis.RedisError)
    def infrastructure_error(_error):
        if _is_api_request():
            return _api_error_response(
                "service_unavailable",
                "The service is temporarily unavailable.",
                503,
            )
        return render_template(
            "error.html",
            message="The authentication service is temporarily unavailable.",
        ), 503

    @app.errorhandler(404)
    def not_found(_error):
        if _is_api_request():
            return _api_error_response("not_found", "Resource not found.", 404)
        return render_template("error.html", message="Not found."), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        if _is_api_request():
            return _api_error_response("method_not_allowed", "Method not allowed.", 405)
        return render_template("error.html", message="Method not allowed."), 405

    @app.errorhandler(500)
    def internal_error(_error):
        if _is_api_request():
            return _api_error_response("internal_error", "The service could not complete the request.", 500)
        return render_template("error.html", message="The service could not complete the request."), 500

    app.register_blueprint(create_site_blueprint())
    app.register_blueprint(create_projects_blueprint(project_service))
    app.register_blueprint(create_project_api_blueprint(project_service))
    app.register_blueprint(create_auth_blueprint(auth_service, settings))
    app.register_blueprint(create_health_blueprint(build_health_service(settings)))
    return app


app = create_app()
