from datetime import datetime

import pymysql

from backend.config import Settings


class DuplicateAccountError(Exception):
    """Raised when a username or email is already registered."""


class UserRepository:
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

    def find_by_username(self, username: str):
        return self._find_one("SELECT * FROM users WHERE username = %s", (username,))

    def find_by_email(self, email: str):
        return self._find_one("SELECT * FROM users WHERE email = %s", (email,))

    def find_by_identifier(self, identifier: str):
        normalized = identifier.strip()
        return self._find_one(
            "SELECT * FROM users WHERE username = %s OR email = %s",
            (normalized, normalized.lower()),
        )

    def find_by_id(self, user_id: int):
        return self._find_one("SELECT * FROM users WHERE id = %s", (user_id,))

    def _find_one(self, query: str, params: tuple):
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()
        finally:
            connection.close()

    def create_pending(
        self,
        username: str,
        email: str,
        password_hash: str,
        now: datetime,
    ) -> int:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users
                        (username, email, password_hash, role, status, bio, website,
                         email_verified_at, created_at, updated_at)
                    VALUES (%s, %s, %s, 'user', 'pending', '', NULL, NULL, %s, %s)
                    """,
                    (username, email, password_hash, now, now),
                )
                user_id = cursor.lastrowid
            connection.commit()
            return int(user_id)
        except pymysql.err.IntegrityError as error:
            connection.rollback()
            if error.args and error.args[0] == 1062:
                raise DuplicateAccountError from error
            raise
        finally:
            connection.close()

    def update_last_login(self, user_id: int, now: datetime) -> None:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET last_login_at = %s, updated_at = %s WHERE id = %s",
                    (now, now, user_id),
                )
            connection.commit()
        finally:
            connection.close()
