from backend.config import Settings


def test_settings_default_to_local_deny(monkeypatch):
    monkeypatch.delenv("LAB_EGRESS", raising=False)
    settings = Settings.from_env()
    assert settings.lab_egress == "deny"
    assert settings.db_host == "mysql"


def test_settings_read_non_secret_connection_values(monkeypatch):
    monkeypatch.setenv("DB_HOST", "db-test")
    monkeypatch.setenv("DB_PORT", "3307")
    monkeypatch.setenv("REDIS_DB", "2")
    settings = Settings.from_env()
    assert settings.db_host == "db-test"
    assert settings.db_port == 3307
    assert settings.redis_db == 2
