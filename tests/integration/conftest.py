import pymysql
import pytest
import redis

from backend.config import Settings


def _cleanup_test_state():
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
            cursor.execute("DELETE FROM users WHERE id > 5")
        connection.commit()
    finally:
        connection.close()

    store = redis.Redis(host=settings.redis_host, port=settings.redis_port, db=settings.redis_db)
    keys = list(store.scan_iter(match="websec:mailbox:verification:*"))
    keys.extend(store.scan_iter(match="websec:session:*"))
    if keys:
        store.delete(*keys)


@pytest.fixture(autouse=True)
def isolate_integration_test_state():
    _cleanup_test_state()
    yield
    _cleanup_test_state()
