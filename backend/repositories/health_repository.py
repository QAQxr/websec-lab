import json
from urllib.request import urlopen

import pymysql
import redis

from backend.config import Settings


class DatabaseHealthRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def check(self) -> bool:
        connection = pymysql.connect(
            host=self.settings.db_host,
            port=self.settings.db_port,
            user=self.settings.db_user,
            password=self.settings.db_password,
            database=self.settings.db_name,
            connect_timeout=2,
            read_timeout=2,
            write_timeout=2,
            autocommit=True,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone()[0] == 1
        finally:
            connection.close()


class RedisHealthRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def check(self) -> bool:
        client = redis.Redis(
            host=self.settings.redis_host,
            port=self.settings.redis_port,
            db=self.settings.redis_db,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        return bool(client.ping())


class InternalApiHealthRepository:
    def __init__(self, settings: Settings):
        self.url = f"{settings.internal_api_url.rstrip('/')}/internal/health"

    def check(self) -> bool:
        with urlopen(self.url, timeout=2) as response:
            if response.status != 200:
                return False
            payload = json.load(response)
        return payload.get("status") == "ok"
