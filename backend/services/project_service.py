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
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ProjectNotFoundError(ProjectError):
    def __init__(self):
        super().__init__("Project not found.", 404)


class ProjectForbiddenError(ProjectError):
    def __init__(self, message: str = "You are not allowed to access this project."):
        super().__init__(message, 403)


class ProjectValidationError(ProjectError):
    pass


class ProjectConflictError(ProjectError):
    def __init__(self, message: str = "That project slug is already in use."):
        super().__init__(message, 409)


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
        rows = self.repository.list_for_user(
            principal["id"],
            is_admin=principal["role"] == "admin",
        )
        return [self._decorate(row, principal) for row in rows]

    def get_project(self, principal, project_id: int) -> dict:
        self._require_principal(principal)
        row = self.repository.find_for_user(
            self._project_id(project_id),
            principal["id"],
            is_admin=principal["role"] == "admin",
        )
        if row is None:
            raise ProjectNotFoundError()
        project = self._decorate(row, principal)
        if not self.policy.can_view(principal, project):
            raise ProjectNotFoundError()
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
        if not self.policy.can_edit(principal, project):
            raise ProjectForbiddenError("You are not allowed to edit this project.")
        name, description, visibility = self._validate_fields(name, description, visibility)
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
        if not self.policy.can_delete(principal, project):
            raise ProjectForbiddenError("Only the project owner or an administrator can delete it.")
        self.repository.delete(project["id"])

    def _require_principal(self, principal) -> None:
        if not self.policy._is_active(principal):
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
        name = (name or "").strip()
        description = (description or "").strip()
        visibility = (visibility or "private").strip().lower()
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
        role = self._effective_role(project, principal)
        project["member_role"] = role
        project["can_edit"] = self.policy.can_edit(principal, project)
        project["can_delete"] = self.policy.can_delete(principal, project)
        return project

    @staticmethod
    def _effective_role(project: dict, principal) -> str | None:
        if principal["role"] == "admin":
            return "admin"
        if principal["id"] == project["owner_id"]:
            return "owner"
        return project.get("member_role")


def build_project_service(settings: Settings) -> ProjectService:
    return ProjectService(ProjectRepository(settings))
