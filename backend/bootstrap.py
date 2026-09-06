from pathlib import Path
import time

import pymysql

from backend.config import Settings


DATABASE_DIR = Path(__file__).resolve().parents[1] / "database"
SCHEMA_VERSION = "002_phase22a_schema"
SCHEMA_APPLIED_AT = "2026-01-01 00:00:00.000000"


def sql_statements(path: Path):
    return [statement.strip() for statement in path.read_text().split(";") if statement.strip()]


def execute_file(cursor, path: Path) -> None:
    for statement in sql_statements(path):
        try:
            cursor.execute(statement)
        except pymysql.err.OperationalError as error:
            # A previous bootstrap may have completed this non-transactional DDL
            # statement before a later statement failed. Keep retries idempotent.
            if error.args and error.args[0] == 1826:
                continue
            raise


def bootstrap(settings: Settings, attempts: int = 30) -> None:
    for _ in range(attempts):
        try:
            connection = pymysql.connect(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
                database=settings.db_name,
                connect_timeout=2,
                autocommit=True,
            )
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS schema_migrations (
                            version VARCHAR(64) NOT NULL PRIMARY KEY,
                            applied_at DATETIME(6) NOT NULL
                        ) ENGINE=InnoDB
                        """
                    )
                    cursor.execute(
                        "SELECT 1 FROM schema_migrations WHERE version = %s",
                        (SCHEMA_VERSION,),
                    )
                    if cursor.fetchone() is None:
                        execute_file(cursor, DATABASE_DIR / "schema.sql")
                        cursor.execute(
                            "INSERT INTO schema_migrations (version, applied_at) VALUES (%s, %s)",
                            (SCHEMA_VERSION, SCHEMA_APPLIED_AT),
                        )
                    execute_file(cursor, DATABASE_DIR / "seed.sql")
                return
            finally:
                connection.close()
        except pymysql.MySQLError:
            time.sleep(2)
    raise RuntimeError("database bootstrap failed")


if __name__ == "__main__":
    bootstrap(Settings.from_env())
