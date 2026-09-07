import json
from datetime import datetime

import pymysql
import redis

from backend.config import Settings


SESSION_PREFIX = "websec:session:"


class RedisSessionStore:
    def __init__(self, settings: Settings):
        self.client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )

    @staticmethod
    def _key(session_key: str) -> str:
        return f"{SESSION_PREFIX}{session_key}"

    def put(self, session_key: str, payload: dict, ttl: int) -> None:
        self.client.set(self._key(session_key), json.dumps(payload), ex=ttl)

    def get(self, session_key: str) -> dict | None:
        payload = self.client.get(self._key(session_key))
        return json.loads(payload) if payload else None

    def delete(self, session_key: str) -> None:
        self.client.delete(self._key(session_key))


class SessionRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _connection(self):
        return pymysql.connect(
            host=self.settings.db_host,
            port=self.settings.db_port,
            user=self.settings.db_user,
            password=self.settings.db_password,
            database=self.settings.db_name,
            connect_timeout=3,
            read_timeout=3,
            write_timeout=3,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def create(
        self,
        session_key: str,
        user_id: int,
        remember_me: bool,
        created_at: datetime,
        ip_address: str,
        user_agent: str,
    ) -> None:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO sessions
                        (user_id, session_key, remember_me, created_at, last_seen_at,
                         ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        session_key,
                        remember_me,
                        created_at,
                        created_at,
                        ip_address[:64],
                        user_agent[:512],
                    ),
                )
            connection.commit()
        finally:
            connection.close()

    def find(self, session_key: str):
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM sessions WHERE session_key = %s",
                    (session_key,),
                )
                return cursor.fetchone()
        finally:
            connection.close()

    def touch(self, session_key: str, last_seen_at: datetime) -> None:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE sessions SET last_seen_at = %s WHERE session_key = %s",
                    (last_seen_at, session_key),
                )
            connection.commit()
        finally:
            connection.close()

    def delete(self, session_key: str) -> None:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM sessions WHERE session_key = %s", (session_key,))
            connection.commit()
        finally:
            connection.close()
