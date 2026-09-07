from datetime import datetime, timedelta, timezone
import hashlib

from .auth_helpers import Browser, db_execute, db_query, mailbox_token, register, verify_account


def test_verification_activates_user_and_is_single_use():
    browser = Browser()
    account, response = register(browser)
    assert response.status == 302
    token = verify_account(browser)

    row = db_query(
        """
        SELECT u.status, u.email_verified_at, ev.used_at
        FROM users u JOIN email_verifications ev ON ev.user_id = u.id
        WHERE u.username = %s
        """,
        (account["username"],),
    )[0]
    assert row["status"] == "active"
    assert row["email_verified_at"] is not None
    assert row["used_at"] is not None

    response = browser.request(f"/verify/{token}")
    assert response.status == 409
    assert "already been used" in response.body


def test_invalid_and_expired_verification_tokens_fail():
    browser = Browser()
    response = browser.request("/verify/not-a-real-token")
    assert response.status == 400
    assert "invalid" in response.body.lower()

    account, response = register(browser)
    assert response.status == 302
    token = mailbox_token(browser)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    db_execute(
        "UPDATE email_verifications SET expires_at = %s WHERE token_hash = %s",
        (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1), token_hash),
    )

    response = browser.request(f"/verify/{token}")
    assert response.status == 400
    assert "expired" in response.body.lower()
    assert db_query("SELECT status FROM users WHERE username = %s", (account["username"],))[0]["status"] == "pending"
