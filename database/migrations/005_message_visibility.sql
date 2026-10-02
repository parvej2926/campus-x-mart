CREATE TABLE IF NOT EXISTS message_hidden_for (
    message_id BIGINT NOT NULL REFERENCES messages(message_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    hidden_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (message_id, user_id)
);