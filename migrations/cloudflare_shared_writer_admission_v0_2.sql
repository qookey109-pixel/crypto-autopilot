-- Shared Cloudflare writer admission V0.2.
-- Prepare-only. Capacity is a hard stop; this migration does not prune,
-- archive, provision, or activate production D1.
CREATE TABLE IF NOT EXISTS cloudflare_shared_writer_admission_capacity_v0_2 (
    capacity_id INTEGER PRIMARY KEY CHECK (capacity_id = 1),
    retained_reservations INTEGER NOT NULL CHECK (retained_reservations >= 0),
    max_retained_reservations INTEGER
        CHECK (max_retained_reservations IS NULL OR max_retained_reservations > 0)
);
INSERT INTO cloudflare_shared_writer_admission_capacity_v0_2
    (capacity_id, retained_reservations, max_retained_reservations)
VALUES (1, 0, NULL)
ON CONFLICT(capacity_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS cloudflare_shared_writer_reservations_v0_2 (
    writer_id TEXT NOT NULL CHECK (length(writer_id) BETWEEN 1 AND 128),
    idempotency_key TEXT NOT NULL CHECK (length(idempotency_key) BETWEEN 1 AND 200),
    slot_id TEXT NOT NULL CHECK (length(slot_id) BETWEEN 1 AND 200),
    utc_day TEXT NOT NULL CHECK (length(utc_day) = 10),
    reserved_at_ms INTEGER NOT NULL CHECK (reserved_at_ms >= 0),
    provider_requests INTEGER NOT NULL CHECK (provider_requests >= 0),
    r2_class_a INTEGER NOT NULL CHECK (r2_class_a >= 0),
    r2_class_b INTEGER NOT NULL CHECK (r2_class_b >= 0),
    r2_new_bytes INTEGER NOT NULL CHECK (r2_new_bytes >= 0),
    d1_queries INTEGER NOT NULL CHECK (d1_queries >= 0),
    d1_rows_written INTEGER NOT NULL CHECK (d1_rows_written >= 0),
    d1_storage_growth_bytes INTEGER NOT NULL CHECK (d1_storage_growth_bytes >= 0),
    PRIMARY KEY (writer_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS cloudflare_shared_writer_day_v0_2_idx
ON cloudflare_shared_writer_reservations_v0_2 (utc_day);
CREATE INDEX IF NOT EXISTS cloudflare_shared_writer_time_v0_2_idx
ON cloudflare_shared_writer_reservations_v0_2 (reserved_at_ms);

CREATE TRIGGER IF NOT EXISTS cloudflare_shared_writer_capacity_insert_v0_2
AFTER INSERT ON cloudflare_shared_writer_reservations_v0_2
BEGIN
    UPDATE cloudflare_shared_writer_admission_capacity_v0_2
    SET retained_reservations = retained_reservations + 1
    WHERE capacity_id = 1;
END;
