DO $migration$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM item_media
        GROUP BY item_id
        HAVING COUNT(*) > 32768
    ) THEN
        RAISE EXCEPTION 'An item has more media rows than SMALLINT sort_order can represent.';
    END IF;
END;
$migration$;

DROP INDEX IF EXISTS idx_item_media_item_sort_order;

WITH ordered_media AS (
    SELECT media_id,
           (ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY sort_order, media_id) - 1)::SMALLINT AS new_sort_order
    FROM item_media
)
UPDATE item_media AS media
SET sort_order = ordered_media.new_sort_order
FROM ordered_media
WHERE media.media_id = ordered_media.media_id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_item_media_item_sort_order
    ON item_media (item_id, sort_order);
