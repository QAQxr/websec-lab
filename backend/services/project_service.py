import re
import unicodedata

from backend.config import Settings
from backend.policies.project_policy import ProjectPolicy
from backend.repositories.project_repository import (
    DuplicateProjectSlugError,
    ProjectRepository,
)
from backend.utils.time import utc_now


class ProjectError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "project_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class ProjectNotFoundError(ProjectError):
    def __init__(self):
        super().__init__("Project not found.", 404, "project_not_found")


class ProjectForbiddenError(ProjectError):
    def __init__(self, message: str = "You are not allowed to access this project."):
        super().__init__(message, 403, "forbidden")


class ProjectValidationError(ProjectError):
    def __init__(self, message: str):
        super().__init__(message, 400, "validation_error")


class ProjectConflictError(ProjectError):
    def __init__(self, message: str = "That project slug is already in use."):
        super().__init__(message, 409, "project_conflict")


class ProjectService:
    VISIBILITIES = ("private", "team", "shared")
    NAME_MAX_LENGTH = 160
    DESCRIPTION_MAX_LENGTH = 10_000
    SLUG_MAX_LENGTH = 180

    def __init__(
        self,
        repository: ProjectRepository,
        policy: type[ProjectPolicy] = ProjectPolicy,
        clock=utc_now,
    ):
        self.repository = repository
        self.policy = policy
        self.clock = clock

    def list_projects(self, principal) -> list[dict]:
        self._require_principal(principal)
        scope = self.policy.query_scope(principal)
        rows = self.repository.list_for_user(
            principal["id"],
            scope=scope,
        )
        return [self._decorate(row, principal) for row in rows]

    def get_project(self, principal, project_id: int) -> dict:
        self._require_principal(principal)
        scope = self.policy.query_scope(principal)
        row = self.repository.find_for_user(
            self._project_id(project_id),
            principal["id"],
            scope=scope,
        )
        if row is None:
            raise ProjectNotFoundError()
        project = self._decorate(row, principal)
        if not project["access"].can_view:
            raise ProjectNotFoundError()
        return project

    def get_project_for_edit(self, principal, project_id: int) -> dict:
        project = self.get_project(principal, project_id)
        if not project["access"].can_edit_metadata:
            raise ProjectForbiddenError("You are not allowed to edit this project.")
        return project

    def create_project(self, principal, name: str, description: str, visibility: str) -> dict:
        self._require_principal(principal)
        if not self.policy.can_create(principal):
            raise ProjectForbiddenError("You are not allowed to create projects.")
        name, description, visibility = self._validate_fields(name, description, visibility)
        slug_base = self._slugify(name)
        now = self.clock()
        for suffix in range(1, 10_001):
            slug = self._with_suffix(slug_base, suffix)
            try:
                project_id = self.repository.create(
                    principal["id"],
                    name,
                    slug,
                    description,
                    visibility,
                    now,
                )
                return self.get_project(principal, project_id)
            except DuplicateProjectSlugError:
                continue
        raise ProjectConflictError()

    def update_project(
        self,
        principal,
        project_id: int,
        name: str,
        description: str,
        visibility: str,
    ) -> dict:
        project = self.get_project(principal, project_id)
        access = project["access"]
        if not access.can_edit_metadata:
            raise ProjectForbiddenError("You are not allowed to edit this project.")
        name, description, visibility = self._validate_fields(name, description, visibility)
        if visibility != project["visibility"] and not access.can_edit_visibility:
            raise ProjectForbiddenError("You are not allowed to change project visibility.")
        self.repository.update(
            project["id"],
            name,
            description,
            visibility,
            self.clock(),
        )
        return self.get_project(principal, project["id"])

    def delete_project(self, principal, project_id: int) -> None:
        project = self.get_project(principal, project_id)
        if not project["access"].can_delete:
            raise ProjectForbiddenError("Only the project owner or an administrator can delete it.")
        self.repository.delete(project["id"])

    def _require_principal(self, principal) -> None:
        if self.policy.query_scope(principal) == self.policy.QUERY_NONE:
            raise ProjectForbiddenError("You must be signed in to access projects.")

    @staticmethod
    def _project_id(project_id) -> int:
        try:
            value = int(project_id)
        except (TypeError, ValueError) as error:
            raise ProjectNotFoundError() from error
        if value <= 0:
            raise ProjectNotFoundError()
        return value

    @classmethod
    def _validate_fields(cls, name: str, description: str, visibility: str):
        if not isinstance(name, str):
            raise ProjectValidationError("Project name must be a string.")
        if not isinstance(description, str):
            raise ProjectValidationError("Project description must be a string.")
        if not isinstance(visibility, str):
            raise ProjectValidationError("Project visibility must be a string.")
        name = name.strip()
        description = description.strip()
        visibility = visibility.strip().lower()
        if not name:
            raise ProjectValidationError("Project name is required.")
        if len(name) > cls.NAME_MAX_LENGTH:
            raise ProjectValidationError("Project name must be 160 characters or fewer.")
        if len(description) > cls.DESCRIPTION_MAX_LENGTH:
            raise ProjectValidationError("Project description is too long.")
        if visibility not in cls.VISIBILITIES:
            raise ProjectValidationError("Choose a valid project visibility.")
        return name, description, visibility

    @classmethod
    def _slugify(cls, name: str) -> str:
        ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_name).strip("-").lower()
        slug = slug[: cls.SLUG_MAX_LENGTH].rstrip("-")
        return slug or "project"

    @classmethod
    def _with_suffix(cls, base: str, suffix: int) -> str:
        if suffix == 1:
            return base
        suffix_text = f"-{suffix}"
        return f"{base[: cls.SLUG_MAX_LENGTH - len(suffix_text)].rstrip('-')}{suffix_text}"

    def _decorate(self, row: dict, principal) -> dict:
        project = dict(row)
        settings = project.get("settings_json")
        if isinstance(settings, str):
            project["settings_json"] = settings
        access = self.policy.access_for(principal, project)
        project["access"] = access
        project["membership_role"] = access.membership_role
        project["member_role"] = access.membership_role
        project["effective_role"] = access.effective_role
        project["global_role"] = access.global_role
        project["is_owner"] = access.is_owner
        project["is_global_admin"] = access.is_global_admin
        project["can_view"] = access.can_view
        project["can_edit_metadata"] = access.can_edit_metadata
        project["can_edit_visibility"] = access.can_edit_visibility
        project["can_delete"] = access.can_delete
        project["can_manage_members"] = access.can_manage_members
        project["can_view_members"] = access.can_view_members
        project["can_transfer_ownership"] = access.can_transfer_ownership
        return project


def build_project_service(settings: Settings) -> ProjectService:
    return ProjectService(ProjectRepository(settings))
