from flask import Blueprint, g, jsonify, request
from werkzeug.exceptions import BadRequest

from backend.services.membership_service import MembershipError, MembershipService
from backend.services.ownership_transfer_service import (
    OwnershipTransferError,
    OwnershipTransferService,
)
from backend.services.project_service import ProjectError, ProjectService


PROJECT_FIELDS = {"name", "description", "visibility"}


def create_project_api_blueprint(
    project_service: ProjectService,
    membership_service: MembershipService | None = None,
    ownership_transfer_service: OwnershipTransferService | None = None,
):
    blueprint = Blueprint("project_api", __name__, url_prefix="/api/projects")

    @blueprint.get("")
    def list_projects():
        principal, error_response = _authenticated_principal()
        if error_response:
            return error_response
        try:
            projects = project_service.list_projects(principal)
        except ProjectError as error:
            return _project_error_response(error)
        return jsonify({"data": [_serialize_project(project) for project in projects]})

    @blueprint.post("")
    def create_project():
        principal, error_response = _authenticated_principal()
        if error_response:
            return error_response
        payload, error_response = _json_payload()
        if error_response:
            return error_response
        error_response = _reject_unknown_fields(payload)
        if error_response:
            return error_response
        try:
            project = project_service.create_project(
                principal,
                payload.get("name", ""),
                payload.get("description", ""),
                payload.get("visibility", "private"),
            )
        except ProjectError as error:
            return _project_error_response(error)
        return jsonify({"data": _serialize_project(project)}), 201

    @blueprint.get("/<int:project_id>")
    def get_project(project_id):
        principal, error_response = _authenticated_principal()
        if error_response:
            return error_response
        try:
            project = project_service.get_project(principal, project_id)
        except ProjectError as error:
            return _project_error_response(error)
        return jsonify({"data": _serialize_project(project)})

    @blueprint.get("/<int:project_id>/members")
    def list_members(project_id):
        principal, error_response = _authenticated_principal()
        if error_response:
            return error_response
        try:
            members = membership_service.list_members(principal, project_id)
        except (ProjectError, MembershipError) as error:
            return _service_error_response(error)
        return jsonify({"data": [_serialize_member(member) for member in members]})

    @blueprint.post("/<int:project_id>/members")
    def invite_member(project_id):
        principal, error_response = _authenticated_principal()
        if error_response:
            return error_response
        payload, error_response = _json_payload()
        if error_response:
            return error_response
        error_response = _reject_unknown_fields(payload, {"user_id", "role"}, "membership")
        if error_response:
            return error_response
        try:
            member = membership_service.invite_member(
                principal,
                project_id,
                payload.get("user_id"),
                payload.get("role"),
            )
        except (ProjectError, MembershipError) as error:
            return _service_error_response(error)
        return jsonify({"data": _serialize_member(member)}), 201

    @blueprint.patch("/<int:project_id>/members/<int:user_id>")
    def change_member_role(project_id, user_id):
        principal, error_response = _authenticated_principal()
        if error_response:
            return error_response
        payload, error_response = _json_payload()
        if error_response:
            return error_response
        error_response = _reject_unknown_fields(payload, {"role"}, "membership")
        if error_response:
            return error_response
        try:
            member = membership_service.change_member_role(
                principal,
                project_id,
                user_id,
                payload.get("role"),
            )
        except (ProjectError, MembershipError) as error:
            return _service_error_response(error)
        return jsonify({"data": _serialize_member(member)})

    @blueprint.delete("/<int:project_id>/members/<int:user_id>")
    def remove_member(project_id, user_id):
        principal, error_response = _authenticated_principal()
        if error_response:
            return error_response
        try:
            member = membership_service.remove_member(principal, project_id, user_id)
        except (ProjectError, MembershipError) as error:
            return _service_error_response(error)
        return jsonify({"data": member})

    @blueprint.post("/<int:project_id>/ownership-transfer")
    def transfer_ownership(project_id):
        principal, error_response = _authenticated_principal()
        if error_response:
            return error_response
        payload, error_response = _json_payload()
        if error_response:
            return error_response
        error_response = _reject_unknown_fields(payload, {"target_user_id"}, "ownership")
        if error_response:
            return error_response
        try:
            project = ownership_transfer_service.transfer_ownership(
                principal,
                project_id,
                payload.get("target_user_id"),
            )
        except (ProjectError, OwnershipTransferError) as error:
            return _service_error_response(error)
        return jsonify({"data": _serialize_project(project)})

    @blueprint.patch("/<int:project_id>")
    def update_project(project_id):
        principal, error_response = _authenticated_principal()
        if error_response:
            return error_response
        payload, error_response = _json_payload()
        if error_response:
            return error_response
        error_response = _reject_unknown_fields(payload)
        if error_response:
            return error_response
        try:
            current = project_service.get_project(principal, project_id)
            project = project_service.update_project(
                principal,
                project_id,
                payload.get("name", current["name"]),
                payload.get("description", current["description"]),
                payload.get("visibility", current["visibility"]),
            )
        except ProjectError as error:
            return _project_error_response(error)
        return jsonify({"data": _serialize_project(project)})

    @blueprint.delete("/<int:project_id>")
    def delete_project(project_id):
        principal, error_response = _authenticated_principal()
        if error_response:
            return error_response
        try:
            project_service.delete_project(principal, project_id)
        except ProjectError as error:
            return _project_error_response(error)
        return jsonify({"data": {"id": project_id}})


    return blueprint


def _authenticated_principal():
    principal = getattr(g, "current_user", None)
    if principal is None or principal.get("status") != "active":
        return None, _api_error(
            "unauthenticated",
            "Authentication is required.",
            401,
        )
    return principal, None


def _json_payload():
    if request.mimetype != "application/json":
        return None, _api_error(
            "invalid_content_type",
            "Content-Type must be application/json.",
            400,
        )
    try:
        payload = request.get_json(silent=False)
    except BadRequest:
        return None, _api_error("invalid_json", "Request body must contain valid JSON.", 400)
    if not isinstance(payload, dict):
        return None, _api_error("validation_error", "Request body must be a JSON object.", 400)
    return payload, None


def _reject_unknown_fields(payload, allowed_fields=PROJECT_FIELDS, resource="project"):
    unknown_fields = sorted(set(payload) - allowed_fields)
    if not unknown_fields:
        return None
    fields = ", ".join(unknown_fields)
    return _api_error(
        "validation_error",
        f"Unsupported {resource} fields: {fields}.",
        400,
    )


def _serialize_project(project: dict) -> dict:
    return {
        "id": project["id"],
        "name": project["name"],
        "slug": project["slug"],
        "description": project["description"],
        "visibility": project["visibility"],
        "created_at": _serialize_timestamp(project.get("created_at")),
        "updated_at": _serialize_timestamp(project.get("updated_at")),
        "membership_role": project.get("membership_role"),
        "effective_role": project.get("effective_role"),
        "global_role": project.get("global_role"),
        "is_owner": project.get("is_owner", False),
        "is_global_admin": project.get("is_global_admin", False),
        "can_edit_metadata": project.get("can_edit_metadata", False),
        "can_edit_visibility": project.get("can_edit_visibility", False),
        "can_delete": project.get("can_delete", False),
        "can_manage_members": project.get("can_manage_members", False),
        "can_view_members": project.get("can_view_members", False),
        "can_transfer_ownership": project.get("can_transfer_ownership", False),
    }


def _serialize_member(member: dict) -> dict:
    return {
        "user_id": member["user_id"],
        "username": member["username"],
        "role": member["role"],
    }


def _serialize_timestamp(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _project_error_response(error: ProjectError):
    return _api_error(error.code, error.message, error.status_code)


def _service_error_response(error):
    return _api_error(error.code, error.message, error.status_code)


def _api_error(code: str, message: str, status_code: int):
    return jsonify({"error": {"code": code, "message": message}}), status_code
