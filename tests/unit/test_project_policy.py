from backend.policies.project_policy import ProjectPolicy


def principal(user_id=7, role="user", status="active"):
    return {"id": user_id, "role": role, "status": status}


def project(owner_id=7, member_role=None, visibility="private"):
    return {
        "id": 1,
        "owner_id": owner_id,
        "member_role": member_role,
        "visibility": visibility,
    }


def test_owner_has_owner_capabilities_but_admin_is_not_a_membership_role():
    owner_access = ProjectPolicy.access_for(principal(), project())
    admin_access = ProjectPolicy.access_for(
        principal(user_id=99, role="admin"),
        project(owner_id=7),
    )

    assert owner_access.is_owner
    assert owner_access.membership_role is None
    assert owner_access.effective_role == "owner"
    assert owner_access.can_view
    assert owner_access.can_edit_metadata
    assert owner_access.can_edit_visibility
    assert owner_access.can_delete
    assert owner_access.can_manage_members
    assert admin_access.is_global_admin
    assert admin_access.membership_role is None
    assert admin_access.effective_role is None
    assert admin_access.can_view
    assert admin_access.can_edit_metadata
    assert admin_access.can_delete


def test_manager_membership_is_scoped_to_metadata_and_member_management():
    access = ProjectPolicy.access_for(
        principal(user_id=8),
        project(owner_id=7, member_role="manager"),
    )

    assert access.can_view
    assert access.can_edit_metadata
    assert not access.can_edit_visibility
    assert not access.can_delete
    assert access.can_manage_members
    assert access.can_invite_viewer
    assert access.can_invite_contributor
    assert not access.can_invite_manager
    assert not access.can_invite_owner
    assert ProjectPolicy.can_change_member_role(
        principal(user_id=8),
        project(owner_id=7, member_role="manager"),
        target_role="viewer",
        new_role="contributor",
    )
    assert not ProjectPolicy.can_change_member_role(
        principal(user_id=8),
        project(owner_id=7, member_role="manager"),
        target_role="manager",
        new_role="viewer",
    )
    assert ProjectPolicy.can_remove_member(
        principal(user_id=8),
        project(owner_id=7, member_role="manager"),
        target_role="viewer",
    )
    assert not ProjectPolicy.can_remove_member(
        principal(user_id=8),
        project(owner_id=7, member_role="manager"),
        target_role="manager",
    )


def test_viewer_and_contributor_are_read_only():
    for member_role in ("viewer", "contributor"):
        access = ProjectPolicy.access_for(
            principal(user_id=8),
            project(owner_id=7, member_role=member_role),
        )

        assert access.can_view
        assert not access.can_edit_metadata
        assert not access.can_edit_visibility
        assert not access.can_delete
        assert not access.can_manage_members


def test_global_manager_without_membership_is_team_read_only_only():
    manager = principal(user_id=8, role="manager")

    private_access = ProjectPolicy.access_for(manager, project(owner_id=7, visibility="private"))
    team_access = ProjectPolicy.access_for(manager, project(owner_id=7, visibility="team"))
    shared_access = ProjectPolicy.access_for(manager, project(owner_id=7, visibility="shared"))

    assert not private_access.can_view
    assert team_access.can_view
    assert not team_access.can_edit_metadata
    assert not team_access.can_manage_members
    assert not shared_access.can_view


def test_visibility_requires_active_authentication_and_shared_is_not_public():
    for status in ("pending", "locked"):
        access = ProjectPolicy.access_for(
            principal(status=status),
            project(owner_id=99, visibility="team"),
        )
        assert access.authentication_state == status
        assert not access.can_view
        assert ProjectPolicy.query_scope(principal(status=status)) == ProjectPolicy.QUERY_NONE

    guest_access = ProjectPolicy.access_for(None, project(owner_id=99, visibility="team"))
    assert guest_access.authentication_state == "guest"
    assert not guest_access.can_view
    assert ProjectPolicy.query_scope(None) == ProjectPolicy.QUERY_NONE

    shared_access = ProjectPolicy.access_for(
        principal(user_id=8),
        project(owner_id=7, visibility="shared"),
    )
    assert not shared_access.can_view


def test_owner_membership_mismatch_fails_closed_for_owner_capabilities():
    bob = principal(user_id=8)
    mismatched = project(owner_id=7, member_role="owner")

    access = ProjectPolicy.access_for(bob, mismatched)

    assert not access.is_owner
    assert access.membership_role == "owner"
    assert access.effective_role is None
    assert access.can_view
    assert not access.can_edit_metadata
    assert not access.can_delete
    assert not access.can_manage_members
    assert not access.can_transfer_ownership


def test_owner_and_admin_can_express_future_ownership_capability():
    owner = principal(user_id=7)
    admin = principal(user_id=99, role="admin")
    resource = project(owner_id=7)

    assert ProjectPolicy.access_for(owner, resource).can_transfer_ownership
    assert ProjectPolicy.access_for(admin, resource).can_transfer_ownership
    assert ProjectPolicy.access_for(owner, resource).can_assign_owner
    assert ProjectPolicy.access_for(admin, resource).can_assign_owner


def test_repository_scope_is_explicitly_derived_by_policy():
    assert ProjectPolicy.query_scope(principal()) == ProjectPolicy.QUERY_AUTHENTICATED
    assert ProjectPolicy.query_scope(principal(role="manager")) == ProjectPolicy.QUERY_AUTHENTICATED
    assert ProjectPolicy.query_scope(principal(role="admin")) == ProjectPolicy.QUERY_GLOBAL


def test_membership_visibility_is_not_granted_by_team_project_visibility():
    member_access = ProjectPolicy.access_for(
        principal(user_id=8),
        project(owner_id=7, member_role="viewer", visibility="team"),
    )
    team_non_member_access = ProjectPolicy.access_for(
        principal(user_id=8),
        project(owner_id=7, visibility="team"),
    )
    manager_non_member_access = ProjectPolicy.access_for(
        principal(user_id=8, role="manager"),
        project(owner_id=7, visibility="team"),
    )
    admin_access = ProjectPolicy.access_for(
        principal(user_id=99, role="admin"),
        project(owner_id=7, visibility="private"),
    )

    assert member_access.can_view_members
    assert not team_non_member_access.can_view_members
    assert not manager_non_member_access.can_view_members
    assert admin_access.can_view_members


def test_owner_target_constraints_allow_only_normal_member_mutations():
    owner = principal(user_id=7)
    resource = project(owner_id=7)

    assert ProjectPolicy.can_invite_member(owner, resource, "manager", target_user_id=8)
    assert not ProjectPolicy.can_invite_member(owner, resource, "owner", target_user_id=8)
    assert ProjectPolicy.can_change_member_role(
        owner,
        resource,
        target_role="viewer",
        new_role="manager",
        target_user_id=8,
    )
    assert not ProjectPolicy.can_change_member_role(
        owner,
        resource,
        target_role="viewer",
        new_role="viewer",
        target_user_id=8,
    )
    assert not ProjectPolicy.can_change_member_role(
        owner,
        resource,
        target_role="owner",
        new_role="manager",
        target_user_id=8,
    )
    assert not ProjectPolicy.can_remove_member(
        owner,
        resource,
        target_role="owner",
        target_user_id=7,
    )


def test_manager_target_constraints_are_limited_to_viewer_and_contributor():
    manager = principal(user_id=8)
    resource = project(owner_id=7, member_role="manager")

    assert ProjectPolicy.can_invite_member(manager, resource, "viewer", target_user_id=9)
    assert ProjectPolicy.can_invite_member(manager, resource, "contributor", target_user_id=9)
    assert not ProjectPolicy.can_invite_member(manager, resource, "manager", target_user_id=9)
    assert ProjectPolicy.can_change_member_role(
        manager,
        resource,
        target_role="viewer",
        new_role="contributor",
        target_user_id=9,
    )
    assert not ProjectPolicy.can_change_member_role(
        manager,
        resource,
        target_role="viewer",
        new_role="manager",
        target_user_id=9,
    )
    assert not ProjectPolicy.can_change_member_role(
        manager,
        resource,
        target_role="manager",
        new_role="viewer",
        target_user_id=9,
    )
    assert ProjectPolicy.can_remove_member(
        manager,
        resource,
        target_role="contributor",
        target_user_id=9,
    )
    assert not ProjectPolicy.can_remove_member(
        manager,
        resource,
        target_role="manager",
        target_user_id=9,
    )


def test_admin_can_manage_normal_roles_without_project_membership_but_not_owner():
    admin = principal(user_id=99, role="admin")
    resource = project(owner_id=7)

    assert ProjectPolicy.can_invite_member(admin, resource, "manager", target_user_id=8)
    assert ProjectPolicy.can_change_member_role(
        admin,
        resource,
        target_role="manager",
        new_role="viewer",
        target_user_id=8,
    )
    assert ProjectPolicy.can_remove_member(
        admin,
        resource,
        target_role="manager",
        target_user_id=8,
    )
    assert not ProjectPolicy.can_change_member_role(
        admin,
        resource,
        target_role="owner",
        new_role="viewer",
        target_user_id=7,
    )
    assert not ProjectPolicy.can_remove_member(
        admin,
        resource,
        target_role="owner",
        target_user_id=7,
    )


def test_membership_policy_rejects_self_mutation():
    manager = principal(user_id=8)
    resource = project(owner_id=7, member_role="manager")

    assert not ProjectPolicy.can_invite_member(manager, resource, "viewer", target_user_id=8)
    assert not ProjectPolicy.can_change_member_role(
        manager,
        resource,
        target_role="manager",
        new_role="viewer",
        target_user_id=8,
    )
    assert not ProjectPolicy.can_remove_member(
        manager,
        resource,
        target_role="manager",
        target_user_id=8,
    )
