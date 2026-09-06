from flask import Blueprint, render_template


def create_site_blueprint():
    blueprint = Blueprint("site", __name__)

    @blueprint.get("/")
    def landing():
        return render_template("index.html")

    return blueprint
