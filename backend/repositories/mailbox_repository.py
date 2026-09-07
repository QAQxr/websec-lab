import json

import redis

from backend.config import Settings


class MailboxRepository:
    PREFIX = "websec:mailbox:verification:"

    def __init__(self, settings: Settings):
        self.client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )

    def put_verification(self, verification_id: int, message: dict, ttl: int) -> None:
        self.client.set(
            f"{self.PREFIX}{verification_id}",
            json.dumps(message, sort_keys=True),
            ex=ttl,
        )

    def remove_verification(self, verification_id: int) -> None:
        self.client.delete(f"{self.PREFIX}{verification_id}")

    def list_verifications(self) -> list[dict]:
        messages = []
        for key in self.client.scan_iter(match=f"{self.PREFIX}*"):
            payload = self.client.get(key)
            if payload:
                messages.append(json.loads(payload))
        return sorted(messages, key=lambda item: item.get("created_at", ""), reverse=True)
