import pymysql
import redis
from flask import Flask, g, request, render_template

from backend.config import Settings
from backend.routes.auth import create_auth_blueprint
from backend.routes.health import create_health_blueprint
from backend.routes.projects import create_projects_blueprint
from backend.routes.site import create_site_blueprint
from backend.services.auth_service import build_auth_service
from backend.services.health_service import build_health_service
from backend.services.project_service import build_project_service


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
        return render_template(
            "error.html",
            message="The authentication service is temporarily unavailable.",
        ), 503

    app.register_blueprint(create_site_blueprint())
    app.register_blueprint(create_projects_blueprint(project_service))
    app.register_blueprint(create_auth_blueprint(auth_service, settings))
    app.register_blueprint(create_health_blueprint(build_health_service(settings)))
    return app


app = create_app()
