import pytest

from backend.policies.project_policy import ProjectPolicy
from backend.services.membership_service import (
    MembershipConflictError,
    MembershipForbiddenError,
    MembershipService,
)


class FakeProjectService:
    def __init__(self, project):
        self.project = project

    def get_project(self, _principal, _project_id):
        return self.project


class FakeMembershipRepository:
    def __init__(self, members=None):
        self.members = dict(members or {})
        self.created = []
        self.updated = []
        self.deleted = []

    def list_members(self, _project_id):
        return list(self.members.values())

    def find_member(self, _project_id, user_id):
        return self.members.get(user_id)

    def create_member(self, project_id, user_id, role, invited_by, _now):
        if user_id in self.members:
            from backend.repositories.membership_repository import DuplicateMembershipError

            raise DuplicateMembershipError
        member = {"user_id": user_id, "username": f"user-{user_id}", "role": role}
        self.members[user_id] = member
        self.created.append((project_id, user_id, role, invited_by))

    def update_member_role(self, project_id, user_id, role):
        self.members[user_id]["role"] = role
        self.updated.append((project_id, user_id, role))

    def delete_member(self, project_id, user_id):
        self.members.pop(user_id)
        self.deleted.append((project_id, user_id))


class FakeUsers:
    def __init__(self, *user_ids):
        self.users = {
            user_id: {"id": user_id, "username": f"user-{user_id}"}
            for user_id in user_ids
        }

    def find_by_id(self, user_id):
        return self.users.get(user_id)


def make_service(principal, project=None, members=None, target_ids=(2, 3, 4, 5)):
    project = project or {
        "id": 1,
        "owner_id": 1,
        "member_role": "owner" if principal["id"] == 1 else None,
        "visibility": "private",
    }
    project["access"] = ProjectPolicy.access_for(principal, project)
    repository = FakeMembershipRepository(members)
    users = FakeUsers(*target_ids, 1, 8, 99)
    return (
        MembershipService(FakeProjectService(project), repository, users),
        repository,
    )


def member(user_id, role):
    return {"user_id": user_id, "username": f"user-{user_id}", "role": role}


def test_owner_can_invite_normal_member_and_service_sets_actor_as_inviter():
    owner = {"id": 1, "role": "user", "status": "active"}
    service, repository = make_service(owner)

    result = service.invite_member(owner, 1, 2, "viewer")

    assert result == {"user_id": 2, "username": "user-2", "role": "viewer"}
    assert repository.created == [(1, 2, "viewer", 1)]


def test_manager_cannot_invite_manager_or_change_manager_but_can_change_viewer():
    manager = {"id": 8, "role": "user", "status": "active"}
    project = {
        "id": 1,
        "owner_id": 1,
        "member_role": "manager",
        "visibility": "private",
    }
    service, repository = make_service(
        manager,
        project,
        members={2: member(2, "viewer"), 3: member(3, "manager")},
    )

    with pytest.raises(MembershipForbiddenError):
        service.invite_member(manager, 1, 4, "manager")
    with pytest.raises(MembershipForbiddenError):
        service.change_member_role(manager, 1, 3, "viewer")

    result = service.change_member_role(manager, 1, 2, "contributor")

    assert result["role"] == "contributor"
    assert repository.updated == [(1, 2, "contributor")]


def test_self_mutation_and_owner_mutation_are_rejected_without_repository_changes():
    manager = {"id": 8, "role": "user", "status": "active"}
    project = {
        "id": 1,
        "owner_id": 1,
        "member_role": "manager",
        "visibility": "private",
    }
    service, repository = make_service(
        manager,
        project,
        members={1: member(1, "owner"), 8: member(8, "manager")},
    )

    with pytest.raises(MembershipForbiddenError):
        service.change_member_role(manager, 1, 8, "viewer")
    with pytest.raises(MembershipForbiddenError):
        service.remove_member(manager, 1, 8)
    with pytest.raises(MembershipForbiddenError):
        service.remove_member(manager, 1, 1)

    assert repository.updated == []
    assert repository.deleted == []
    assert repository.members[1]["role"] == "owner"


def test_duplicate_invite_is_a_conflict_and_does_not_create_second_row():
    owner = {"id": 1, "role": "user", "status": "active"}
    service, repository = make_service(owner, members={2: member(2, "viewer")})

    with pytest.raises(MembershipConflictError):
        service.invite_member(owner, 1, 2, "contributor")

    assert list(repository.members) == [2]


def test_team_non_member_can_read_project_but_cannot_list_members():
    reader = {"id": 8, "role": "user", "status": "active"}
    project = {
        "id": 1,
        "owner_id": 1,
        "member_role": None,
        "visibility": "team",
    }
    service, _repository = make_service(reader, project, members={1: member(1, "owner")})

    with pytest.raises(MembershipForbiddenError):
        service.list_members(reader, 1)
