from backend.policies.project_policy import ProjectPolicy


def principal(user_id=7, role="user", status="active"):
    return {"id": user_id, "role": role, "status": status}


def project(owner_id=7, member_role=None):
    return {"id": 1, "owner_id": owner_id, "member_role": member_role}


def test_owner_can_edit_and_delete_owned_project():
    user = principal()
    resource = project()

    assert ProjectPolicy.can_view(user, resource)
    assert ProjectPolicy.can_edit(user, resource)
    assert ProjectPolicy.can_delete(user, resource)


def test_manager_can_edit_but_not_delete_project():
    user = principal(user_id=8)
    resource = project(member_role="manager")

    assert ProjectPolicy.can_view(user, resource)
    assert ProjectPolicy.can_edit(user, resource)
    assert not ProjectPolicy.can_delete(user, resource)


def test_viewer_is_read_only_and_global_manager_needs_membership():
    viewer = principal(user_id=8)
    manager = principal(user_id=9, role="manager")

    assert ProjectPolicy.can_view(viewer, project(member_role="viewer"))
    assert not ProjectPolicy.can_edit(viewer, project(member_role="viewer"))
    assert not ProjectPolicy.can_view(manager, project(owner_id=7))


def test_admin_can_manage_any_project_but_inactive_users_cannot():
    admin = principal(user_id=1, role="admin")
    inactive = principal(status="locked")
    resource = project(owner_id=99)

    assert ProjectPolicy.can_view(admin, resource)
    assert ProjectPolicy.can_edit(admin, resource)
    assert ProjectPolicy.can_delete(admin, resource)
    assert not ProjectPolicy.can_create(inactive)
    assert not ProjectPolicy.can_view(inactive, resource)
