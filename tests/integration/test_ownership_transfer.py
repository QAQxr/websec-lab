import pytest

from .auth_helpers import Browser, db_execute, db_query
from .test_membership import (
    active_account,
    api_create,
    api_error,
    api_invite,
    api_json,
    create_project,
    owner_invariant,
    user_id,
)


def test_owner_can_transfer_via_rest_and_old_owner_becomes_manager():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    target_browser = Browser()
    target = active_account(target_browser)
    project = api_create(owner_browser, name="REST ownership transfer")
    assert api_invite(owner_browser, project["id"], target, "viewer").status == 201

    response = owner_browser.request(
        f"/api/projects/{project['id']}/ownership-transfer",
        method="POST",
        json_body={"target_user_id": user_id(target)},
    )
    assert response.status == 200, response.body
    transferred = api_json(response)["data"]
    assert transferred["is_owner"] is False
    assert transferred["membership_role"] == "manager"
    assert transferred["effective_role"] == "manager"
    assert transferred["global_role"] == "user"

    target_view = api_json(
        target_browser.request(f"/api/projects/{project['id']}")
    )["data"]
    assert target_view["is_owner"] is True
    assert target_view["membership_role"] == "owner"
    assert target_view["effective_role"] == "owner"

    old_owner_view = api_json(
        owner_browser.request(f"/api/projects/{project['id']}")
    )["data"]
    assert old_owner_view["is_owner"] is False
    assert old_owner_view["membership_role"] == "manager"
    assert old_owner_view["effective_role"] == "manager"
    assert old_owner_view["can_manage_members"] is True
    assert db_query(
        "SELECT owner_id FROM projects WHERE id = %s",
        (project["id"],),
    )[0]["owner_id"] == user_id(target)
    owner_invariant(project["id"])


def test_global_admin_can_transfer_without_project_membership():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    target_browser = Browser()
    target = active_account(target_browser)
    project = api_create(owner_browser, name="Admin ownership transfer")
    assert api_invite(owner_browser, project["id"], target, "manager").status == 201
    admin_browser = Browser()
    admin = active_account(admin_browser, role="admin")

    assert db_query(
        "SELECT project_id FROM project_members WHERE project_id = %s AND user_id = %s",
        (project["id"], user_id(admin)),
    ) == ()

    response = admin_browser.request(
        f"/api/projects/{project['id']}/ownership-transfer",
        method="POST",
        json_body={"target_user_id": user_id(target)},
    )
    assert response.status == 200, response.body
    assert api_json(response)["data"]["is_global_admin"] is True
    owner_invariant(project["id"])


def test_project_members_and_global_manager_are_denied_but_team_scope_is_preserved():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    project = api_create(owner_browser, name="Role boundary transfer")
    manager_browser = Browser()
    manager = active_account(manager_browser)
    contributor_browser = Browser()
    contributor = active_account(contributor_browser)
    viewer_browser = Browser()
    viewer = active_account(viewer_browser)
    assert api_invite(owner_browser, project["id"], manager, "manager").status == 201
    assert api_invite(owner_browser, project["id"], contributor, "contributor").status == 201
    assert api_invite(owner_browser, project["id"], viewer, "viewer").status == 201

    for browser in (manager_browser, contributor_browser, viewer_browser):
        api_error(
            browser.request(
                f"/api/projects/{project['id']}/ownership-transfer",
                method="POST",
                json_body={"target_user_id": user_id(viewer)},
            ),
            403,
            "forbidden",
        )

    team_project = api_create(owner_browser, name="Team transfer scope", visibility="team")
    assert api_invite(owner_browser, team_project["id"], viewer, "viewer").status == 201
    global_manager_browser = Browser()
    active_account(global_manager_browser, role="manager")
    assert global_manager_browser.request(f"/api/projects/{team_project['id']}").status == 200
    api_error(
        global_manager_browser.request(
            f"/api/projects/{team_project['id']}/ownership-transfer",
            method="POST",
            json_body={"target_user_id": user_id(viewer)},
        ),
        403,
        "forbidden",
    )
    owner_invariant(project["id"])
    owner_invariant(team_project["id"])


@pytest.mark.parametrize("status", ["pending", "locked"])
def test_guest_pending_and_locked_actors_are_rejected(status):
    browser = Browser()
    if status == "pending":
        response = browser.request(
            "/api/projects/1/ownership-transfer",
            method="POST",
            json_body={"target_user_id": 2},
            follow_redirects=False,
        )
        api_error(response, 401, "unauthenticated")
        return

    account = active_account(browser)
    db_execute("UPDATE users SET status = %s WHERE username = %s", (status, account["username"]))
    api_error(
        browser.request(
            "/api/projects/1/ownership-transfer",
            method="POST",
            json_body={"target_user_id": 2},
            follow_redirects=False,
        ),
        401,
        "unauthenticated",
    )


def test_target_constraints_self_owner_nonmember_and_inactive_are_denied():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    target_browser = Browser()
    target = active_account(target_browser)
    inactive_browser = Browser()
    inactive = active_account(inactive_browser)
    project = api_create(owner_browser, name="Target constraints transfer")
    assert api_invite(owner_browser, project["id"], target, "viewer").status == 201
    assert api_invite(owner_browser, project["id"], inactive, "contributor").status == 201

    api_error(
        owner_browser.request(
            f"/api/projects/{project['id']}/ownership-transfer",
            method="POST",
            json_body={"target_user_id": user_id(owner)},
        ),
        403,
        "forbidden",
    )
    api_error(
        owner_browser.request(
            f"/api/projects/{project['id']}/ownership-transfer",
            method="POST",
            json_body={"target_user_id": 999999},
        ),
        404,
        "target_user_not_found",
    )
    db_execute("UPDATE users SET status = 'locked' WHERE id = %s", (user_id(inactive),))
    api_error(
        owner_browser.request(
            f"/api/projects/{project['id']}/ownership-transfer",
            method="POST",
            json_body={"target_user_id": user_id(inactive)},
        ),
        403,
        "forbidden",
    )
    owner_invariant(project["id"])


def test_private_and_team_project_object_scope_blocks_idor_transfer():
    alice_browser = Browser()
    alice = active_account(alice_browser)
    private_project = api_create(alice_browser, name="Private transfer target")
    team_project = api_create(alice_browser, name="Team transfer target", visibility="team")
    bob_browser = Browser()
    bob = active_account(bob_browser)

    api_error(
        bob_browser.request(
            f"/api/projects/{private_project['id']}/ownership-transfer",
            method="POST",
            json_body={"target_user_id": user_id(bob)},
        ),
        404,
        "project_not_found",
    )
    assert bob_browser.request(f"/api/projects/{team_project['id']}").status == 200
    api_error(
        bob_browser.request(
            f"/api/projects/{team_project['id']}/ownership-transfer",
            method="POST",
            json_body={"target_user_id": user_id(alice)},
        ),
        403,
        "forbidden",
    )


def test_html_and_rest_transfer_endpoints_share_the_same_policy_decision():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    manager_browser = Browser()
    manager = active_account(manager_browser)
    viewer_browser = Browser()
    viewer = active_account(viewer_browser)
    project = api_create(owner_browser, name="Parity transfer project")
    assert api_invite(owner_browser, project["id"], manager, "manager").status == 201
    assert api_invite(owner_browser, project["id"], viewer, "viewer").status == 201

    html_response = manager_browser.request(
        f"/project/{project['id']}/ownership/transfer",
        form={"target_user_id": str(user_id(viewer))},
        follow_redirects=False,
    )
    assert html_response.status == 403
    api_error(
        manager_browser.request(
            f"/api/projects/{project['id']}/ownership-transfer",
            method="POST",
            json_body={"target_user_id": user_id(viewer)},
        ),
        403,
        "forbidden",
    )
    assert owner_browser.request(f"/project/{project['id']}/ownership/transfer").status == 200

    html_transfer_project = create_project(owner_browser, name="HTML transfer project")
    html_target_browser = Browser()
    html_target = active_account(html_target_browser)
    assert api_invite(owner_browser, html_transfer_project, html_target, "viewer").status == 201
    html_response = owner_browser.request(
        f"/project/{html_transfer_project}/ownership/transfer",
        form={"target_user_id": str(user_id(html_target))},
        follow_redirects=False,
    )
    assert html_response.status == 302
    owner_invariant(html_transfer_project)


def test_broken_owner_invariant_fails_closed_without_repair():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    target_browser = Browser()
    target = active_account(target_browser)
    project = api_create(owner_browser, name="Broken invariant transfer")
    assert api_invite(owner_browser, project["id"], target, "viewer").status == 201
    db_execute(
        "UPDATE project_members SET member_role = 'owner' WHERE project_id = %s AND user_id = %s",
        (project["id"], user_id(target)),
    )

    api_error(
        owner_browser.request(
            f"/api/projects/{project['id']}/ownership-transfer",
            method="POST",
            json_body={"target_user_id": user_id(target)},
        ),
        409,
        "ownership_invariant",
    )
    assert db_query("SELECT owner_id FROM projects WHERE id = %s", (project["id"],))[0]["owner_id"] == user_id(owner)
