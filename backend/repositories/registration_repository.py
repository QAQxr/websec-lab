from datetime import datetime

import pymysql

from backend.config import Settings
from backend.repositories.user_repository import DuplicateAccountError


class RegistrationRepository:
    """Persist a new user and its verification row in one MySQL transaction."""

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

    def create_pending_with_verification(
        self,
        username: str,
        email: str,
        password_hash: str,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> tuple[int, int]:
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
                user_id = int(cursor.lastrowid)
                cursor.execute(
                    """
                    INSERT INTO email_verifications
                        (user_id, token_hash, expires_at, used_at, created_at)
                    VALUES (%s, %s, %s, NULL, %s)
                    """,
                    (user_id, token_hash, expires_at, now),
                )
                verification_id = int(cursor.lastrowid)
            connection.commit()
            return user_id, verification_id
        except pymysql.err.IntegrityError as error:
            connection.rollback()
            if error.args and error.args[0] == 1062:
                raise DuplicateAccountError from error
            raise
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def rollback_registration(self, user_id: int, verification_id: int) -> None:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM email_verifications WHERE id = %s AND user_id = %s",
                    (verification_id, user_id),
                )
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
