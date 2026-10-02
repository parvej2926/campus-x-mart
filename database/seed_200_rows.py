import argparse
from datetime import datetime, timedelta

import psycopg2

from settings import settings


def connect():
    return psycopg2.connect(settings.DATABASE_URL)


def main():
    if settings.APP_ENV != "dev":
        raise SystemExit("Refusing to seed data outside APP_ENV=dev.")

    parser = argparse.ArgumentParser(description="Seed the development database.")
    parser.add_argument("--yes", action="store_true", help="Required confirmation flag to seed the database.")
    args = parser.parse_args()

    if not args.yes:
        raise SystemExit("Seed action requires --yes. Refusing to run without explicit approval.")

    conn = connect()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            TRUNCATE TABLE
                item_predictions,
                reports,
                notifications,
                messages,
                orders,
                reviews,
                item_reactions,
                post_reactions,
                item_comments,
                post_comments,
                post_media,
                item_media,
                posts,
                items,
                locations,
                verification_codes,
                user_sessions,
                users
            RESTART IDENTITY CASCADE;
            """
        )
        conn.commit()

        user_rows = []
        for i in range(1, 201):
            user_rows.append(
                (
                    f'student{i}',
                    f'Student {i}',
                    f'student{i}@campusxmart.test',
                    f'+88017{(i * 17) % 100000000:08d}',
                    f'$2b$12$seedhash{i:04d}aaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    None,
                    'STUDENT',
                    True,
                    True,
                    True,
                )
            )
        cur.executemany(
            """
            INSERT INTO users (
                username,
                full_name,
                email,
                phone,
                password_hash,
                profile_image_url,
                role,
                email_verified,
                phone_verified,
                is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            user_rows,
        )
        conn.commit()
        cur.execute('SELECT user_id FROM users ORDER BY user_id')
        user_ids = [row[0] for row in cur.fetchall()]

        location_rows = []
        for i in range(1, 201):
            location_rows.append(
                (
                    f'Location {i}',
                    f'Campus {((i - 1) % 8) + 1}',
                    f'{i} Main Road, University City',
                    round(23.7000 + ((i % 50) * 0.002), 6),
                    round(90.3000 + ((i % 60) * 0.002), 6),
                )
            )
        cur.executemany(
            """
            INSERT INTO locations (
                location_name,
                campus_name,
                address,
                latitude,
                longitude
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            location_rows,
        )
        conn.commit()
        cur.execute('SELECT location_id FROM locations ORDER BY location_id')
        location_ids = [row[0] for row in cur.fetchall()]

        categories = ['Books', 'Electronics', 'Furniture', 'Bikes', 'Others', 'Study Material']
        conditions = ['NEW', 'USED_EXCELLENT', 'USED_GOOD', 'USED']
        statuses = ['AVAILABLE', 'AVAILABLE', 'RESERVED', 'AVAILABLE', 'AVAILABLE']
        item_rows = []
        for i in range(1, 201):
            seller_id = user_ids[(i - 1) % len(user_ids)]
            location_id = location_ids[(i - 1) % len(location_ids)]
            item_rows.append(
                (
                    seller_id,
                    location_id,
                    f'Item {i}',
                    f'High-quality campus item {i} suitable for daily student use and easy to carry.',
                    round(float((i * 350) % 95000 + 150), 2),
                    categories[(i - 1) % len(categories)],
                    conditions[(i - 1) % len(conditions)],
                    (datetime.now() - timedelta(days=(i % 120))).date(),
                    statuses[(i - 1) % len(statuses)],
                    None,
                )
            )
        cur.executemany(
            """
            INSERT INTO items (
                seller_id,
                location_id,
                name,
                description,
                price,
                category,
                item_condition,
                available_from,
                status,
                video_url
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            item_rows,
        )
        conn.commit()
        cur.execute('SELECT item_id FROM items ORDER BY item_id')
        item_ids = [row[0] for row in cur.fetchall()]

        item_media_rows = []
        for i in range(1, 201):
            item_media_rows.append(
                (
                    item_ids[(i - 1) % len(item_ids)],
                    'IMAGE',
                    'CLOUDINARY',
                    f'https://res.cloudinary.com/demo/image/upload/item_{i}.jpg',
                    f'item_{i}',
                    f'item_{i}.jpg',
                    (i - 1) % 5,
                )
            )
        cur.executemany(
            """
            INSERT INTO item_media (
                item_id,
                media_type,
                storage_provider,
                media_url,
                public_id,
                original_filename,
                sort_order
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            item_media_rows,
        )
        conn.commit()

        post_rows = []
        for i in range(1, 201):
            post_rows.append(
                (
                    user_ids[(i - 1) % len(user_ids)],
                    item_ids[(i - 1) % len(item_ids)],
                    f'Campus deal #{i}: useful, affordable, and student-friendly.',
                )
            )
        cur.executemany(
            "INSERT INTO posts (author_id, item_id, caption) VALUES (%s, %s, %s)",
            post_rows,
        )
        conn.commit()
        cur.execute('SELECT post_id FROM posts ORDER BY post_id')
        post_ids = [row[0] for row in cur.fetchall()]

        post_media_rows = []
        for i in range(1, 201):
            post_media_rows.append(
                (
                    post_ids[(i - 1) % len(post_ids)],
                    'IMAGE',
                    'CLOUDINARY',
                    f'https://res.cloudinary.com/demo/image/upload/post_{i}.jpg',
                    f'post_{i}',
                    (i - 1) % 4,
                )
            )
        cur.executemany(
            """
            INSERT INTO post_media (
                post_id,
                media_type,
                storage_provider,
                media_url,
                public_id,
                sort_order
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            post_media_rows,
        )
        conn.commit()
        print(f"Seeded {len(user_rows)} users and {len(item_rows)} items.")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()

# POST COMMENTS
post_comment_rows = []
for i in range(1, 201):
    post_comment_rows.append(
        (
            post_ids[(i - 1) % len(post_ids)],
            user_ids[(i * 7) % len(user_ids)],
            f'Comment {i}: this item looks useful for my academic needs.',
        )
    )
cur.executemany(
    "INSERT INTO post_comments (post_id, author_id, comment_text) VALUES (%s, %s, %s)",
    post_comment_rows,
)
conn.commit()

# ITEM COMMENTS
item_comment_rows = []
for i in range(1, 201):
    item_comment_rows.append(
        (
            item_ids[(i - 1) % len(item_ids)],
            user_ids[(i * 11) % len(user_ids)],
            f'Interested in item {i}. Please share more details and pickup timing.',
        )
    )
cur.executemany(
    "INSERT INTO item_comments (item_id, author_id, comment_text) VALUES (%s, %s, %s)",
    item_comment_rows,
)
conn.commit()

# POST REACTIONS
post_reaction_rows = []
seen = set()
for i in range(1, 201):
    post_id = post_ids[(i - 1) % len(post_ids)]
    user_id = user_ids[(i * 13) % len(user_ids)]
    key = (post_id, user_id)
    if key in seen:
        continue
    seen.add(key)
    post_reaction_rows.append((post_id, user_id, 'LIKE' if i % 2 == 0 else 'DISLIKE'))
cur.executemany(
    "INSERT INTO post_reactions (post_id, user_id, reaction_type) VALUES (%s, %s, %s)",
    post_reaction_rows,
)
conn.commit()

# ITEM REACTIONS
item_reaction_rows = []
seen = set()
for i in range(1, 201):
    item_id = item_ids[(i - 1) % len(item_ids)]
    user_id = user_ids[(i * 17) % len(user_ids)]
    key = (item_id, user_id)
    if key in seen:
        continue
    seen.add(key)
    item_reaction_rows.append((item_id, user_id, 'LIKE' if i % 2 == 0 else 'DISLIKE'))
cur.executemany(
    "INSERT INTO item_reactions (item_id, user_id, reaction_type) VALUES (%s, %s, %s)",
    item_reaction_rows,
)
conn.commit()

# REVIEWS
review_rows = []
seen = set()
for i in range(1, 201):
    item_id = item_ids[(i - 1) % len(item_ids)]
    seller_id = cur.execute('SELECT seller_id FROM items WHERE item_id = %s', (item_id,))
    seller_id = cur.fetchone()[0]
    buyer_id = user_ids[(i * 19) % len(user_ids)]
    if buyer_id == seller_id:
        buyer_id = user_ids[(i + 1) % len(user_ids)]
    key = (item_id, buyer_id)
    if key in seen:
        continue
    seen.add(key)
    review_rows.append((item_id, buyer_id, ((i % 5) + 1), f'Review {i}: overall good quality and a smooth student-friendly exchange.'))
cur.executemany(
    "INSERT INTO reviews (item_id, user_id, rating, review_text) VALUES (%s, %s, %s, %s)",
    review_rows,
)
conn.commit()

# ORDERS
order_rows = []
for i in range(1, 201):
    item_id = item_ids[(i - 1) % len(item_ids)]
    seller_id = cur.execute('SELECT seller_id FROM items WHERE item_id = %s', (item_id,))
    seller_id = cur.fetchone()[0]
    buyer_id = user_ids[(i * 23) % len(user_ids)]
    if buyer_id == seller_id:
        buyer_id = user_ids[(i + 2) % len(user_ids)]
    order_rows.append(
        (
            item_id,
            buyer_id,
            seller_id,
            round(float((i * 175) % 90000 + 250), 2),
            ['PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED'][i % 4],
        )
    )
cur.executemany(
    "INSERT INTO orders (item_id, buyer_id, seller_id, agreed_price, status) VALUES (%s, %s, %s, %s, %s)",
    order_rows,
)
conn.commit()

# MESSAGES
message_rows = []
for i in range(1, 201):
    sender_id = user_ids[(i * 3) % len(user_ids)]
    receiver_id = user_ids[(i * 5 + 1) % len(user_ids)]
    if sender_id == receiver_id:
        receiver_id = user_ids[(i + 1) % len(user_ids)]
    message_rows.append(
        (
            sender_id,
            receiver_id,
            f'Message {i}: I would like to know the latest details about the item and the pickup time.',
            i % 2 == 0,
        )
    )
cur.executemany(
    "INSERT INTO messages (sender_id, receiver_id, message_text, is_read) VALUES (%s, %s, %s, %s)",
    message_rows,
)
conn.commit()

# NOTIFICATIONS
notification_rows = []
for i in range(1, 201):
    notification_rows.append(
        (
            user_ids[(i - 1) % len(user_ids)],
            ['REACTION', 'COMMENT', 'ORDER', 'MESSAGE', 'SYSTEM'][i % 5],
            f'Notification {i}',
            f'Your campus marketplace feed has a new update for item {i}.',
            f'/items/{item_ids[(i - 1) % len(item_ids)]}',
            i % 3 == 0,
        )
    )
cur.executemany(
    """
    INSERT INTO notifications (
        user_id,
        notification_type,
        title,
        message,
        target_url,
        is_read
    ) VALUES (%s, %s, %s, %s, %s, %s)
    """,
    notification_rows,
)
conn.commit()

# REPORTS
report_rows = []
for i in range(1, 201):
    reporter_id = user_ids[(i - 1) % len(user_ids)]
    reported_user_id = user_ids[(i * 2) % len(user_ids)]
    if reporter_id == reported_user_id:
        reported_user_id = user_ids[(i + 1) % len(user_ids)]
    report_rows.append(
        (
            reporter_id,
            reported_user_id,
            item_ids[(i - 1) % len(item_ids)],
            None,
            f'Reason {i}: item details or pricing do not match the listing.',
            'OPEN',
            None,
        )
    )
cur.executemany(
    """
    INSERT INTO reports (
        reporter_id,
        reported_user_id,
        item_id,
        post_id,
        reason,
        status,
        reviewed_by
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """,
    report_rows,
)
conn.commit()

# ITEM PREDICTIONS
item_prediction_rows = []
for i in range(1, 201):
    item_prediction_rows.append(
        (
            item_ids[(i - 1) % len(item_ids)],
            'campus-item-classifier-v1',
            categories[(i - 1) % len(categories)],
            round(0.75 + (i % 25) * 0.01, 4),
        )
    )
cur.executemany(
    """
    INSERT INTO item_predictions (
        item_id,
        model_name,
        predicted_category,
        confidence
    ) VALUES (%s, %s, %s, %s)
    """,
    item_prediction_rows,
)
conn.commit()

# VERIFICATION CODES
verification_rows = []
for i in range(1, 201):
    user_id = user_ids[(i - 1) % len(user_ids)]
    channel = 'EMAIL' if i % 2 == 0 else 'PHONE'
    destination = (
        f'{user_id}student{(i % 99) + 1}@campusxmart.test'
        if channel == 'EMAIL' else
        f'+88017{(i * 13) % 100000000:08d}'
    )
    verification_rows.append(
        (
            user_id,
            channel,
            destination,
            f'$2b$12$verify{i:04d}aaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            datetime.now() + timedelta(days=2),
            None,
            0,
        )
    )
cur.executemany(
    """
    INSERT INTO verification_codes (
        user_id,
        channel,
        destination,
        code_hash,
        expires_at,
        verified_at,
        attempt_count
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """,
    verification_rows,
)
conn.commit()

# USER SESSIONS
session_rows = []
for i in range(1, 201):
    session_rows.append(
        (
            str(uuid4()),
            user_ids[(i - 1) % len(user_ids)],
            f'$2b$12$session{i:04d}aaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            datetime.now() + timedelta(days=30),
            None,
        )
    )
cur.executemany(
    """
    INSERT INTO user_sessions (
        session_id,
        user_id,
        refresh_token_hash,
        expires_at,
        revoked_at
    ) VALUES (%s, %s, %s, %s, %s)
    """,
    session_rows,
)
conn.commit()

# Final verification count printout.
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name NOT LIKE 'pg_%' ORDER BY table_name")
for (table_name,) in cur.fetchall():
    cur.execute(f'SELECT COUNT(*) FROM {table_name}')
    count = cur.fetchone()[0]
    print(f'{table_name}: {count}')

conn.close()
