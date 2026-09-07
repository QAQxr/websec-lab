from pathlib import Path
from types import SimpleNamespace

from flask import Flask

from backend.routes.auth import create_auth_blueprint
from backend.routes.site import create_site_blueprint


def test_mailbox_is_disabled_outside_local_and_test():
    app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[2] / "backend" / "templates"))
    settings = SimpleNamespace(mailbox_enabled=False)
    service = SimpleNamespace(mailbox_messages=lambda: [])
    app.register_blueprint(create_site_blueprint())
    app.register_blueprint(create_auth_blueprint(service, settings))

    response = app.test_client().get("/dev/mail")

    assert response.status_code == 404
