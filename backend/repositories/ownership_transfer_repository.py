from datetime import datetime

import pymysql

from backend.config import Settings


class OwnershipTransferRepositoryError(Exception):
    """Raised when a locked ownership transfer cannot update its expected rows."""


class OwnershipTransferTransaction:
    def __init__(self, connection):
        self.connection = connection
        self._committed = False

    def __enter__(self):
        return self

    def __exit__(self, exception_type, _exception, _traceback):
        if exception_type is not None or not self._committed:
            self.connection.rollback()
        self.connection.close()
        return False

    def lock_project(self, project_id: int) -> dict | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, owner_id, visibility, updated_at
                FROM projects
                WHERE id = %s
                FOR UPDATE
                """,
                (project_id,),
            )
            return cursor.fetchone()

    def lock_memberships(self, project_id: int) -> list[dict]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT project_id, user_id, member_role, invited_by, created_at
                FROM project_members
                WHERE project_id = %s
                ORDER BY user_id
                FOR UPDATE
                """,
                (project_id,),
            )
            return list(cursor.fetchall())

    def lock_user(self, user_id: int) -> dict | None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, role, status
                FROM users
                WHERE id = %s
                FOR UPDATE
                """,
                (user_id,),
            )
            return cursor.fetchone()

    def apply_transfer(
        self,
        project_id: int,
        old_owner_id: int,
        new_owner_id: int,
        now: datetime,
    ) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE projects
                SET owner_id = %s, updated_at = %s
                WHERE id = %s AND owner_id = %s
                """,
                (new_owner_id, now, project_id, old_owner_id),
            )
            if cursor.rowcount != 1:
                raise OwnershipTransferRepositoryError

            cursor.execute(
                """
                UPDATE project_members
                SET member_role = 'manager'
                WHERE project_id = %s
                  AND user_id = %s
                  AND member_role = 'owner'
                """,
                (project_id, old_owner_id),
            )
            if cursor.rowcount != 1:
                raise OwnershipTransferRepositoryError

            cursor.execute(
                """
                UPDATE project_members
                SET member_role = 'owner'
                WHERE project_id = %s
                  AND user_id = %s
                  AND member_role IN ('viewer', 'contributor', 'manager')
                """,
                (project_id, new_owner_id),
            )
            if cursor.rowcount != 1:
                raise OwnershipTransferRepositoryError

    def commit(self) -> None:
        self.connection.commit()
        self._committed = True


class OwnershipTransferRepository:
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

    def transaction(self) -> OwnershipTransferTransaction:
        return OwnershipTransferTransaction(self._connection())
