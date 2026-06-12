from __future__ import annotations

from pathlib import Path

from psycopg import connect

_SCHEMA_MIGRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def list_migration_files() -> list[Path]:
    migrations_dir = Path(__file__).parent / "migrations"
    return sorted(migrations_dir.glob("*.sql"))


def apply_migrations(dsn: str) -> None:
    """Apply pending SQL migrations in lexical order; record versions in ``schema_migrations``."""
    with connect(dsn) as conn:
        conn.execute(_SCHEMA_MIGRATIONS_SQL)
        for path in list_migration_files():
            version = path.stem
            applied = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE version = %s",
                (version,),
            ).fetchone()
            if applied is not None:
                continue
            sql = path.read_text(encoding="utf-8")
            conn.execute(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s)",
                (version,),
            )
