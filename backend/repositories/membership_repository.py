from datetime import datetime

import pymysql

from backend.config import Settings


class DuplicateMembershipError(Exception):
    """Raised when a project already contains the target user."""


class MembershipNotFoundError(Exception):
    """Raised when a membership disappears before a mutation is committed."""


class MembershipRepository:
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

    def list_members(self, project_id: int) -> list[dict]:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pm.user_id, u.username, pm.member_role AS role
                    FROM project_members AS pm
                    INNER JOIN users AS u ON u.id = pm.user_id
                    WHERE pm.project_id = %s
                    ORDER BY FIELD(pm.member_role, 'owner', 'manager', 'contributor', 'viewer'),
                             u.username, pm.user_id
                    """,
                    (project_id,),
                )
                return list(cursor.fetchall())
        finally:
            connection.close()

    def find_member(self, project_id: int, user_id: int) -> dict | None:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pm.user_id, u.username, pm.member_role AS role
                    FROM project_members AS pm
                    INNER JOIN users AS u ON u.id = pm.user_id
                    WHERE pm.project_id = %s AND pm.user_id = %s
                    """,
                    (project_id, user_id),
                )
                return cursor.fetchone()
        finally:
            connection.close()

    def create_member(
        self,
        project_id: int,
        user_id: int,
        role: str,
        invited_by: int,
        now: datetime,
    ) -> None:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO project_members
                        (project_id, user_id, member_role, invited_by, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (project_id, user_id, role, invited_by, now),
                )
            connection.commit()
        except pymysql.err.IntegrityError as error:
            connection.rollback()
            if error.args and error.args[0] == 1062:
                raise DuplicateMembershipError from error
            raise
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def update_member_role(self, project_id: int, user_id: int, role: str) -> None:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE project_members
                    SET member_role = %s
                    WHERE project_id = %s AND user_id = %s
                    """,
                    (role, project_id, user_id),
                )
                if cursor.rowcount != 1:
                    raise MembershipNotFoundError
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def delete_member(self, project_id: int, user_id: int) -> None:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM project_members WHERE project_id = %s AND user_id = %s",
                    (project_id, user_id),
                )
                if cursor.rowcount != 1:
                    raise MembershipNotFoundError
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
