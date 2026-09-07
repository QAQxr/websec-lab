from flask import Blueprint, g, redirect, render_template, url_for


def create_site_blueprint():
    blueprint = Blueprint("site", __name__)

    @blueprint.get("/")
    def landing():
        return render_template("index.html")

    @blueprint.get("/profile")
    def profile():
        if g.current_user is None:
            return redirect(url_for("auth.login"))
        return render_template(
            "profile.html",
            user=g.current_user,
            session=g.current_session,
        )

    @blueprint.get("/dashboard")
    def dashboard():
        if g.current_user is None:
            return redirect(url_for("auth.login"))
        return render_template("dashboard.html", user=g.current_user)

    return blueprint
