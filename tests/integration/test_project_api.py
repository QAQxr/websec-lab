import json

import pytest

from .auth_helpers import (
    Browser,
    db_execute,
    db_query,
    register,
    verify_account,
)


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


def api_json(response):
    return json.loads(response.body)


def api_create(browser, name="API project", visibility="private", description="API description"):
    response = browser.request(
        "/api/projects",
        method="POST",
        json_body={"name": name, "description": description, "visibility": visibility},
        follow_redirects=False,
    )
    assert response.status == 201, response.body
    return api_json(response)["data"]


def assert_api_error(response, status, code):
    assert response.status == status, response.body
    payload = api_json(response)
    assert payload["error"]["code"] == code
    assert set(payload) == {"error"}


def add_members(project_id, owner, *members):
    placeholders = ", ".join(["(%s, %s, %s, %s, UTC_TIMESTAMP(6))"] * len(members))
    db_execute(
        f"""
        INSERT INTO project_members (project_id, user_id, invited_by, member_role, created_at)
        VALUES {placeholders}
        """,
        tuple(
            value
            for index, member in enumerate(members)
            for value in (project_id, user_id(member[0]), user_id(owner), member[1])
        ),
    )


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/projects", None),
        ("POST", "/api/projects", {"name": "Guest project"}),
        ("GET", "/api/projects/1", None),
        ("PATCH", "/api/projects/1", {"name": "Guest update"}),
        ("DELETE", "/api/projects/1", None),
    ],
)
def test_guest_api_requires_authentication(method, path, body):
    browser = Browser()
    response = browser.request(
        path,
        method=method,
        json_body=body,
        follow_redirects=False,
    )

    assert_api_error(response, 401, "unauthenticated")


@pytest.mark.parametrize("status", ["pending", "locked"])
def test_non_active_session_is_rejected_by_api(status):
    browser = Browser()
    account = active_account(browser)
    db_execute("UPDATE users SET status = %s WHERE username = %s", (status, account["username"]))

    response = browser.request("/api/projects", follow_redirects=False)

    assert_api_error(response, 401, "unauthenticated")


def test_owner_can_create_list_detail_patch_and_delete_project_via_api():
    browser = Browser()
    account = active_account(browser)

    created = api_create(browser, name="REST Launch Notes")
    assert created["membership_role"] == "owner"
    assert created["effective_role"] == "owner"
    assert created["global_role"] == "user"
    assert created["is_owner"] is True
    assert "owner_id" not in created
    assert "settings_json" not in created
    assert "member_role" not in created
    assert "access" not in created

    listing = browser.request("/api/projects")
    assert listing.status == 200
    assert any(project["id"] == created["id"] for project in api_json(listing)["data"])

    detail = browser.request(f"/api/projects/{created['id']}")
    assert detail.status == 200
    assert api_json(detail)["data"]["name"] == "REST Launch Notes"

    response = browser.request(
        f"/api/projects/{created['id']}",
        method="PATCH",
        json_body={"name": "REST Launch Notes Updated", "description": "Updated by API."},
    )
    assert response.status == 200
    assert api_json(response)["data"]["visibility"] == "private"

    response = browser.request(
        f"/api/projects/{created['id']}",
        method="PATCH",
        json_body={"visibility": "team"},
    )
    assert response.status == 200
    assert api_json(response)["data"]["visibility"] == "team"

    response = browser.request(
        f"/api/projects/{created['id']}",
        method="DELETE",
        follow_redirects=False,
    )
    assert response.status == 200
    assert api_json(response)["data"] == {"id": created["id"]}
    assert_api_error(browser.request(f"/api/projects/{created['id']}"), 404, "project_not_found")
    assert db_query("SELECT id FROM projects WHERE id = %s", (created["id"],)) == ()
    assert db_query("SELECT id FROM users WHERE username = %s", (account["username"],))


def test_api_validation_content_type_json_types_and_mass_assignment():
    browser = Browser()
    active_account(browser)

    response = browser.request(
        "/api/projects",
        method="POST",
        form={"name": "Form project"},
        follow_redirects=False,
    )
    assert_api_error(response, 400, "invalid_content_type")

    response = browser.request(
        "/api/projects",
        method="POST",
        raw_body="{",
        headers={"Content-Type": "application/json"},
        follow_redirects=False,
    )
    assert_api_error(response, 400, "invalid_json")

    response = browser.request(
        "/api/projects",
        method="POST",
        json_body={"name": "Mass assignment", "owner_id": 1, "global_role": "admin"},
        follow_redirects=False,
    )
    assert_api_error(response, 400, "validation_error")
    assert db_query("SELECT id FROM projects WHERE name = %s", ("Mass assignment",)) == ()

    response = browser.request(
        "/api/projects",
        method="POST",
        json_body={"name": 42, "description": [], "visibility": "private"},
        follow_redirects=False,
    )
    assert_api_error(response, 400, "validation_error")

    response = browser.request(
        "/api/projects",
        method="POST",
        json_body={"name": "Invalid visibility", "visibility": "public"},
        follow_redirects=False,
    )
    assert_api_error(response, 400, "validation_error")


def test_api_slug_collisions_keep_service_behavior():
    browser = Browser()
    active_account(browser)

    first = api_create(browser, name="Same REST Name")
    second = api_create(browser, name="Same REST Name")

    assert first["slug"] == "same-rest-name"
    assert second["slug"] == "same-rest-name-2"


def test_private_project_is_not_readable_or_mutable_through_idor():
    alice_browser = Browser()
    alice = active_account(alice_browser)
    project = api_create(alice_browser, name="Alice private project")

    bob_browser = Browser()
    active_account(bob_browser)
    api_create(bob_browser, name="Bob private project")

    assert_api_error(
        bob_browser.request(f"/api/projects/{project['id']}"),
        404,
        "project_not_found",
    )
    assert_api_error(
        bob_browser.request(
            f"/api/projects/{project['id']}",
            method="PATCH",
            json_body={"name": "IDOR update"},
        ),
        404,
        "project_not_found",
    )
    assert_api_error(
        bob_browser.request(f"/api/projects/{project['id']}", method="DELETE"),
        404,
        "project_not_found",
    )

    names = {item["name"] for item in api_json(bob_browser.request("/api/projects"))["data"]}
    assert "Alice private project" not in names
    assert api_json(alice_browser.request(f"/api/projects/{project['id']}"))["data"]["name"] == (
        "Alice private project"
    )
    assert db_query("SELECT owner_id FROM projects WHERE id = %s", (project["id"],))[0]["owner_id"] == user_id(alice)


def test_visibility_and_global_manager_api_parity():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    project = api_create(owner_browser, name="Visibility API project")

    reader_browser = Browser()
    active_account(reader_browser)
    manager_browser = Browser()
    active_account(manager_browser, role="manager")

    assert_api_error(
        reader_browser.request(f"/api/projects/{project['id']}"),
        404,
        "project_not_found",
    )
    assert_api_error(
        manager_browser.request(f"/api/projects/{project['id']}"),
        404,
        "project_not_found",
    )
    assert project["id"] not in {
        item["id"] for item in api_json(manager_browser.request("/api/projects"))["data"]
    }

    response = owner_browser.request(
        f"/api/projects/{project['id']}",
        method="PATCH",
        json_body={"visibility": "team"},
    )
    assert response.status == 200

    for browser in (reader_browser, manager_browser):
        assert browser.request(f"/api/projects/{project['id']}").status == 200
        assert project["id"] in {
            item["id"] for item in api_json(browser.request("/api/projects"))["data"]
        }
        assert_api_error(
            browser.request(
                f"/api/projects/{project['id']}",
                method="PATCH",
                json_body={"name": "Not allowed"},
            ),
            403,
            "forbidden",
        )
        assert_api_error(
            browser.request(f"/api/projects/{project['id']}", method="DELETE"),
            403,
            "forbidden",
        )

    response = owner_browser.request(
        f"/api/projects/{project['id']}",
        method="PATCH",
        json_body={"visibility": "shared"},
    )
    assert response.status == 200
    assert_api_error(
        reader_browser.request(f"/api/projects/{project['id']}"),
        404,
        "project_not_found",
    )
    assert "Visibility API project" not in {
        item["name"] for item in api_json(reader_browser.request("/api/projects"))["data"]
    }
    assert db_query("SELECT owner_id FROM projects WHERE id = %s", (project["id"],))[0]["owner_id"] == user_id(owner)


def test_manager_member_can_edit_metadata_but_not_visibility_or_delete():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    project = api_create(owner_browser, name="Manager API project")

    manager_browser = Browser()
    manager = active_account(manager_browser)
    viewer_browser = Browser()
    viewer = active_account(viewer_browser)
    contributor_browser = Browser()
    contributor = active_account(contributor_browser)
    add_members(
        project["id"],
        owner,
        (manager, "manager"),
        (viewer, "viewer"),
        (contributor, "contributor"),
    )

    for browser in (viewer_browser, contributor_browser):
        assert browser.request(f"/api/projects/{project['id']}").status == 200
        assert_api_error(
            browser.request(
                f"/api/projects/{project['id']}",
                method="PATCH",
                json_body={"name": "Read-only update"},
            ),
            403,
            "forbidden",
        )
        assert_api_error(
            browser.request(f"/api/projects/{project['id']}", method="DELETE"),
            403,
            "forbidden",
        )

    response = manager_browser.request(
        f"/api/projects/{project['id']}",
        method="PATCH",
        json_body={"name": "Manager metadata update", "description": "Allowed."},
    )
    assert response.status == 200
    assert api_json(response)["data"]["visibility"] == "private"
    assert_api_error(
        manager_browser.request(
            f"/api/projects/{project['id']}",
            method="PATCH",
            json_body={"visibility": "team"},
        ),
        403,
        "forbidden",
    )
    assert_api_error(
        manager_browser.request(f"/api/projects/{project['id']}", method="DELETE"),
        403,
        "forbidden",
    )


def test_global_admin_can_access_private_project_without_membership_row():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    project = api_create(owner_browser, name="Admin API project")

    admin_browser = Browser()
    admin = active_account(admin_browser, role="admin")
    assert db_query(
        "SELECT project_id FROM project_members WHERE project_id = %s AND user_id = %s",
        (project["id"], user_id(admin)),
    ) == ()

    detail = admin_browser.request(f"/api/projects/{project['id']}")
    assert detail.status == 200
    data = api_json(detail)["data"]
    assert data["membership_role"] is None
    assert data["effective_role"] is None
    assert data["global_role"] == "admin"
    assert data["is_global_admin"] is True
    assert data["can_edit_visibility"] is True
    assert project["id"] in {
        item["id"] for item in api_json(admin_browser.request("/api/projects"))["data"]
    }

    response = admin_browser.request(
        f"/api/projects/{project['id']}",
        method="PATCH",
        json_body={"visibility": "team"},
    )
    assert response.status == 200
    assert admin_browser.request(f"/api/projects/{project['id']}").status == 200

    response = admin_browser.request(f"/api/projects/{project['id']}", method="DELETE")
    assert response.status == 200
    assert db_query("SELECT id FROM projects WHERE id = %s", (project["id"],)) == ()
    assert db_query("SELECT id FROM users WHERE username = %s", (owner["username"],))


def test_owner_membership_mismatch_fails_closed_through_api():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    project = api_create(owner_browser, name="API ownership invariant")

    bob_browser = Browser()
    bob = active_account(bob_browser)
    db_execute(
        """
        INSERT INTO project_members (project_id, user_id, member_role, invited_by, created_at)
        VALUES (%s, %s, 'owner', %s, UTC_TIMESTAMP(6))
        """,
        (project["id"], user_id(bob), user_id(owner)),
    )

    detail = bob_browser.request(f"/api/projects/{project['id']}")
    assert detail.status == 200
    data = api_json(detail)["data"]
    assert data["membership_role"] == "owner"
    assert data["effective_role"] is None
    assert data["is_owner"] is False
    assert data["can_edit_metadata"] is False
    assert data["can_delete"] is False
    assert_api_error(
        bob_browser.request(
            f"/api/projects/{project['id']}",
            method="PATCH",
            json_body={"name": "Mismatch update"},
        ),
        403,
        "forbidden",
    )
    assert_api_error(
        bob_browser.request(f"/api/projects/{project['id']}", method="DELETE"),
        403,
        "forbidden",
    )


def test_html_and_api_return_the_same_authorization_decisions():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    project = api_create(owner_browser, name="HTML API parity project", visibility="private")

    reader_browser = Browser()
    active_account(reader_browser)
    assert reader_browser.request(f"/project/{project['id']}").status == 404
    assert reader_browser.request(f"/api/projects/{project['id']}").status == 404

    owner_browser.request(
        f"/api/projects/{project['id']}",
        method="PATCH",
        json_body={"visibility": "team"},
    )
    assert reader_browser.request(f"/project/{project['id']}").status == 200
    assert reader_browser.request(f"/api/projects/{project['id']}").status == 200
    assert reader_browser.request(f"/project/{project['id']}/edit", follow_redirects=False).status == 403
    assert_api_error(
        reader_browser.request(
            f"/api/projects/{project['id']}",
            method="PATCH",
            json_body={"name": "Parity update"},
        ),
        403,
        "forbidden",
    )
    assert db_query("SELECT owner_id FROM projects WHERE id = %s", (project["id"],))[0]["owner_id"] == user_id(owner)
