import json
import os
from urllib.request import urlopen


BASE_URL = os.getenv("TEST_BASE_URL", "http://nginx")


def get_json(url):
    with urlopen(url, timeout=5) as response:
        assert response.status == 200
        return json.load(response)


def test_nginx_proxies_to_flask():
    payload = get_json(f"{BASE_URL}/health")
    assert payload["status"] == "ok"


def test_web_connectivity_checks_are_healthy():
    payload = get_json(f"{BASE_URL}/health")
    assert payload["checks"] == {
        "database": "ok",
        "redis": "ok",
        "internal_api": "ok",
    }


def test_internal_api_is_reachable_inside_private_network():
    payload = get_json("http://internal-api:8081/internal/health")
    assert payload == {"service": "internal-api", "status": "ok"}


def test_landing_page_is_acmecloud():
    with urlopen(f"{BASE_URL}/", timeout=5) as response:
        body = response.read().decode("utf-8")
    assert "AcmeCloud" in body
    assert "WebSec Lab" in body
