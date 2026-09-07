from dataclasses import dataclass
from datetime import datetime

import pymysql

from backend.config import Settings


@dataclass(frozen=True)
class VerificationOutcome:
    status: str
    verification_id: int | None = None
    user_id: int | None = None


class VerificationRepository:
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
        user_id: int,
        token_hash: str,
        expires_at: datetime,
        created_at: datetime,
    ) -> int:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO email_verifications
                        (user_id, token_hash, expires_at, used_at, created_at)
                    VALUES (%s, %s, %s, NULL, %s)
                    """,
                    (user_id, token_hash, expires_at, created_at),
                )
                verification_id = cursor.lastrowid
            connection.commit()
            return int(verification_id)
        finally:
            connection.close()

    def consume(self, token_hash: str, now: datetime) -> VerificationOutcome:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, user_id, expires_at, used_at
                    FROM email_verifications
                    WHERE token_hash = %s
                    FOR UPDATE
                    """,
                    (token_hash,),
                )
                row = cursor.fetchone()
                if row is None:
                    connection.rollback()
                    return VerificationOutcome("invalid")
                if row["used_at"] is not None:
                    connection.rollback()
                    return VerificationOutcome("already_used", row["id"], row["user_id"])
                if row["expires_at"] <= now:
                    connection.rollback()
                    return VerificationOutcome("expired", row["id"], row["user_id"])

                cursor.execute(
                    "UPDATE email_verifications SET used_at = %s WHERE id = %s",
                    (now, row["id"]),
                )
                cursor.execute(
                    """
                    UPDATE users
                    SET status = 'active', email_verified_at = %s, updated_at = %s
                    WHERE id = %s
                    """,
                    (now, now, row["user_id"]),
                )
            connection.commit()
            return VerificationOutcome("verified", row["id"], row["user_id"])
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
