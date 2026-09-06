from flask import Flask

from backend.config import Settings
from backend.routes.health import create_health_blueprint
from backend.routes.site import create_site_blueprint
from backend.services.health_service import build_health_service


def create_app(settings=None):
    app = Flask(__name__, template_folder="templates")
    settings = settings or Settings.from_env()
    app.config["SETTINGS"] = settings

    app.register_blueprint(create_site_blueprint())
    app.register_blueprint(create_health_blueprint(build_health_service(settings)))
    return app


app = create_app()
