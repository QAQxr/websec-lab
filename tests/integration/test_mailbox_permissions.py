from .auth_helpers import Browser, db_execute, register, verify_account


def login_account(browser, account):
    response = browser.request(
        "/login",
        form={"identifier": account["username"], "password": account["password"]},
    )
    assert response.status == 200


def test_mailbox_requires_authentication_and_admin_role():
    anonymous = Browser()
    response = anonymous.request("/dev/mail", follow_redirects=False)
    assert response.status == 403
    assert "/verify/" not in response.body

    normal_user = Browser()
    normal_account, response = register(normal_user)
    assert response.status == 302
    verify_account(normal_user, normal_account)
    login_account(normal_user, normal_account)
    response = normal_user.request("/dev/mail", follow_redirects=False)
    assert response.status == 403
    assert "/verify/" not in response.body


def test_admin_can_view_local_mailbox_messages():
    admin_browser = Browser()
    admin_account, response = register(admin_browser)
    assert response.status == 302
    verify_account(admin_browser, admin_account)
    db_execute(
        "UPDATE users SET role = 'admin' WHERE username = %s",
        (admin_account["username"],),
    )
    login_account(admin_browser, admin_account)

    pending_browser = Browser()
    pending_account, response = register(pending_browser)
    assert response.status == 302

    response = admin_browser.request("/dev/mail")
    assert response.status == 200
    assert pending_account["email"] in response.body
    assert "/verify/" in response.body
