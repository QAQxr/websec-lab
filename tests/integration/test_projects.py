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


def create_project(browser, name="Test project", visibility="private"):
    response = browser.request(
        "/projects/new",
        form={"name": name, "description": "A project for integration tests.", "visibility": visibility},
        follow_redirects=False,
    )
    assert response.status == 302
    return response.headers["Location"]


def test_unauthenticated_project_pages_redirect_to_login():
    browser = Browser()

    response = browser.request("/projects", follow_redirects=False)
    assert response.status == 302
    assert response.headers["Location"].endswith("/login")

    response = browser.request("/projects/new", follow_redirects=False)
    assert response.status == 302
    assert response.headers["Location"].endswith("/login")


def test_owner_can_create_list_edit_and_delete_project():
    browser = Browser()
    account = active_account(browser)

    location = create_project(browser, name="Launch Notes")
    assert "/project/" in location

    listing = browser.request("/projects")
    assert listing.status == 200
    assert "Launch Notes" in listing.body
    assert "launch-notes" in listing.body

    project_id = int(location.rstrip("/").rsplit("/", 1)[-1])
    detail = browser.request(f"/project/{project_id}")
    assert detail.status == 200
    assert account["username"] not in detail.body
    assert "owner" in detail.body

    response = browser.request(
        f"/project/{project_id}/edit",
        form={
            "name": "Launch Notes Updated",
            "description": "Updated description.",
            "visibility": "team",
        },
        follow_redirects=False,
    )
    assert response.status == 302
    assert browser.request(f"/project/{project_id}").body.find("Launch Notes Updated") >= 0

    response = browser.request(f"/project/{project_id}/delete", method="POST", follow_redirects=False)
    assert response.status == 302
    assert browser.request(f"/project/{project_id}").status == 404
    assert db_query("SELECT id FROM projects WHERE id = %s", (project_id,)) == ()


def test_manager_can_edit_but_viewer_cannot_edit_or_delete():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    location = create_project(owner_browser, name="Shared Workspace")
    project_id = int(location.rstrip("/").rsplit("/", 1)[-1])

    manager_browser = Browser()
    manager = active_account(manager_browser)
    viewer_browser = Browser()
    viewer = active_account(viewer_browser)
    db_execute(
        """
        INSERT INTO project_members (project_id, user_id, member_role, invited_by, created_at)
        VALUES (%s, %s, 'manager', %s, UTC_TIMESTAMP(6)), (%s, %s, 'viewer', %s, UTC_TIMESTAMP(6))
        """,
        (project_id, user_id(manager), user_id(owner), project_id, user_id(viewer), user_id(owner)),
    )

    response = manager_browser.request(
        f"/project/{project_id}/edit",
        form={"name": "Manager Updated", "description": "Manager edit.", "visibility": "shared"},
        follow_redirects=False,
    )
    assert response.status == 302

    response = viewer_browser.request(
        f"/project/{project_id}/edit",
        form={"name": "Viewer Updated", "description": "Nope", "visibility": "private"},
        follow_redirects=False,
    )
    assert response.status == 403
    assert "not allowed" in response.body.lower()

    response = viewer_browser.request(f"/project/{project_id}/delete", method="POST", follow_redirects=False)
    assert response.status == 403

    assert manager_browser.request(f"/project/{project_id}").status == 200
    assert viewer_browser.request(f"/project/{project_id}").status == 200


def test_non_member_cannot_view_project_and_global_manager_is_not_project_manager():
    owner_browser = Browser()
    owner = active_account(owner_browser)
    location = create_project(owner_browser, name="Private Workspace")
    project_id = int(location.rstrip("/").rsplit("/", 1)[-1])

    user_browser = Browser()
    active_account(user_browser)
    assert user_browser.request(f"/project/{project_id}").status == 404

    manager_browser = Browser()
    active_account(manager_browser, role="manager")
    assert manager_browser.request(f"/project/{project_id}").status == 404

    assert db_query(
        "SELECT owner_id, name FROM projects WHERE id = %s",
        (project_id,),
    )[0]["owner_id"] == user_id(owner)


def test_project_validation_and_slug_collisions_are_handled():
    browser = Browser()
    active_account(browser)
    create_project(browser, name="Same Name")

    response = browser.request(
        "/projects/new",
        form={"name": "Same Name", "description": "Second.", "visibility": "private"},
        follow_redirects=False,
    )
    assert response.status == 302
    assert [row["slug"] for row in db_query(
        "SELECT slug FROM projects WHERE name = %s ORDER BY id",
        ("Same Name",),
    )] == ["same-name", "same-name-2"]

    response = browser.request(
        "/projects/new",
        form={"name": "", "description": "Invalid.", "visibility": "private"},
        follow_redirects=False,
    )
    assert response.status == 400
    assert "name is required" in response.body.lower()
