from flask import Blueprint, g, redirect, render_template, request, url_for

from backend.services.auth_service import AuthError, AuthService


def create_auth_blueprint(auth_service: AuthService, settings):
    blueprint = Blueprint("auth", __name__)

    @blueprint.route("/register", methods=["GET", "POST"])
    def register():
        values = {
            "username": request.form.get("username", ""),
            "email": request.form.get("email", ""),
        }
        if request.method == "GET":
            return render_template("register.html", values=values, errors=[])
        try:
            auth_service.register(
                request.form.get("username", ""),
                request.form.get("email", ""),
                request.form.get("password", ""),
                request.form.get("password_confirmation", ""),
            )
        except AuthError as error:
            return render_template("register.html", values=values, errors=[error.message]), error.status_code
        return redirect(url_for("auth.login", registered="1"))

    @blueprint.get("/verify/<token>")
    def verify(token):
        try:
            auth_service.verify_email(token)
        except AuthError as error:
            return render_template("verify.html", success=False, message=error.message), error.status_code
        return render_template(
            "verify.html",
            success=True,
            message="Your email is verified. You can now sign in.",
        )

    @blueprint.get("/dev/mail")
    def mailbox():
        if not settings.mailbox_enabled:
            return render_template("error.html", message="Not found."), 404
        return render_template("mailbox.html", messages=auth_service.mailbox_messages())

    @blueprint.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template(
                "login.html",
                errors=[],
                registered=request.args.get("registered") == "1",
                logged_out=request.args.get("logged_out") == "1",
            )
        try:
            session_key = auth_service.login(
                request.form.get("identifier", ""),
                request.form.get("password", ""),
                request.form.get("remember_me") == "on",
                request.cookies.get(settings.session_cookie_name),
                request.remote_addr or "unknown",
                request.headers.get("User-Agent", "unknown"),
            )
        except AuthError as error:
            return render_template("login.html", errors=[error.message]), error.status_code
        response = redirect(url_for("site.dashboard"))
        _set_session_cookie(response, settings, session_key, request.form.get("remember_me") == "on")
        return response

    @blueprint.post("/logout")
    def logout():
        auth_service.logout(request.cookies.get(settings.session_cookie_name))
        response = redirect(url_for("auth.login", logged_out="1"))
        _clear_session_cookie(response, settings)
        return response

    return blueprint


def _set_session_cookie(response, settings, session_key: str, remember_me: bool):
    max_age = (
        settings.remember_session_ttl_seconds
        if remember_me
        else settings.session_ttl_seconds
    )
    response.set_cookie(
        settings.session_cookie_name,
        session_key,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


def _clear_session_cookie(response, settings):
    response.set_cookie(
        settings.session_cookie_name,
        "",
        max_age=0,
        expires=0,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
