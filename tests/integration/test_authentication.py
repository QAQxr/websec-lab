from .auth_helpers import Browser, account_details, db_execute, db_query, register, verify_account


def test_registration_creates_pending_hashed_account():
    browser = Browser()
    account, response = register(browser)

    assert response.status == 302
    row = db_query("SELECT status, password_hash, email_verified_at FROM users WHERE username = %s", (account["username"],))[0]
    assert row["status"] == "pending"
    assert row["email_verified_at"] is None
    assert row["password_hash"].startswith("scrypt:")
    assert account["password"] not in row["password_hash"]
    assert db_query(
        "SELECT user_id FROM email_verifications WHERE user_id = (SELECT id FROM users WHERE username = %s)",
        (account["username"],),
    )


def test_registration_rejects_duplicate_username_and_email():
    browser = Browser()
    account, response = register(browser)
    assert response.status == 302

    duplicate_username = account_details()
    duplicate_username["username"] = account["username"]
    _, response = register(browser, duplicate_username)
    assert response.status == 409
    assert "already in use" in response.body

    duplicate_email = account_details()
    duplicate_email["email"] = account["email"]
    _, response = register(browser, duplicate_email)
    assert response.status == 409


def test_registration_rejects_password_confirmation_mismatch():
    browser = Browser()
    account = account_details()
    response = browser.request(
        "/register",
        form={
            **account,
            "password_confirmation": "a different password",
        },
        follow_redirects=False,
    )

    assert response.status == 400
    assert "confirmation" in response.body.lower()


def test_login_rejects_pending_then_rotates_session_after_verification():
    browser = Browser()
    account, response = register(browser)
    assert response.status == 302

    response = browser.request(
        "/login",
        form={"identifier": account["username"], "password": account["password"]},
        follow_redirects=False,
    )
    assert response.status == 403
    assert "verify" in response.body.lower()

    verify_account(browser)
    old_session = "pre-authentication-session"
    response = browser.request(
        "/login",
        form={"identifier": account["username"], "password": account["password"]},
        headers={"Cookie": f"session={old_session}"},
        follow_redirects=False,
    )

    assert response.status == 302
    assert response.headers["Location"].endswith("/dashboard")
    assert browser.cookie_value() != old_session
    set_cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in set_cookie
    assert "SameSite=Lax" in set_cookie
    assert "Secure" not in set_cookie
    assert db_query(
        "SELECT last_login_at FROM users WHERE username = %s", (account["username"],)
    )[0]["last_login_at"] is not None


def test_wrong_password_and_locked_account_are_rejected():
    browser = Browser()
    account, response = register(browser)
    assert response.status == 302
    verify_account(browser)

    response = browser.request(
        "/login",
        form={"identifier": account["username"], "password": "wrong password"},
        follow_redirects=False,
    )
    assert response.status == 401
    assert "invalid username or password" in response.body.lower()

    db_execute(
        "UPDATE users SET status = 'locked' WHERE username = %s",
        (account["username"],),
    )
    response = browser.request(
        "/login",
        form={"identifier": account["username"], "password": account["password"]},
        follow_redirects=False,
    )
    assert response.status == 403
    assert "locked" in response.body.lower()
