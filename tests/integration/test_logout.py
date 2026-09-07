import time

import redis

from backend.config import Settings
from backend.repositories.session_repository import SESSION_PREFIX
from .auth_helpers import Browser, db_query, register, verify_account


def login_verified_account(browser):
    account, response = register(browser)
    assert response.status == 302
    verify_account(browser, account)
    response = browser.request(
        "/login",
        form={"identifier": account["username"], "password": account["password"]},
        follow_redirects=False,
    )
    assert response.status == 302
    return account, browser.cookie_value()


def test_logout_invalidates_server_side_session_and_expires_cookie():
    browser = Browser()
    account, session_key = login_verified_account(browser)
    response = browser.request("/logout", method="POST", follow_redirects=False)

    assert response.status == 302
    assert "Max-Age=0" in response.headers["Set-Cookie"]
    assert not db_query("SELECT id FROM sessions WHERE session_key = %s", (session_key,))

    old_cookie_browser = Browser()
    response = old_cookie_browser.request(
        "/dashboard",
        headers={"Cookie": f"session={session_key}"},
        follow_redirects=False,
    )
    assert response.status == 302
    assert response.headers["Location"].endswith("/login")
    assert account["username"]


def test_expired_redis_session_is_rejected_and_removed_from_mysql():
    browser = Browser()
    account, session_key = login_verified_account(browser)
    settings = Settings.from_env()
    store = redis.Redis(host=settings.redis_host, port=settings.redis_port, db=settings.redis_db)
    assert store.expire(f"{SESSION_PREFIX}{session_key}", 1)
    time.sleep(2)

    response = browser.request("/dashboard", follow_redirects=False)
    assert response.status == 302
    assert response.headers["Location"].endswith("/login")
    assert not db_query("SELECT id FROM sessions WHERE session_key = %s", (session_key,))
    assert account["email"]
