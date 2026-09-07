from dataclasses import dataclass
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import (
    HTTPRedirectHandler,
    HTTPCookieProcessor,
    Request,
    build_opener,
)
import uuid

import pymysql

from backend.config import Settings
from backend.repositories.mailbox_repository import MailboxRepository


BASE_URL = "http://nginx"


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


@dataclass
class HttpResult:
    status: int
    body: str
    headers: object
    url: str


class Browser:
    def __init__(self):
        self.jar = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.jar))
        self.no_redirect_opener = build_opener(
            HTTPCookieProcessor(self.jar),
            NoRedirectHandler(),
        )

    def request(self, path, form=None, method=None, follow_redirects=True, headers=None):
        url = urljoin(f"{BASE_URL}/", path.lstrip("/"))
        data = urlencode(form).encode("utf-8") if form is not None else None
        request = Request(url, data=data, method=method or ("POST" if data else "GET"))
        if data is not None:
            request.add_header("Content-Type", "application/x-www-form-urlencoded")
        for name, value in (headers or {}).items():
            request.add_header(name, value)
        opener = self.opener if follow_redirects else self.no_redirect_opener
        try:
            with opener.open(request, timeout=8) as response:
                return HttpResult(response.status, response.read().decode(), response.headers, response.url)
        except HTTPError as error:
            return HttpResult(error.code, error.read().decode(), error.headers, error.url)

    def cookie_value(self, name="session"):
        for cookie in self.jar:
            if cookie.name == name:
                return cookie.value
        return None


def account_details():
    suffix = uuid.uuid4().hex[:10]
    return {
        "username": f"user_{suffix}",
        "email": f"{suffix}@example.local",
        "password": "Correct Horse Battery 1!",
    }


def register(browser, account=None):
    account = account or account_details()
    response = browser.request(
        "/register",
        form={
            "username": account["username"],
            "email": account["email"],
            "password": account["password"],
            "password_confirmation": account["password"],
        },
        follow_redirects=False,
    )
    return account, response


def mailbox_token(browser, email=None):
    messages = MailboxRepository(Settings.from_env()).list_verifications()
    if email is not None:
        messages = [message for message in messages if message["to"] == email]
    assert messages
    return urlparse(messages[0]["verification_url"]).path.rsplit("/", 1)[-1]


def verify_account(browser, account):
    token = mailbox_token(browser, account["email"])
    response = browser.request(f"/verify/{token}")
    assert response.status == 200, response.body
    return token


def db_query(sql, params=()):
    settings = Settings.from_env()
    connection = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        connection.close()


def db_execute(sql, params=()):
    settings = Settings.from_env()
    connection = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
        connection.commit()
    finally:
        connection.close()
