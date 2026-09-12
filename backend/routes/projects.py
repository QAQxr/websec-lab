from flask import Blueprint, g, redirect, render_template, request, url_for

from backend.services.membership_service import (
    MembershipError,
    MembershipForbiddenError,
    MembershipService,
)
from backend.services.ownership_transfer_service import (
    OwnershipTransferError,
    OwnershipTransferService,
)
from backend.services.project_service import ProjectError, ProjectService


def create_projects_blueprint(
    project_service: ProjectService,
    membership_service: MembershipService,
    ownership_transfer_service: OwnershipTransferService,
):
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
        members = []
        try:
            members = membership_service.list_members(g.current_user, project_id)
        except MembershipForbiddenError:
            pass
        except MembershipError as error:
            return _error_response(error)
        return render_template("project_detail.html", project=project, members=members)

    @blueprint.route(
        "/project/<int:project_id>/ownership/transfer",
        methods=["GET", "POST"],
    )
    def transfer_ownership(project_id):
        if g.current_user is None:
            return redirect(url_for("auth.login"))
        try:
            project = ownership_transfer_service.get_transfer_project(
                g.current_user,
                project_id,
            )
        except (ProjectError, OwnershipTransferError) as error:
            return _error_response(error)
        values = {"target_user_id": request.form.get("target_user_id", "")}
        if request.method == "POST":
            try:
                project = ownership_transfer_service.transfer_ownership(
                    g.current_user,
                    project_id,
                    values["target_user_id"],
                )
            except OwnershipTransferError as error:
                return _ownership_form_response(project, values, [error.message], error.status_code)
            except ProjectError as error:
                return _error_response(error)
            return redirect(url_for("projects.detail", project_id=project["id"]))
        return _ownership_form_response(project, values, [])

    @blueprint.get("/project/<int:project_id>/members")
    def members(project_id):
        if g.current_user is None:
            return redirect(url_for("auth.login"))
        try:
            project = project_service.get_project(g.current_user, project_id)
            project_members = membership_service.list_members(g.current_user, project_id)
        except (ProjectError, MembershipError) as error:
            return _error_response(error)
        return render_template(
            "project_members.html",
            project=project,
            members=project_members,
            errors=[],
        )

    @blueprint.get("/project/<int:project_id>/members/new")
    @blueprint.post("/project/<int:project_id>/members")
    def new_member(project_id):
        if g.current_user is None:
            return redirect(url_for("auth.login"))
        try:
            project = membership_service.get_management_project(g.current_user, project_id)
        except (ProjectError, MembershipError) as error:
            return _error_response(error)
        values = _member_form_values(request.form if request.method == "POST" else {})
        if request.method == "POST":
            try:
                membership_service.invite_member(
                    g.current_user,
                    project_id,
                    values["user_id"],
                    values["role"],
                )
            except MembershipError as error:
                return _member_form_response(project, values, [error.message], error.status_code)
            return redirect(url_for("projects.members", project_id=project_id))
        return _member_form_response(project, values, [])

    @blueprint.post("/project/<int:project_id>/members/<int:user_id>/role")
    def change_member_role(project_id, user_id):
        if g.current_user is None:
            return redirect(url_for("auth.login"))
        try:
            membership_service.change_member_role(
                g.current_user,
                project_id,
                user_id,
                request.form.get("role", ""),
            )
        except (ProjectError, MembershipError) as error:
            return _error_response(error)
        return redirect(url_for("projects.members", project_id=project_id))

    @blueprint.post("/project/<int:project_id>/members/<int:user_id>/remove")
    def remove_member(project_id, user_id):
        if g.current_user is None:
            return redirect(url_for("auth.login"))
        try:
            membership_service.remove_member(g.current_user, project_id, user_id)
        except (ProjectError, MembershipError) as error:
            return _error_response(error)
        return redirect(url_for("projects.members", project_id=project_id))

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


def _member_form_values(source) -> dict:
    return {
        "user_id": source.get("user_id", ""),
        "role": source.get("role", "viewer"),
    }


def _member_form_response(project, values, errors, status_code=200):
    return (
        render_template(
            "member_form.html",
            project=project,
            values=values,
            errors=errors,
            role_options=("viewer", "contributor", "manager"),
        ),
        status_code,
    )


def _ownership_form_response(project, values, errors, status_code=200):
    return (
        render_template(
            "ownership_transfer_form.html",
            project=project,
            values=values,
            errors=errors,
        ),
        status_code,
    )


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
