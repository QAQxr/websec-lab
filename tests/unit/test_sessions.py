from datetime import datetime, timedelta
from types import SimpleNamespace

from backend.services.session_service import SessionService


class FakeSessionRepository:
    def __init__(self):
        self.rows = {}

    def create(self, session_key, user_id, remember_me, created_at, ip_address, user_agent):
        self.rows[session_key] = {
            "session_key": session_key,
            "user_id": user_id,
            "remember_me": remember_me,
            "created_at": created_at,
            "last_seen_at": created_at,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

    def find(self, session_key):
        return self.rows.get(session_key)

    def touch(self, session_key, last_seen_at):
        self.rows[session_key]["last_seen_at"] = last_seen_at

    def delete(self, session_key):
        self.rows.pop(session_key, None)


class FakeSessionStore:
    def __init__(self):
        self.values = {}

    def put(self, session_key, payload, ttl):
        self.values[session_key] = {"payload": payload, "ttl": ttl}

    def get(self, session_key):
        item = self.values.get(session_key)
        return item["payload"] if item else None

    def delete(self, session_key):
        self.values.pop(session_key, None)


def build_service(now):
    settings = SimpleNamespace(
        session_ttl_seconds=3600,
        remember_session_ttl_seconds=86400,
    )
    repository = FakeSessionRepository()
    store = FakeSessionStore()
    return SessionService(repository, store, settings, clock=lambda: now), repository, store


def test_session_id_is_opaque_and_stored_server_side():
    now = datetime(2026, 1, 1, 12, 0, 0)
    service, repository, store = build_service(now)

    session_key = service.create(42, False, "127.0.0.1", "test-agent")

    assert len(session_key) >= 40
    assert "42" not in session_key
    assert session_key in repository.rows
    assert session_key in store.values


def test_session_rotation_invalidates_old_session():
    now = datetime(2026, 1, 1, 12, 0, 0)
    service, repository, store = build_service(now)
    old_key = service.create(42, False, "127.0.0.1", "test-agent")

    new_key = service.rotate(old_key, 42, False, "127.0.0.1", "test-agent")

    assert new_key != old_key
    assert old_key not in repository.rows
    assert old_key not in store.values
    assert new_key in repository.rows


def test_expired_session_is_invalidated():
    now = datetime(2026, 1, 1, 12, 0, 0)
    service, repository, store = build_service(now)
    session_key = service.create(42, False, "127.0.0.1", "test-agent")
    store.values[session_key]["payload"]["expires_at"] = (now - timedelta(seconds=1)).isoformat()

    assert service.load(session_key) is None
    assert session_key not in repository.rows
    assert session_key not in store.values
