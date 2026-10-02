-- Campus X Mart: corrected PostgreSQL schema
-- This is a clean baseline schema for a NEW database, not a migration for
-- the existing schema.sql. Keep password_hash values hashed (PBKDF2-SHA256),
-- never store plain-text passwords.

CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    profile_image_url TEXT,
    role VARCHAR(20) NOT NULL DEFAULT 'STUDENT'
        CHECK (role IN ('STUDENT', 'ADMIN')),
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    phone_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    posting_banned BOOLEAN NOT NULL DEFAULT FALSE,
    posting_ban_reason TEXT,
    posting_banned_at TIMESTAMPTZ,
    posting_banned_by BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (char_length(username) >= 3)
);

-- One-time codes for email or phone verification. Store code_hash rather than
-- the raw OTP in a production system.
CREATE TABLE verification_codes (
    verification_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    channel VARCHAR(10) NOT NULL CHECK (channel IN ('EMAIL', 'PHONE')),
    destination VARCHAR(150) NOT NULL,
    code_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    verified_at TIMESTAMPTZ,
    attempt_count SMALLINT NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX verification_codes_lookup_idx
    ON verification_codes (user_id, channel, created_at DESC)
    WHERE verified_at IS NULL;

-- Optional server-side refresh-token/session tracking for JWT logout/revocation.
CREATE TABLE user_sessions (
    session_id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE websocket_tickets (
    ticket_hash CHAR(64) PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX websocket_tickets_expires_at_idx ON websocket_tickets (expires_at);

CREATE TABLE locations (
    location_id BIGSERIAL PRIMARY KEY,
    location_name VARCHAR(100) NOT NULL,
    campus_name VARCHAR(100),
    address TEXT,
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
);

CREATE TABLE items (
    item_id BIGSERIAL PRIMARY KEY,
    seller_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    location_id BIGINT REFERENCES locations(location_id) ON DELETE SET NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    category VARCHAR(50) NOT NULL,
    item_condition VARCHAR(30) NOT NULL
        CHECK (item_condition IN ('NEW', 'USED_EXCELLENT', 'USED_GOOD', 'USED')),
    available_from DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE'
        CHECK (status IN ('DRAFT', 'AVAILABLE', 'RESERVED', 'SOLD', 'ARCHIVED')),
    video_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Cloudinary/S3/Firebase URLs for multiple item images, videos, or documents.
CREATE TABLE item_media (
    media_id BIGSERIAL PRIMARY KEY,
    item_id BIGINT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
    media_type VARCHAR(10) NOT NULL CHECK (media_type IN ('IMAGE', 'VIDEO', 'FILE', 'AUDIO')),
    storage_provider VARCHAR(30) NOT NULL,
    media_url TEXT NOT NULL,
    public_id VARCHAR(255),
    original_filename VARCHAR(255),
    sort_order SMALLINT NOT NULL DEFAULT 0 CHECK (sort_order >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- A marketplace/feed post may optionally promote one item.
CREATE TABLE posts (
    post_id BIGSERIAL PRIMARY KEY,
    author_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    item_id BIGINT REFERENCES items(item_id) ON DELETE SET NULL,
    caption TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE post_media (
    media_id BIGSERIAL PRIMARY KEY,
    post_id BIGINT NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
    media_type VARCHAR(10) NOT NULL CHECK (media_type IN ('IMAGE', 'VIDEO', 'FILE', 'AUDIO')),
    storage_provider VARCHAR(30) NOT NULL,
    media_url TEXT NOT NULL,
    public_id VARCHAR(255),
    sort_order SMALLINT NOT NULL DEFAULT 0 CHECK (sort_order >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE post_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    post_id BIGINT NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
    author_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    parent_comment_id BIGINT,
    comment_text TEXT NOT NULL CHECK (char_length(trim(comment_text)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (post_id, comment_id),
    -- A reply can only point to another comment belonging to the same post.
    FOREIGN KEY (post_id, parent_comment_id)
        REFERENCES post_comments(post_id, comment_id) ON DELETE CASCADE
);

CREATE TABLE item_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    item_id BIGINT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
    author_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    comment_text TEXT NOT NULL CHECK (char_length(trim(comment_text)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- UNIQUE prevents one user from reacting more than once to the same target.
CREATE TABLE post_reactions (
    post_id BIGINT NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    reaction_type VARCHAR(10) NOT NULL CHECK (reaction_type IN ('LIKE', 'DISLIKE')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, user_id)
);

CREATE TABLE item_reactions (
    item_id BIGINT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    reaction_type VARCHAR(10) NOT NULL CHECK (reaction_type IN ('LIKE', 'DISLIKE')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (item_id, user_id)
);

CREATE TABLE reviews (
    review_id BIGSERIAL PRIMARY KEY,
    item_id BIGINT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (item_id, user_id)
);

CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    item_id BIGINT NOT NULL REFERENCES items(item_id) ON DELETE RESTRICT,
    buyer_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    seller_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    agreed_price NUMERIC(10, 2) NOT NULL CHECK (agreed_price >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'CONFIRMED', 'CANCELLED', 'COMPLETED')),
    meetup_date DATE,
    ordered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (buyer_id <> seller_id)
);

CREATE TABLE messages (
    message_id BIGSERIAL PRIMARY KEY,
    sender_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    receiver_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    message_text TEXT NOT NULL CHECK (char_length(trim(message_text)) > 0),
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (sender_id <> receiver_id)
);

CREATE TABLE message_hidden_for (
    message_id BIGINT NOT NULL REFERENCES messages(message_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    hidden_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (message_id, user_id)
);

CREATE TABLE notifications (
    notification_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    notification_type VARCHAR(30) NOT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    target_url TEXT,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reports (
    report_id BIGSERIAL PRIMARY KEY,
    reporter_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    reported_user_id BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    item_id BIGINT REFERENCES items(item_id) ON DELETE SET NULL,
    post_id BIGINT REFERENCES posts(post_id) ON DELETE SET NULL,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'REVIEWING', 'RESOLVED', 'REJECTED')),
    reviewed_by BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ,
    CHECK (reported_user_id IS NOT NULL OR item_id IS NOT NULL OR post_id IS NOT NULL)
);

-- Stores results produced by TensorFlow Lite or an equivalent ML model.
CREATE TABLE item_predictions (
    prediction_id BIGSERIAL PRIMARY KEY,
    item_id BIGINT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL,
    predicted_category VARCHAR(50) NOT NULL,
    confidence NUMERIC(5, 4) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for foreign-key joins, feed queries, and pagination.
CREATE INDEX idx_items_seller_status_created ON items (seller_id, status, created_at DESC);
CREATE INDEX idx_items_category_status_created ON items (category, status, created_at DESC);
CREATE INDEX idx_posts_author_created ON posts (author_id, created_at DESC);
CREATE INDEX idx_post_comments_post_created ON post_comments (post_id, created_at ASC);
CREATE INDEX idx_item_comments_item_created ON item_comments (item_id, created_at ASC);
CREATE INDEX idx_reviews_item ON reviews (item_id);
CREATE INDEX idx_orders_buyer ON orders (buyer_id, ordered_at DESC);
CREATE INDEX idx_orders_seller ON orders (seller_id, ordered_at DESC);
CREATE UNIQUE INDEX idx_orders_one_active_per_item
    ON orders (item_id)
    WHERE status IN ('CONFIRMED', 'COMPLETED');
CREATE INDEX idx_messages_conversation ON messages (sender_id, receiver_id, sent_at DESC);
CREATE INDEX idx_notifications_user_unread ON notifications (user_id, is_read, created_at DESC);

-- API-level rules still required:
-- 1. A buyer cannot order their own item.
-- 2. orders.seller_id must equal items.seller_id.
-- 3. A user should not review or react to their own item/post.
-- 4. Only one active order should be allowed when an item is sold/reserved.
