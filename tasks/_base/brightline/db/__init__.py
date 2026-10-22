"""SQLite access and a tiny forward/backward migration runner.

Layout:
    schema.sql                      baseline, version 1
    migrations/NNNN_name.up.sql     applied in order for NNNN > 1
    migrations/NNNN_name.down.sql   required to roll that migration back
"""
import re
import sqlite3
from pathlib import Path

_HERE = Path(__file__).parent
MIGRATIONS_DIR = _HERE / "migrations"
_NAME = re.compile(r"^(\d{4})_(.+)\.(up|down)\.sql$")


class MigrationError(RuntimeError):
    pass


def _discover():
    """Return {version: {"up": Path, "down": Path|None}} for numbered migrations."""
    found = {}
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        m = _NAME.match(path.name)
        if not m:
            continue
        entry = found.setdefault(int(m.group(1)), {"up": None, "down": None})
        entry[m.group(3)] = path
    return found


def latest_version():
    versions = _discover()
    return max(versions) if versions else 1


def current_version(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)")
    row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    return row[0] or 0


def migrate(conn, target=None):
    """Bring the database up to `target` (default: latest)."""
    target = latest_version() if target is None else target
    version = current_version(conn)
    if version == 0:
        conn.executescript((_HERE / "schema.sql").read_text())
        conn.execute("INSERT INTO schema_migrations(version) VALUES (1)")
        version = 1
    migrations = _discover()
    for v in sorted(migrations):
        if version < v <= target:
            if migrations[v]["up"] is None:
                raise MigrationError(f"migration {v:04d} has no .up.sql")
            conn.executescript(migrations[v]["up"].read_text())
            conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (v,))
            version = v
    conn.commit()
    return version


def rollback(conn, steps=1):
    """Undo the last `steps` migrations. The baseline cannot be rolled back."""
    migrations = _discover()
    for _ in range(steps):
        version = current_version(conn)
        if version <= 1:
            raise MigrationError("nothing to roll back")
        down = migrations.get(version, {}).get("down")
        if down is None:
            raise MigrationError(f"migration {version:04d} is not reversible")
        conn.executescript(down.read_text())
        conn.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
    conn.commit()
    return current_version(conn)


def connect(path=":memory:"):
    """Open a database with the schema fully migrated."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    migrate(conn)
    return conn
