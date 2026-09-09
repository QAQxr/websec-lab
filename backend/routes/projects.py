from flask import Blueprint, g, redirect, render_template, request, url_for

from backend.services.project_service import ProjectError, ProjectService


def create_projects_blueprint(project_service: ProjectService):
    blueprint = Blueprint("projects", __name__)

    @blueprint.get("/projects")
    def index():
        if g.current_user is None:
            return redirect(url_for("auth.login"))
        try:
            projects = project_service.list_projects(g.current_user)
        except ProjectError as error:
            return _error_response(error)
        return render_template("projects.html", projects=projects)

    @blueprint.route("/projects/new", methods=["GET", "POST"])
    def new():
        if g.current_user is None:
            return redirect(url_for("auth.login"))
        values = _form_values(request.form if request.method == "POST" else {})
        if request.method == "GET":
            values["visibility"] = "private"
        if request.method == "POST":
            try:
                project = project_service.create_project(
                    g.current_user,
                    values["name"],
                    values["description"],
                    values["visibility"],
                )
            except ProjectError as error:
                return _project_form_response("Create project", values, [error.message], error.status_code)
            return redirect(url_for("projects.detail", project_id=project["id"]))
        return _project_form_response("Create project", values, [])

    @blueprint.get("/project/<int:project_id>")
    def detail(project_id):
        if g.current_user is None:
            return redirect(url_for("auth.login"))
        try:
            project = project_service.get_project(g.current_user, project_id)
        except ProjectError as error:
            return _error_response(error)
        return render_template("project_detail.html", project=project)

    @blueprint.route("/project/<int:project_id>/edit", methods=["GET", "POST"])
    def edit(project_id):
        if g.current_user is None:
            return redirect(url_for("auth.login"))
        try:
            if request.method == "GET":
                project = project_service.get_project_for_edit(g.current_user, project_id)
            else:
                project = project_service.get_project(g.current_user, project_id)
        except ProjectError as error:
            return _error_response(error)

        values = _form_values(request.form if request.method == "POST" else project)
        if request.method == "POST":
            try:
                project = project_service.update_project(
                    g.current_user,
                    project_id,
                    values["name"],
                    values["description"],
                    values["visibility"],
                )
            except ProjectError as error:
                return _project_form_response("Edit project", values, [error.message], error.status_code, project)
            return redirect(url_for("projects.detail", project_id=project["id"]))
        return _project_form_response("Edit project", values, [], project=project)

    @blueprint.post("/project/<int:project_id>/delete")
    def delete(project_id):
        if g.current_user is None:
            return redirect(url_for("auth.login"))
        try:
            project_service.delete_project(g.current_user, project_id)
        except ProjectError as error:
            return _error_response(error)
        return redirect(url_for("projects.index"))

    return blueprint


def _form_values(source) -> dict:
    return {
        "name": source.get("name", ""),
        "description": source.get("description", ""),
        "visibility": source.get("visibility", "private"),
    }


def _project_form_response(title, values, errors, status_code=200, project=None):
    return (
        render_template(
            "project_form.html",
            title_text=title,
            values=values,
            errors=errors,
            project=project,
            visibility_options=("private", "team", "shared"),
            can_edit_visibility=project is None or project.get("can_edit_visibility", False),
        ),
        status_code,
    )


def _error_response(error: ProjectError):
    return render_template("error.html", message=error.message), error.status_code
