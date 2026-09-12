from backend.config import Settings
from backend.policies.project_policy import ProjectPolicy
from backend.repositories.ownership_transfer_repository import (
    OwnershipTransferRepository,
    OwnershipTransferRepositoryError,
)
from backend.services.project_service import ProjectService
from backend.utils.time import utc_now


class OwnershipTransferError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "ownership_transfer_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class OwnershipTransferAuthenticationError(OwnershipTransferError):
    def __init__(self):
        super().__init__("Authentication is required.", 401, "unauthenticated")


class OwnershipTransferForbiddenError(OwnershipTransferError):
    def __init__(self, message: str = "You are not allowed to transfer project ownership."):
        super().__init__(message, 403, "forbidden")


class OwnershipTransferValidationError(OwnershipTransferError):
    def __init__(self, message: str):
        super().__init__(message, 400, "validation_error")


class OwnershipTransferNotFoundError(OwnershipTransferError):
    def __init__(self, message: str, code: str):
        super().__init__(message, 404, code)


class OwnershipTransferConflictError(OwnershipTransferError):
    def __init__(self, message: str = "Project ownership data is inconsistent."):
        super().__init__(message, 409, "ownership_invariant")


class OwnershipTransferService:
    NORMAL_TARGET_ROLES = ProjectPolicy.NORMAL_MEMBER_ROLES

    def __init__(
        self,
        project_service: ProjectService,
        repository: OwnershipTransferRepository,
        policy: type[ProjectPolicy] = ProjectPolicy,
        clock=utc_now,
    ):
        self.project_service = project_service
        self.repository = repository
        self.policy = policy
        self.clock = clock

    def get_transfer_project(self, principal, project_id: int) -> dict:
        project = self.project_service.get_project(principal, project_id)
        if not project["access"].can_transfer_ownership:
            raise OwnershipTransferForbiddenError()
        return project

    def transfer_ownership(self, principal, project_id: int, target_user_id) -> dict:
        project = self.project_service.get_project(principal, project_id)
        target_user_id = self._user_id(target_user_id)

        with self.repository.transaction() as transaction:
            locked_project = transaction.lock_project(project["id"])
            if locked_project is None:
                raise self._project_not_found()

            memberships = transaction.lock_memberships(project["id"])
            actor_user = transaction.lock_user(principal["id"])
            target_user = transaction.lock_user(target_user_id)
            if actor_user is None or actor_user["status"] != "active":
                raise OwnershipTransferAuthenticationError()
            if target_user is None:
                raise OwnershipTransferNotFoundError("User not found.", "target_user_not_found")
            if target_user_id == actor_user["id"]:
                raise OwnershipTransferForbiddenError("You cannot transfer ownership to yourself.")

            membership_by_user = {row["user_id"]: row for row in memberships}
            owner_rows = [row for row in memberships if row["member_role"] == "owner"]
            if len(owner_rows) != 1 or owner_rows[0]["user_id"] != locked_project["owner_id"]:
                raise OwnershipTransferConflictError()

            target_membership = membership_by_user.get(target_user_id)
            if target_membership is None:
                raise OwnershipTransferNotFoundError(
                    "The target user is not a member of this project.",
                    "member_not_found",
                )
            if target_user["status"] != "active":
                raise OwnershipTransferForbiddenError("The target account is not active.")

            actor_membership = membership_by_user.get(actor_user["id"])
            policy_project = {
                "id": locked_project["id"],
                "owner_id": locked_project["owner_id"],
                "visibility": locked_project["visibility"],
                "member_role": actor_membership["member_role"] if actor_membership else None,
            }
            if not self.policy.can_transfer_ownership(
                actor_user,
                policy_project,
                target_role=target_membership["member_role"],
                target_user_id=target_user_id,
            ):
                raise OwnershipTransferForbiddenError()
            if target_membership["member_role"] not in self.NORMAL_TARGET_ROLES:
                raise OwnershipTransferForbiddenError(
                    "The target user cannot become the project owner."
                )

            try:
                transaction.apply_transfer(
                    project["id"],
                    locked_project["owner_id"],
                    target_user_id,
                    self.clock(),
                )
            except OwnershipTransferRepositoryError as error:
                raise OwnershipTransferConflictError() from error
            transaction.commit()

        return self.project_service.get_project(principal, project["id"])

    @staticmethod
    def _user_id(user_id) -> int:
        if isinstance(user_id, bool):
            raise OwnershipTransferValidationError("Target user ID must be a positive integer.")
        try:
            value = int(user_id)
        except (TypeError, ValueError) as error:
            raise OwnershipTransferValidationError(
                "Target user ID must be a positive integer."
            ) from error
        if value <= 0:
            raise OwnershipTransferValidationError("Target user ID must be a positive integer.")
        return value

    @staticmethod
    def _project_not_found():
        from backend.services.project_service import ProjectNotFoundError

        return ProjectNotFoundError()


def build_ownership_transfer_service(
    settings: Settings,
    project_service: ProjectService,
) -> OwnershipTransferService:
    return OwnershipTransferService(
        project_service=project_service,
        repository=OwnershipTransferRepository(settings),
    )
