import psycopg2
import pytest

from database import get_connection
from migrate import apply_migrations


def test_migrations_upgrade_legacy_objects_and_are_idempotent(make_user, make_item):
    seller = make_user(verified=True)
    item = make_item(seller=seller)["item"]
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DROP INDEX IF EXISTS idx_item_media_item_sort_order")
            cursor.execute("ALTER TABLE user_sessions DROP COLUMN IF EXISTS admin_session")
            cursor.execute("ALTER TABLE users DROP COLUMN IF EXISTS profile_image_url")
            cursor.execute("DROP TABLE IF EXISTS schema_migrations")
            cursor.execute(
                """INSERT INTO item_media
                   (item_id, media_type, storage_provider, media_url, sort_order)
                   VALUES (%s, 'IMAGE', 'LOCAL', 'first.jpg', 7),
                          (%s, 'IMAGE', 'LOCAL', 'second.jpg', 7)""",
                (item["item_id"], item["item_id"]),
            )
        connection.commit()
    finally:
        connection.close()

    applied = apply_migrations()

    assert applied == [
        "001_websocket_tickets.sql",
        "002_active_order_per_item.sql",
        "003_order_meetup_date.sql",
        "004_user_posting_bans.sql",
        "005_message_visibility.sql",
        "006_item_media_order_unique.sql",
        "007_user_session_admin.sql",
        "008_profile_image_url.sql",
    ]
    assert apply_migrations() == []

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT media_url, sort_order FROM item_media
                   WHERE item_id = %s ORDER BY sort_order""",
                (item["item_id"],),
            )
            assert cursor.fetchall() == [("first.jpg", 0), ("second.jpg", 1)]
            cursor.execute("SELECT COUNT(*) FROM schema_migrations")
            assert cursor.fetchone()[0] == 8
            with pytest.raises(psycopg2.IntegrityError):
                cursor.execute(
                    """INSERT INTO item_media
                       (item_id, media_type, storage_provider, media_url, sort_order)
                       VALUES (%s, 'IMAGE', 'LOCAL', 'duplicate.jpg', 0)""",
                    (item["item_id"],),
                )
        connection.rollback()
    finally:
        connection.close()
