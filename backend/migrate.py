import hashlib
from pathlib import Path

from database import get_connection

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "database" / "migrations"


def apply_migrations() -> list[str]:
    applied_now = []
    connection = get_connection()
    lock_acquired = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_lock(%s)", (731904261,))
            lock_acquired = True
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS schema_migrations (
                       version VARCHAR(100) PRIMARY KEY,
                       checksum CHAR(64) NOT NULL,
                       applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                   )"""
            )
        connection.commit()

        for migration_path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")):
            migration_sql = migration_path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(migration_sql.encode("utf-8")).hexdigest()
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT checksum FROM schema_migrations WHERE version = %s",
                    (migration_path.name,),
                )
                existing = cursor.fetchone()
                if existing:
                    if existing[0].strip() != checksum:
                        raise RuntimeError(
                            f"Applied migration {migration_path.name} was modified; add a new migration instead."
                        )
                    continue

                cursor.execute(migration_sql)
                cursor.execute(
                    "INSERT INTO schema_migrations (version, checksum) VALUES (%s, %s)",
                    (migration_path.name, checksum),
                )
            connection.commit()
            applied_now.append(migration_path.name)
        return applied_now
    except Exception:
        connection.rollback()
        raise
    finally:
        if lock_acquired:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (731904261,))
            connection.commit()
        connection.close()


if __name__ == "__main__":
    migrations = apply_migrations()
    if migrations:
        print("Applied migrations: " + ", ".join(migrations))
    else:
        print("Database schema is up to date.")
