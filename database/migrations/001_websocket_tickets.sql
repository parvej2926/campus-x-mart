CREATE TABLE IF NOT EXISTS websocket_tickets (
    ticket_hash CHAR(64) PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS websocket_tickets_expires_at_idx
    ON websocket_tickets (expires_at);
