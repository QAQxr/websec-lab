import time

import pymysql

from backend.config import Settings


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
                        CREATE TABLE IF NOT EXISTS lab_bootstrap (
                            marker VARCHAR(64) PRIMARY KEY,
                            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                    cursor.execute(
                        "INSERT IGNORE INTO lab_bootstrap (marker) VALUES ('phase-2.1')"
                    )
                return
            finally:
                connection.close()
        except pymysql.MySQLError:
            time.sleep(2)
    raise RuntimeError("database bootstrap failed")


if __name__ == "__main__":
    bootstrap(Settings.from_env())
