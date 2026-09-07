from .auth_helpers import Browser, register, verify_account


def test_unauthenticated_dashboard_redirects_to_login():
    response = Browser().request("/dashboard", follow_redirects=False)

    assert response.status == 302
    assert response.headers["Location"].endswith("/login")


def test_authenticated_dashboard_and_profile_expose_safe_session_data_only():
    browser = Browser()
    account, response = register(browser)
    assert response.status == 302
    verify_account(browser, account)
    response = browser.request(
        "/login",
        form={"identifier": account["username"], "password": account["password"]},
    )
    assert response.status == 200

    dashboard = browser.request("/dashboard")
    assert account["username"] in dashboard.body
    assert "AcmeCloud" in dashboard.body
    assert account["password"] not in dashboard.body

    profile = browser.request("/profile")
    assert account["username"] in profile.body
    assert "user" in profile.body
    assert "session_key" not in profile.body
    assert "password_hash" not in profile.body
    assert "verification_url" not in profile.body
