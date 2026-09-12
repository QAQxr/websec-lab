from copy import deepcopy
from datetime import datetime

import pytest

from backend.policies.project_policy import ProjectPolicy
from backend.repositories.ownership_transfer_repository import OwnershipTransferRepositoryError
from backend.services.ownership_transfer_service import (
    OwnershipTransferConflictError,
    OwnershipTransferForbiddenError,
    OwnershipTransferNotFoundError,
    OwnershipTransferService,
)


class FakeProjectService:
    def __init__(self, project):
        self.project = project

    def get_project(self, _principal, _project_id):
        return self.project


class FakeTransaction:
    def __init__(self, repository):
        self.repository = repository
        self.snapshot = None
        self.committed = False

    def __enter__(self):
        self.snapshot = deepcopy((self.repository.project, self.repository.members))
        return self

    def __exit__(self, exception_type, _exception, _traceback):
        if exception_type is not None or not self.committed:
            self.repository.project, self.repository.members = deepcopy(self.snapshot)
        return False

    def lock_project(self, _project_id):
        return dict(self.repository.project)

    def lock_memberships(self, _project_id):
        return [dict(member) for member in self.repository.members.values()]

    def lock_user(self, user_id):
        user = self.repository.users.get(user_id)
        return dict(user) if user else None

    def apply_transfer(self, _project_id, old_owner_id, new_owner_id, _now):
        self.repository.project["owner_id"] = new_owner_id
        self.repository.members[old_owner_id]["member_role"] = "manager"
        self.repository.members[new_owner_id]["member_role"] = "owner"
        if self.repository.fail_on_apply:
            raise OwnershipTransferRepositoryError

    def commit(self):
        self.committed = True


class FakeRepository:
    def __init__(self, project, members, users, fail_on_apply=False):
        self.project = project
        self.members = members
        self.users = users
        self.fail_on_apply = fail_on_apply

    def transaction(self):
        return FakeTransaction(self)


def make_service(principal, actor_role, members, users=None, fail_on_apply=False):
    project = {
        "id": 1,
        "owner_id": 1,
        "member_role": actor_role,
        "visibility": "private",
    }
    project["access"] = ProjectPolicy.access_for(principal, project)
    repository = FakeRepository(
        project,
        {user_id: {"user_id": user_id, "member_role": role} for user_id, role in members.items()},
        users
        or {
            1: {"id": 1, "role": "user", "status": "active"},
            2: {"id": 2, "role": "user", "status": "active"},
            3: {"id": 3, "role": "user", "status": "active"},
            99: {"id": 99, "role": "admin", "status": "active"},
        },
        fail_on_apply=fail_on_apply,
    )
    return OwnershipTransferService(
        FakeProjectService(project),
        repository,
        clock=lambda: datetime(2026, 1, 1),
    ), repository


def test_owner_transfer_changes_project_and_both_memberships():
    owner = {"id": 1, "role": "user", "status": "active"}
    service, repository = make_service(owner, "owner", {1: "owner", 2: "viewer"})

    service.transfer_ownership(owner, 1, 2)

    assert repository.project["owner_id"] == 2
    assert repository.members[1]["member_role"] == "manager"
    assert repository.members[2]["member_role"] == "owner"


def test_global_admin_can_transfer_without_project_membership():
    admin = {"id": 99, "role": "admin", "status": "active"}
    service, repository = make_service(admin, None, {1: "owner", 2: "manager"})

    service.transfer_ownership(admin, 1, 2)

    assert repository.project["owner_id"] == 2
    assert repository.members[1]["member_role"] == "manager"
    assert repository.members[2]["member_role"] == "owner"


def test_project_manager_cannot_transfer_and_state_is_unchanged():
    manager = {"id": 3, "role": "user", "status": "active"}
    service, repository = make_service(
        manager,
        "manager",
        {1: "owner", 2: "viewer", 3: "manager"},
    )
    before = deepcopy((repository.project, repository.members))

    with pytest.raises(OwnershipTransferForbiddenError):
        service.transfer_ownership(manager, 1, 2)

    assert (repository.project, repository.members) == before


def test_target_must_be_a_member_and_active():
    owner = {"id": 1, "role": "user", "status": "active"}
    service, _repository = make_service(owner, "owner", {1: "owner"})

    with pytest.raises(OwnershipTransferNotFoundError):
        service.transfer_ownership(owner, 1, 2)

    inactive_service, _repository = make_service(
        owner,
        "owner",
        {1: "owner", 2: "viewer"},
        users={
            1: {"id": 1, "role": "user", "status": "active"},
            2: {"id": 2, "role": "user", "status": "locked"},
        },
    )
    with pytest.raises(OwnershipTransferForbiddenError):
        inactive_service.transfer_ownership(owner, 1, 2)


def test_invariant_failure_and_mid_transaction_failure_roll_back():
    owner = {"id": 1, "role": "user", "status": "active"}
    broken_service, broken_repository = make_service(owner, "owner", {1: "manager", 2: "viewer"})
    broken_before = deepcopy((broken_repository.project, broken_repository.members))
    with pytest.raises(OwnershipTransferConflictError):
        broken_service.transfer_ownership(owner, 1, 2)
    assert (broken_repository.project, broken_repository.members) == broken_before

    failing_service, failing_repository = make_service(
        owner,
        "owner",
        {1: "owner", 2: "viewer"},
        fail_on_apply=True,
    )
    failing_before = deepcopy((failing_repository.project, failing_repository.members))
    with pytest.raises(OwnershipTransferConflictError):
        failing_service.transfer_ownership(owner, 1, 2)
    assert (failing_repository.project, failing_repository.members) == failing_before
