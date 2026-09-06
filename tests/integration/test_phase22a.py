import json
from pathlib import Path

import pymysql

from backend.bootstrap import sql_statements
from backend.config import Settings
from backend.repositories.lab_repository import LabRepository


CORE_TABLES = {
    "users",
    "sessions",
    "projects",
    "project_members",
    "files",
    "messages",
    "comments",
    "notifications",
    "api_keys",
    "audit_logs",
    "system_settings",
}

SUPPORT_TABLES = {
    "email_verifications",
    "password_resets",
    "shares",
    "webhook_configs",
    "import_jobs",
    "point_balances",
    "point_redemptions",
    "challenge_progress",
    "lab_attempts",
    "password_history",
}


def connection():
    settings = Settings.from_env()
    return pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        cursorclass=pymysql.cursors.DictCursor,
    )


def query(sql, params=()):
    db = connection()
    try:
        with db.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        db.close()


def execute_schema_script():
    db = connection()
    try:
        with db.cursor() as cursor:
            schema_path = Path(__file__).resolve().parents[2] / "database" / "schema.sql"
            for statement in sql_statements(schema_path):
                cursor.execute(statement)
    finally:
        db.close()


def test_all_phase22a_tables_exist():
    names = LabRepository(Settings.from_env()).table_names()
    assert CORE_TABLES | SUPPORT_TABLES | {"schema_migrations"} <= names


def test_schema_script_is_replayable():
    execute_schema_script()
    execute_schema_script()


def test_primary_keys_foreign_keys_and_unique_constraints_exist():
    primary_keys = {
        row["table_name"]
        for row in query(
            """
            SELECT table_name AS table_name
            FROM information_schema.table_constraints
            WHERE table_schema = DATABASE() AND constraint_type = 'PRIMARY KEY'
            """
        )
    }
    assert CORE_TABLES | SUPPORT_TABLES <= primary_keys

    foreign_keys = {
        (row["table_name"], row["column_name"], row["referenced_table_name"])
        for row in query(
            """
            SELECT table_name AS table_name,
                   column_name AS column_name,
                   referenced_table_name AS referenced_table_name
            FROM information_schema.key_column_usage
            WHERE table_schema = DATABASE() AND referenced_table_name IS NOT NULL
            """
        )
    }
    assert ("projects", "owner_id", "users") in foreign_keys
    assert ("project_members", "project_id", "projects") in foreign_keys
    assert ("project_members", "user_id", "users") in foreign_keys
    assert ("files", "project_id", "projects") in foreign_keys
    assert ("messages", "sender_id", "users") in foreign_keys
    assert ("comments", "project_id", "projects") in foreign_keys
    assert ("api_keys", "user_id", "users") in foreign_keys
    assert ("audit_logs", "actor_id", "users") in foreign_keys

    unique_columns = {
        (row["table_name"], row["column_name"])
        for row in query(
            """
            SELECT DISTINCT table_name AS table_name,
                   column_name AS column_name
            FROM information_schema.statistics
            WHERE table_schema = DATABASE() AND non_unique = 0
            """
        )
    }
    assert ("users", "username") in unique_columns
    assert ("users", "email") in unique_columns
    assert ("projects", "slug") in unique_columns
    assert ("files", "storage_name") in unique_columns
    assert ("api_keys", "key_hash") in unique_columns


def test_json_columns_and_indexes_exist():
    json_columns = {
        (row["table_name"], row["column_name"])
        for row in query(
            """
            SELECT table_name AS table_name,
                   column_name AS column_name
            FROM information_schema.columns
            WHERE table_schema = DATABASE() AND data_type = 'json'
            """
        )
    }
    assert ("projects", "settings_json") in json_columns
    assert ("notifications", "payload_json") in json_columns
    assert ("api_keys", "scopes_json") in json_columns
    assert ("audit_logs", "parameters_json") in json_columns

    indexes = {
        row["index_name"]
        for row in query(
            """
            SELECT DISTINCT index_name AS index_name
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
            """
        )
    }
    assert "idx_projects_owner_id" in indexes
    assert "idx_files_project_id" in indexes
    assert "idx_audit_logs_event_created" in indexes


def test_seed_users_projects_and_memberships():
    snapshot = LabRepository(Settings.from_env()).seed_snapshot()
    users = {row["email"]: row for row in snapshot["users"]}
    assert set(users) == {
        "admin@example.local",
        "manager@example.local",
        "alice@example.local",
        "bob@example.local",
        "charlie@example.local",
    }
    assert users["admin@example.local"]["role"] == "admin"
    assert users["manager@example.local"]["role"] == "manager"
    assert all(row["status"] == "active" for row in users.values())

    projects = {row["id"]: row for row in snapshot["projects"]}
    assert {row["name"] for row in projects.values()} == {
        "Operations",
        "Product",
        "Project Alpha",
        "Project Beta",
        "Project Gamma",
    }
    assert {project_id: row["owner_id"] for project_id, row in projects.items()} == {
        1: 1,
        2: 2,
        3: 3,
        4: 4,
        5: 5,
    }

    memberships = {
        (row["project_id"], row["user_id"]): row["member_role"]
        for row in snapshot["project_members"]
    }
    assert memberships[(1, 1)] == "owner"
    assert memberships[(1, 2)] == "manager"
    assert memberships[(3, 3)] == "owner"
    assert memberships[(3, 4)] == "viewer"
    assert memberships[(4, 4)] == "owner"
    assert memberships[(5, 5)] == "owner"


def test_seed_business_fixtures_and_sensitive_fields():
    snapshot = LabRepository(Settings.from_env()).seed_snapshot()
    assert {row["original_name"] for row in snapshot["files"]} == {
        "deployment-notes.txt",
        "roadmap.pdf",
        "alice-private.txt",
        "bob-report.txt",
        "charlie-profile.png",
    }
    assert {(row["sender_id"], row["recipient_id"]) for row in snapshot["messages"]} >= {
        (3, 4),
        (4, 3),
        (2, 3),
        (1, 2),
    }
    assert len(snapshot["comments"]) == 5
    assert {row["kind"] for row in snapshot["notifications"]} == {
        "project_invitation",
        "mention",
        "file_share",
        "password_reset_notification",
    }
    assert {row["display_prefix"] for row in snapshot["api_keys"]} == {
        "lab_admin_",
        "lab_manager_",
        "lab_user_",
    }
    assert {row["event_type"] for row in snapshot["audit_logs"]} == {
        "login",
        "project.create",
        "project.member.add",
        "file.upload",
        "message.send",
        "settings.update",
    }
    assert {row["setting_key"] for row in snapshot["system_settings"]} == {
        "site_name",
        "default_project_visibility",
        "max_upload_size",
        "maintenance_mode",
    }

    password_rows = query("SELECT email, password_hash FROM users ORDER BY id")
    assert all(row["password_hash"].startswith("pbkdf2_sha256$") for row in password_rows)
    assert all("LOCAL_ONLY_" not in row["password_hash"] for row in password_rows)

    scope_rows = query("SELECT display_prefix, scopes_json FROM api_keys ORDER BY id")
    assert json.loads(scope_rows[0]["scopes_json"]) == ["admin:read", "admin:write"]
