from datetime import datetime, timedelta
import math
import secrets

from backend.repositories.session_repository import RedisSessionStore, SessionRepository
from backend.utils.time import utc_now


class SessionService:
    def __init__(self, repository: SessionRepository, store: RedisSessionStore, settings, clock=utc_now):
        self.repository = repository
        self.store = store
        self.settings = settings
        self.clock = clock

    def create(self, user_id: int, remember_me: bool, ip_address: str, user_agent: str) -> str:
        session_key = secrets.token_urlsafe(32)
        created_at = self.clock()
        ttl = self._ttl(remember_me)
        expires_at = created_at + timedelta(seconds=ttl)
        payload = {
            "user_id": user_id,
            "remember_me": remember_me,
            "created_at": created_at.isoformat(),
            "last_seen_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        self.repository.create(
            session_key,
            user_id,
            remember_me,
            created_at,
            ip_address,
            user_agent,
        )
        try:
            self.store.put(session_key, payload, ttl)
        except Exception:
            self.repository.delete(session_key)
            raise
        return session_key

    def rotate(
        self,
        old_session_key: str | None,
        user_id: int,
        remember_me: bool,
        ip_address: str,
        user_agent: str,
    ) -> str:
        if old_session_key:
            self.invalidate(old_session_key)
        return self.create(user_id, remember_me, ip_address, user_agent)

    def load(self, session_key: str | None):
        if not session_key:
            return None
        payload = self.store.get(session_key)
        if payload is None:
            self.repository.delete(session_key)
            return None
        row = self.repository.find(session_key)
        if row is None or int(payload.get("user_id", -1)) != int(row["user_id"]):
            self.invalidate(session_key)
            return None

        now = self.clock()
        expires_at = datetime.fromisoformat(payload["expires_at"])
        if expires_at <= now:
            self.invalidate(session_key)
            return None

        last_seen_at = now
        remaining = max(1, math.ceil((expires_at - now).total_seconds()))
        payload["last_seen_at"] = last_seen_at.isoformat()
        self.repository.touch(session_key, last_seen_at)
        self.store.put(session_key, payload, remaining)
        return {**row, "expires_at": expires_at}

    def invalidate(self, session_key: str | None) -> None:
        if not session_key:
            return
        self.store.delete(session_key)
        self.repository.delete(session_key)

    def _ttl(self, remember_me: bool) -> int:
        return (
            self.settings.remember_session_ttl_seconds
            if remember_me
            else self.settings.session_ttl_seconds
        )
