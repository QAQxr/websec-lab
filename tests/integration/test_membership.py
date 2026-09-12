import json

import pytest

from .auth_helpers import Browser, db_execute, db_query, register, verify_account


def login_account(browser, account):
    response = browser.request(
        "/login",
        form={"identifier": account["username"], "password": account["password"]},
    )
    assert response.status == 200


def active_account(browser, role=None):
    account, response = register(browser)
    assert response.status == 302
    verify_account(browser, account)
    if role:
        db_execute(
            "UPDATE users SET role = %s WHERE username = %s",
            (role, account["username"]),
        )
    login_account(browser, account)
    return account


def user_id(account):
    return db_query("SELECT id FROM users WHERE username = %s", (account["username"],))[0]["id"]


def create_project(browser, name="Membership project", visibility="private"):
    response = browser.request(
        "/projects/new",
        form={
            "name": name,
            "description": "A project for membership tests.",
            "visibility": visibility,
        },
        follow_redirects=False,
    )
    assert response.status == 302, response.body
    return int(response.headers["Location"].rstrip("/").rsplit("/", 1)[-1])


def api_json(response):
    return json.loads(response.body)


def api_error(response, status, code):
    assert response.status == status, response.body
    payload = api_json(response)
    assert payload["error"]["code"] == code
    assert set(payload) == {"error"}


def api_create(browser, name="Membership API project", visibility="private"):
    response = browser.request(
        "/api/projects",
        method="POST",
        json_body={
            "name": name,
            "description": "A project for membership API tests.",
            "visibility": visibility,
        },
    )
    assert response.status == 201, response.body
    return api_json(response)["data"]


def api_invite(browser, project_id, target, role):
    return browser.request(
        f"/api/projects/{project_id}/members",
        method="POST",
        json_body={"user_id": user_id(target), "role": role},
    )


def owner_invariant(project_id):
    project = db_query("SELECT owner_id FROM projects WHERE id = %s", (project_id,))[0]
    owners = db_query(
        "SELECT user_id FROM project_members WHERE project_id = %s AND member_role = 'owner'",
        (project_id,),
    )
    assert [row["user_id"] for row in owners] == [project["owner_id"]]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/projects/1/members", None),
        ("POST", "/api/projects/1/members", {"user_id": 2, "role": "viewer"}),
        ("PATCH", "/api/projects/1/members/2", {"role": "viewer"}),
        ("DELETE", "/api/projects/1/members/2", None),
    ],
)
def test_guest_membership_api_requires_authentication(method, path, body):
    response = Browser().request(path, method=method, json_body=body, follow_redirects=False)

    api_error(response, 401, "unauthenticated")


def test_owner_html_membership_workflow_and_owner_invariant():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    project_id = create_project(owner_browser, name="HTML membership project")
    target_browser = Browser()
    target = active_account(target_browser)
    target_id = user_id(target)

    assert owner_browser.request(f"/project/{project_id}/members").status == 200
    assert owner_browser.request(f"/project/{project_id}/members/new").status == 200
    assert target["username"] not in owner_browser.request(
        f"/project/{project_id}/members"
    ).body

    response = owner_browser.request(
        f"/project/{project_id}/members",
        form={"user_id": str(target_id), "role": "viewer"},
        follow_redirects=False,
    )
    assert response.status == 302, response.body
    assert owner_browser.request(f"/project/{project_id}").status == 200
    assert target["username"] in owner_browser.request(f"/project/{project_id}").body
    owner_invariant(project_id)

    viewer_members = target_browser.request(f"/project/{project_id}/members")
    assert viewer_members.status == 200
    assert "Invite member" not in viewer_members.body
    assert target["username"] in viewer_members.body

    duplicate = owner_browser.request(
        f"/project/{project_id}/members",
        form={"user_id": str(target_id), "role": "contributor"},
        follow_redirects=False,
    )
    assert duplicate.status == 409
    assert "already" in duplicate.body.lower()
    owner_invariant(project_id)

    response = owner_browser.request(
        f"/project/{project_id}/members/{target_id}/role",
        method="POST",
        form={"role": "contributor"},
        follow_redirects=False,
    )
    assert response.status == 302
    assert db_query(
        "SELECT member_role FROM project_members WHERE project_id = %s AND user_id = %s",
        (project_id, target_id),
    )[0]["member_role"] == "contributor"
    owner_invariant(project_id)

    response = owner_browser.request(
        f"/project/{project_id}/members/{target_id}/remove",
        method="POST",
        follow_redirects=False,
    )
    assert response.status == 302
    assert db_query(
        "SELECT user_id FROM project_members WHERE project_id = %s AND user_id = %s",
        (project_id, target_id),
    ) == ()
    owner_invariant(project_id)


def test_api_owner_manager_and_admin_target_boundaries():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    project = api_create(owner_browser)
    project_id = project["id"]
    manager_browser = Browser()
    manager = active_account(manager_browser)
    viewer_browser = Browser()
    viewer = active_account(viewer_browser)
    contributor_browser = Browser()
    contributor = active_account(contributor_browser)
    manager_invited_browser = Browser()
    manager_invited = active_account(manager_invited_browser)
    admin_browser = Browser()
    admin = active_account(admin_browser, role="admin")

    assert api_invite(owner_browser, project_id, manager, "manager").status == 201
    assert api_invite(owner_browser, project_id, viewer, "viewer").status == 201
    assert api_invite(owner_browser, project_id, contributor, "contributor").status == 201
    owner_invariant(project_id)

    members = api_json(manager_browser.request(f"/api/projects/{project_id}/members"))["data"]
    assert {member["username"] for member in members} >= {
        owner["username"],
        manager["username"],
        viewer["username"],
        contributor["username"],
    }

    viewer_id = user_id(viewer)
    contributor_id = user_id(contributor)
    manager_id = user_id(manager)
    owner_id = user_id(owner)

    response = manager_browser.request(
        f"/api/projects/{project_id}/members/{viewer_id}",
        method="PATCH",
        json_body={"role": "contributor"},
    )
    assert response.status == 200
    response = manager_browser.request(
        f"/api/projects/{project_id}/members/{viewer_id}",
        method="PATCH",
        json_body={"role": "viewer"},
    )
    assert response.status == 200
    owner_invariant(project_id)

    api_error(
        manager_browser.request(
            f"/api/projects/{project_id}/members/{viewer_id}",
            method="PATCH",
            json_body={"role": "manager"},
        ),
        403,
        "forbidden",
    )
    api_error(
        manager_browser.request(
            f"/api/projects/{project_id}/members/{contributor_id}",
            method="PATCH",
            json_body={"role": "manager"},
        ),
        403,
        "forbidden",
    )
    api_error(
        manager_browser.request(
            f"/api/projects/{project_id}/members/{manager_id}",
            method="PATCH",
            json_body={"role": "viewer"},
        ),
        403,
        "forbidden",
    )
    api_error(
        manager_browser.request(
            f"/api/projects/{project_id}/members/{manager_id}",
            method="DELETE",
        ),
        403,
        "forbidden",
    )
    api_error(
        manager_browser.request(
            f"/api/projects/{project_id}/members/{owner_id}",
            method="DELETE",
        ),
        403,
        "forbidden",
    )
    api_error(api_invite(manager_browser, project_id, manager_invited, "manager"), 403, "forbidden")
    assert api_invite(manager_browser, project_id, manager_invited, "viewer").status == 201
    assert (
        manager_browser.request(
            f"/api/projects/{project_id}/members/{user_id(manager_invited)}",
            method="DELETE",
        ).status
        == 200
    )
    owner_invariant(project_id)

    admin_id = user_id(admin)
    assert db_query(
        "SELECT project_id FROM project_members WHERE project_id = %s AND user_id = %s",
        (project_id, admin_id),
    ) == ()
    assert admin_browser.request(f"/api/projects/{project_id}/members").status == 200
    response = admin_browser.request(
        f"/api/projects/{project_id}/members/{contributor_id}",
        method="PATCH",
        json_body={"role": "manager"},
    )
    assert response.status == 200
    assert (
        admin_browser.request(
            f"/api/projects/{project_id}/members/{contributor_id}",
            method="DELETE",
        ).status
        == 200
    )
    api_error(
        admin_browser.request(
            f"/api/projects/{project_id}/members/{owner_id}",
            method="DELETE",
        ),
        403,
        "forbidden",
    )
    owner_invariant(project_id)


def test_membership_api_validation_duplicate_self_and_owner_invariant():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    project = api_create(owner_browser, name="Membership validation project")
    target_browser = Browser()
    target = active_account(target_browser)
    target_id = user_id(target)
    project_id = project["id"]

    assert api_invite(owner_browser, project_id, target, "viewer").status == 201
    api_error(api_invite(owner_browser, project_id, target, "viewer"), 409, "membership_conflict")
    api_error(api_invite(owner_browser, project_id, target, "admin"), 400, "validation_error")
    api_error(
        owner_browser.request(
            f"/api/projects/{project_id}/members",
            method="POST",
            json_body={
                "user_id": target_id,
                "role": "viewer",
                "invited_by": user_id(owner),
                "actor_id": user_id(owner),
            },
        ),
        400,
        "validation_error",
    )
    api_error(
        owner_browser.request(
            f"/api/projects/{project_id}/members",
            method="POST",
            json_body={"user_id": 999999, "role": "viewer"},
        ),
        404,
        "user_not_found",
    )
    api_error(
        owner_browser.request(
            f"/api/projects/{project_id}/members",
            method="POST",
            json_body={"user_id": target_id, "role": "owner"},
        ),
        403,
        "forbidden",
    )
    api_error(
        owner_browser.request(
            f"/api/projects/{project_id}/members",
            method="POST",
            json_body={"user_id": user_id(owner), "role": "viewer"},
        ),
        403,
        "forbidden",
    )
    api_error(
        owner_browser.request(
            f"/api/projects/{project_id}/members/{user_id(owner)}",
            method="PATCH",
            json_body={"role": "manager"},
        ),
        403,
        "forbidden",
    )
    api_error(
        owner_browser.request(
            f"/api/projects/{project_id}/members/{user_id(owner)}",
            method="DELETE",
        ),
        403,
        "forbidden",
    )
    owner_invariant(project_id)

    api_error(
        target_browser.request(
            f"/api/projects/{project_id}/members/{target_id}",
            method="PATCH",
            json_body={"role": "manager"},
        ),
        403,
        "forbidden",
    )
    api_error(
        target_browser.request(
            f"/api/projects/{project_id}/members/{target_id}",
            method="DELETE",
        ),
        403,
        "forbidden",
    )
    owner_invariant(project_id)


def test_private_and_team_membership_endpoints_keep_object_scope():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    private = api_create(owner_browser, name="Private membership scope")
    team = api_create(owner_browser, name="Team membership scope", visibility="team")
    reader_browser = Browser()
    reader = active_account(reader_browser)
    global_manager_browser = Browser()
    active_account(global_manager_browser, role="manager")
    admin_browser = Browser()
    active_account(admin_browser, role="admin")

    for browser in (reader_browser, global_manager_browser):
        api_error(
            browser.request(f"/api/projects/{private['id']}/members"),
            404,
            "project_not_found",
        )
        api_error(
            browser.request(
                f"/api/projects/{private['id']}/members",
                method="POST",
                json_body={"user_id": user_id(reader), "role": "viewer"},
            ),
            404,
            "project_not_found",
        )

        assert browser.request(f"/api/projects/{team['id']}").status == 200
        api_error(
            browser.request(f"/api/projects/{team['id']}/members"),
            403,
            "forbidden",
        )
        api_error(
            browser.request(
                f"/api/projects/{team['id']}/members/{user_id(owner)}",
                method="DELETE",
            ),
            403,
            "forbidden",
        )

    assert admin_browser.request(f"/api/projects/{private['id']}/members").status == 200
    admin_target_browser = Browser()
    admin_target = active_account(admin_target_browser)
    response = api_invite(admin_browser, private["id"], admin_target, "manager")
    assert response.status == 201
    owner_invariant(private["id"])


def test_html_and_rest_membership_authorization_parity():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    project = api_create(owner_browser, name="Membership parity project")
    manager_browser = Browser()
    manager = active_account(manager_browser)
    viewer_browser = Browser()
    viewer = active_account(viewer_browser)
    assert api_invite(owner_browser, project["id"], manager, "manager").status == 201
    assert api_invite(owner_browser, project["id"], viewer, "viewer").status == 201

    viewer_id = user_id(viewer)
    html_response = manager_browser.request(
        f"/project/{project['id']}/members/{viewer_id}/role",
        method="POST",
        form={"role": "manager"},
        follow_redirects=False,
    )
    assert html_response.status == 403
    api_response = manager_browser.request(
        f"/api/projects/{project['id']}/members/{viewer_id}",
        method="PATCH",
        json_body={"role": "manager"},
    )
    api_error(api_response, 403, "forbidden")
    assert db_query(
        "SELECT member_role FROM project_members WHERE project_id = %s AND user_id = %s",
        (project["id"], viewer_id),
    )[0]["member_role"] == "viewer"

    assert viewer_browser.request(f"/project/{project['id']}/members").status == 200
    assert viewer_browser.request(f"/api/projects/{project['id']}/members").status == 200
    owner_invariant(project["id"])
