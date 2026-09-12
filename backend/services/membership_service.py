from backend.config import Settings
from backend.policies.project_policy import ProjectPolicy
from backend.repositories.membership_repository import (
    DuplicateMembershipError,
    MembershipNotFoundError as RepositoryMembershipNotFoundError,
    MembershipRepository,
)
from backend.repositories.user_repository import UserRepository
from backend.services.project_service import ProjectService
from backend.utils.time import utc_now


class MembershipError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "membership_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class MembershipNotFoundError(MembershipError):
    def __init__(self, message: str = "Project member not found.", code: str = "member_not_found"):
        super().__init__(message, 404, code)


class MembershipForbiddenError(MembershipError):
    def __init__(self, message: str = "You are not allowed to manage project members."):
        super().__init__(message, 403, "forbidden")


class MembershipValidationError(MembershipError):
    def __init__(self, message: str):
        super().__init__(message, 400, "validation_error")


class MembershipConflictError(MembershipError):
    def __init__(self, message: str = "That user is already a project member."):
        super().__init__(message, 409, "membership_conflict")


class MembershipService:
    ROLE_VALUES = ProjectPolicy.NORMAL_MEMBER_ROLES | {"owner"}

    def __init__(
        self,
        project_service: ProjectService,
        repository: MembershipRepository,
        users: UserRepository,
        policy: type[ProjectPolicy] = ProjectPolicy,
        clock=utc_now,
    ):
        self.project_service = project_service
        self.repository = repository
        self.users = users
        self.policy = policy
        self.clock = clock

    def list_members(self, principal, project_id: int) -> list[dict]:
        project = self._project(principal, project_id)
        if not project["access"].can_view_members:
            raise MembershipForbiddenError("You are not allowed to view project members.")
        return [
            self._decorate_member(principal, project, member)
            for member in self.repository.list_members(project["id"])
        ]

    def get_management_project(self, principal, project_id: int) -> dict:
        project = self._project(principal, project_id)
        if not project["access"].can_manage_members:
            raise MembershipForbiddenError("You are not allowed to manage project members.")
        return project

    def invite_member(self, principal, project_id: int, target_user_id, role: str) -> dict:
        project = self._project(principal, project_id)
        target_user_id = self._user_id(target_user_id)
        role = self._role(role)
        if not self.policy.can_invite_member(
            principal,
            project,
            role,
            target_user_id=target_user_id,
        ):
            raise MembershipForbiddenError("You are not allowed to invite this member.")

        target = self.users.find_by_id(target_user_id)
        if target is None:
            raise MembershipNotFoundError("User not found.", "user_not_found")
        if self.repository.find_member(project["id"], target_user_id) is not None:
            raise MembershipConflictError()
        try:
            self.repository.create_member(
                project["id"],
                target_user_id,
                role,
                principal["id"],
                self.clock(),
            )
        except DuplicateMembershipError as error:
            raise MembershipConflictError() from error
        return {
            "user_id": target_user_id,
            "username": target["username"],
            "role": role,
        }

    def change_member_role(
        self,
        principal,
        project_id: int,
        target_user_id,
        new_role: str,
    ) -> dict:
        project = self._project(principal, project_id)
        target_user_id = self._user_id(target_user_id)
        new_role = self._role(new_role)
        target = self.repository.find_member(project["id"], target_user_id)
        if target is None:
            raise MembershipNotFoundError()
        if not self.policy.can_change_member_role(
            principal,
            project,
            target_role=target["role"],
            new_role=new_role,
            target_user_id=target_user_id,
        ):
            raise MembershipForbiddenError("You are not allowed to change this member's role.")
        if target["role"] == new_role:
            raise MembershipValidationError("The member already has that role.")
        try:
            self.repository.update_member_role(project["id"], target_user_id, new_role)
        except RepositoryMembershipNotFoundError as error:
            raise MembershipNotFoundError() from error
        return {
            "user_id": target["user_id"],
            "username": target["username"],
            "role": new_role,
        }

    def remove_member(self, principal, project_id: int, target_user_id) -> dict:
        project = self._project(principal, project_id)
        target_user_id = self._user_id(target_user_id)
        target = self.repository.find_member(project["id"], target_user_id)
        if target is None:
            raise MembershipNotFoundError()
        if not self.policy.can_remove_member(
            principal,
            project,
            target_role=target["role"],
            target_user_id=target_user_id,
        ):
            raise MembershipForbiddenError("You are not allowed to remove this member.")
        try:
            self.repository.delete_member(project["id"], target_user_id)
        except RepositoryMembershipNotFoundError as error:
            raise MembershipNotFoundError() from error
        return {"user_id": target_user_id}

    def _project(self, principal, project_id: int) -> dict:
        return self.project_service.get_project(principal, self._project_id(project_id))

    def _decorate_member(self, principal, project: dict, member: dict) -> dict:
        decorated = dict(member)
        decorated["role_options"] = [
            role
            for role in sorted(self.policy.NORMAL_MEMBER_ROLES)
            if role != member["role"]
            and self.policy.can_change_member_role(
                principal,
                project,
                target_role=member["role"],
                new_role=role,
                target_user_id=member["user_id"],
            )
        ]
        decorated["can_remove"] = self.policy.can_remove_member(
            principal,
            project,
            target_role=member["role"],
            target_user_id=member["user_id"],
        )
        return decorated

    @staticmethod
    def _project_id(project_id) -> int:
        try:
            value = int(project_id)
        except (TypeError, ValueError) as error:
            raise MembershipNotFoundError("Project not found.", "project_not_found") from error
        if value <= 0:
            raise MembershipNotFoundError("Project not found.", "project_not_found")
        return value

    @staticmethod
    def _user_id(user_id) -> int:
        if isinstance(user_id, bool):
            raise MembershipValidationError("User ID must be a positive integer.")
        try:
            value = int(user_id)
        except (TypeError, ValueError) as error:
            raise MembershipValidationError("User ID must be a positive integer.") from error
        if value <= 0:
            raise MembershipValidationError("User ID must be a positive integer.")
        return value

    @classmethod
    def _role(cls, role: str) -> str:
        if not isinstance(role, str):
            raise MembershipValidationError("Member role must be a string.")
        role = role.strip().lower()
        if role not in cls.ROLE_VALUES:
            raise MembershipValidationError(
                "Member role must be viewer, contributor, or manager."
            )
        return role


def build_membership_service(
    settings: Settings,
    project_service: ProjectService,
) -> MembershipService:
    return MembershipService(
        project_service=project_service,
        repository=MembershipRepository(settings),
        users=UserRepository(settings),
    )
