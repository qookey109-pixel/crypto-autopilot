-- Shared Cloudflare writer admission V0.1.
-- Prepare-only: never applied automatically; does not provision or activate D1.
-- Reservations are retained conservatively. A future retention/compaction authority
-- is required before this table approaches its bounded account storage envelope.
CREATE TABLE IF NOT EXISTS cloudflare_shared_writer_reservations_v0_1 (
    writer_id TEXT NOT NULL
        CHECK (length(writer_id) BETWEEN 1 AND 128),
    idempotency_key TEXT NOT NULL
        CHECK (length(idempotency_key) BETWEEN 1 AND 200),
    slot_id TEXT NOT NULL
        CHECK (length(slot_id) BETWEEN 1 AND 200),
    utc_day TEXT NOT NULL
        CHECK (length(utc_day) = 10),
    reserved_at_ms INTEGER NOT NULL CHECK (reserved_at_ms >= 0),
    provider_requests INTEGER NOT NULL CHECK (provider_requests >= 0),
    r2_class_a INTEGER NOT NULL CHECK (r2_class_a >= 0),
    r2_class_b INTEGER NOT NULL CHECK (r2_class_b >= 0),
    r2_new_bytes INTEGER NOT NULL CHECK (r2_new_bytes >= 0),
    d1_queries INTEGER NOT NULL CHECK (d1_queries >= 0),
    d1_storage_growth_bytes INTEGER NOT NULL
        CHECK (d1_storage_growth_bytes >= 0),
    PRIMARY KEY (writer_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS cloudflare_shared_writer_day_v0_1_idx
ON cloudflare_shared_writer_reservations_v0_1 (utc_day);

CREATE INDEX IF NOT EXISTS cloudflare_shared_writer_time_v0_1_idx
ON cloudflare_shared_writer_reservations_v0_1 (reserved_at_ms);
