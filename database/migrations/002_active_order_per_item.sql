CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_one_active_per_item
    ON orders (item_id)
    WHERE status IN ('CONFIRMED', 'COMPLETED');