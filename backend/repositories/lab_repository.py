from datetime import date, datetime
import json

import pymysql

from backend.config import Settings


class LabRepository:
    """Database access for schema and fixture verification.

    This repository deliberately contains no authorization or business policy.
    """

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

    @staticmethod
    def _normalize(value):
        if isinstance(value, datetime):
            return value.isoformat(sep=" ")
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, bytes):
            return value.decode("utf-8")
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return value
        if isinstance(value, dict):
            return {key: LabRepository._normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [LabRepository._normalize(item) for item in value]
        return value

    def _rows(self, cursor, query):
        cursor.execute(query)
        return [self._normalize(row) for row in cursor.fetchall()]

    def seed_snapshot(self) -> dict:
        queries = {
            "users": "SELECT id, username, email, role, status, bio, website, email_verified_at, created_at, updated_at FROM users ORDER BY id",
            "projects": "SELECT id, owner_id, name, slug, description, visibility, settings_json, created_at, updated_at FROM projects ORDER BY id",
            "project_members": "SELECT project_id, user_id, member_role, invited_by, created_at FROM project_members ORDER BY project_id, user_id",
            "files": "SELECT id, project_id, owner_id, original_name, storage_name, storage_path, mime_type, size_bytes, kind, is_public, created_at FROM files ORDER BY id",
            "messages": "SELECT id, sender_id, recipient_id, subject, body, thread_id, read_at, created_at FROM messages ORDER BY id",
            "comments": "SELECT id, project_id, author_id, body, created_at, deleted_at FROM comments ORDER BY id",
            "notifications": "SELECT id, user_id, kind, payload_json, read_at, created_at FROM notifications ORDER BY id",
            "api_keys": "SELECT id, user_id, label, display_prefix, scopes_json, last_used_at, created_at FROM api_keys ORDER BY id",
            "audit_logs": "SELECT id, actor_id, event_type, method, path, parameters_json, metadata_json, created_at FROM audit_logs ORDER BY id",
            "system_settings": "SELECT setting_key, setting_value, value_type, updated_by, updated_at FROM system_settings ORDER BY setting_key",
        }
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                return {name: self._rows(cursor, query) for name, query in queries.items()}
        finally:
            connection.close()

    def table_names(self) -> set[str]:
        connection = self._connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT table_name AS table_name
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                    """
                )
                return {row["table_name"] for row in cursor.fetchall()}
        finally:
            connection.close()
