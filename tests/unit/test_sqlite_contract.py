import sqlite3


def test_sqlite_unit_fixture_covers_only_simple_record_shape():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL
        );
        """
    )
    connection.execute(
        "INSERT INTO users (id, email, role) VALUES (?, ?, ?)",
        (1, "alice@example.local", "user"),
    )
    row = connection.execute("SELECT id, email, role FROM users").fetchone()
    connection.close()
    assert row == (1, "alice@example.local", "user")
