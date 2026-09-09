from datetime import datetime
import json

import pymysql

from backend.config import Settings


class DuplicateProjectSlugError(Exception):
    """Raised when a project slug is already in use."""


PROJECT_FIELDS = """
    p.id,
    p.owner_id,
    p.name,
    p.slug,
    p.description,
    p.visibility,
    p.settings_json,
    p.created_at,
    p.updated_at,
    pm.member_role
"""


class ProjectRepository:
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

    def list_for_user(self, user_id: int, is_admin: bool = False) -> list[dict]:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                if is_admin:
                    cursor.execute(
                        f"""
                        SELECT {PROJECT_FIELDS}
                        FROM projects AS p
                        LEFT JOIN project_members AS pm
                            ON pm.project_id = p.id AND pm.user_id = %s
                        ORDER BY p.updated_at DESC, p.id DESC
                        """,
                        (user_id,),
                    )
                else:
                    cursor.execute(
                        f"""
                        SELECT {PROJECT_FIELDS}
                        FROM projects AS p
                        LEFT JOIN project_members AS pm
                            ON pm.project_id = p.id AND pm.user_id = %s
                        WHERE p.owner_id = %s OR pm.user_id = %s
                        ORDER BY p.updated_at DESC, p.id DESC
                        """,
                        (user_id, user_id, user_id),
                    )
                return list(cursor.fetchall())
        finally:
            connection.close()

    def find_for_user(self, project_id: int, user_id: int, is_admin: bool = False):
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                if is_admin:
                    cursor.execute(
                        f"""
                        SELECT {PROJECT_FIELDS}
                        FROM projects AS p
                        LEFT JOIN project_members AS pm
                            ON pm.project_id = p.id AND pm.user_id = %s
                        WHERE p.id = %s
                        """,
                        (user_id, project_id),
                    )
                else:
                    cursor.execute(
                        f"""
                        SELECT {PROJECT_FIELDS}
                        FROM projects AS p
                        LEFT JOIN project_members AS pm
                            ON pm.project_id = p.id AND pm.user_id = %s
                        WHERE p.id = %s
                          AND (p.owner_id = %s OR pm.user_id = %s)
                        """,
                        (user_id, project_id, user_id, user_id),
                    )
                return cursor.fetchone()
        finally:
            connection.close()

    def create(
        self,
        owner_id: int,
        name: str,
        slug: str,
        description: str,
        visibility: str,
        now: datetime,
    ) -> int:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO projects
                        (owner_id, name, slug, description, visibility, settings_json,
                         created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        owner_id,
                        name,
                        slug,
                        description,
                        visibility,
                        json.dumps({}, separators=(",", ":")),
                        now,
                        now,
                    ),
                )
                project_id = int(cursor.lastrowid)
                cursor.execute(
                    """
                    INSERT INTO project_members
                        (project_id, user_id, member_role, invited_by, created_at)
                    VALUES (%s, %s, 'owner', %s, %s)
                    """,
                    (project_id, owner_id, owner_id, now),
                )
            connection.commit()
            return project_id
        except pymysql.err.IntegrityError as error:
            connection.rollback()
            if error.args and error.args[0] == 1062:
                raise DuplicateProjectSlugError from error
            raise
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def update(
        self,
        project_id: int,
        name: str,
        description: str,
        visibility: str,
        now: datetime,
    ) -> None:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE projects
                    SET name = %s, description = %s, visibility = %s, updated_at = %s
                    WHERE id = %s
                    """,
                    (name, description, visibility, now, project_id),
                )
            connection.commit()
        finally:
            connection.close()

    def delete(self, project_id: int) -> None:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM projects WHERE id = %s", (project_id,))
            connection.commit()
        finally:
            connection.close()
