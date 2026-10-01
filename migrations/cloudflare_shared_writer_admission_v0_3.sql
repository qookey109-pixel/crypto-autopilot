-- Shared Cloudflare writer admission V0.3 lifecycle successor.
-- Prepared schema only. Fresh successor schema; no V0.2 production migration,
-- D1 provisioning, Cloudflare access, or automatic compaction is authorized.
CREATE TABLE IF NOT EXISTS cloudflare_shared_writer_lifecycle_policy_v0_3 (
    policy_id INTEGER PRIMARY KEY CHECK (policy_id = 1),
    retained_reservations INTEGER NOT NULL DEFAULT 0
        CHECK (retained_reservations >= 0),
    lifetime_writer_identities INTEGER NOT NULL DEFAULT 0
        CHECK (lifetime_writer_identities >= 0),
    max_active_reservations INTEGER
        CHECK (max_active_reservations IS NULL OR max_active_reservations > 0),
    max_lifetime_writer_identities INTEGER
        CHECK (max_lifetime_writer_identities IS NULL
               OR max_lifetime_writer_identities > 0)
);
INSERT INTO cloudflare_shared_writer_lifecycle_policy_v0_3
    (policy_id, retained_reservations, lifetime_writer_identities,
     max_active_reservations, max_lifetime_writer_identities)
VALUES (1, 0, 0, NULL, NULL)
ON CONFLICT(policy_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS cloudflare_shared_writer_identities_v0_3 (
    writer_id TEXT PRIMARY KEY CHECK (length(writer_id) BETWEEN 1 AND 128),
    lifecycle_state TEXT NOT NULL CHECK (lifecycle_state IN ('ACTIVE', 'RETIRED')),
    owner_attestation_sha256 TEXT NOT NULL
        CHECK (length(owner_attestation_sha256) = 64),
    registered_at_ms INTEGER NOT NULL CHECK (registered_at_ms >= 0)
);

CREATE TRIGGER IF NOT EXISTS cloudflare_writer_identity_cap_v0_3
BEFORE INSERT ON cloudflare_shared_writer_identities_v0_3
WHEN NOT EXISTS (
    SELECT 1
    FROM cloudflare_shared_writer_lifecycle_policy_v0_3
    WHERE policy_id = 1
      AND max_lifetime_writer_identities IS NOT NULL
      AND lifetime_writer_identities < max_lifetime_writer_identities
)
BEGIN
    SELECT RAISE(ABORT, 'BLOCKED_WRITER_IDENTITY_CAP');
END;

CREATE TRIGGER IF NOT EXISTS cloudflare_writer_identity_insert_v0_3
AFTER INSERT ON cloudflare_shared_writer_identities_v0_3
BEGIN
    UPDATE cloudflare_shared_writer_lifecycle_policy_v0_3
    SET lifetime_writer_identities = lifetime_writer_identities + 1
    WHERE policy_id = 1;
END;

CREATE TRIGGER IF NOT EXISTS cloudflare_writer_identity_no_delete_v0_3
BEFORE DELETE ON cloudflare_shared_writer_identities_v0_3
BEGIN
    SELECT RAISE(ABORT, 'WRITER_IDENTITY_DELETE_FORBIDDEN');
END;

CREATE TABLE IF NOT EXISTS cloudflare_shared_writer_retirement_watermarks_v0_3 (
    writer_id TEXT PRIMARY KEY
        REFERENCES cloudflare_shared_writer_identities_v0_3(writer_id),
    retired_through_slot_at_ms INTEGER NOT NULL CHECK (retired_through_slot_at_ms >= 0),
    retired_reservation_count INTEGER NOT NULL CHECK (retired_reservation_count > 0)
);

CREATE TABLE IF NOT EXISTS cloudflare_shared_writer_reservations_v0_3 (
    writer_id TEXT NOT NULL
        REFERENCES cloudflare_shared_writer_identities_v0_3(writer_id),
    slot_id TEXT NOT NULL CHECK (length(slot_id) BETWEEN 6 AND 32),
    idempotency_key TEXT NOT NULL CHECK (idempotency_key = slot_id),
    slot_at_ms INTEGER NOT NULL CHECK (slot_at_ms > 0),
    utc_day TEXT NOT NULL CHECK (
        length(utc_day) = 10
        AND utc_day = date(CAST(reserved_at_ms / 1000 AS INTEGER), 'unixepoch')
        AND date(CAST(reserved_at_ms / 1000 AS INTEGER), 'unixepoch') IS NOT NULL
    ),
    reserved_at_ms INTEGER NOT NULL CHECK (reserved_at_ms >= 0),
    provider_requests INTEGER NOT NULL CHECK (provider_requests >= 0),
    r2_class_a INTEGER NOT NULL CHECK (r2_class_a >= 0),
    r2_class_b INTEGER NOT NULL CHECK (r2_class_b >= 0),
    r2_new_bytes INTEGER NOT NULL CHECK (r2_new_bytes >= 0),
    d1_queries INTEGER NOT NULL CHECK (d1_queries >= 0),
    d1_rows_read INTEGER NOT NULL CHECK (d1_rows_read >= 0),
    d1_rows_written INTEGER NOT NULL CHECK (d1_rows_written >= 0),
    d1_storage_growth_bytes INTEGER NOT NULL CHECK (d1_storage_growth_bytes >= 0),
    CHECK (slot_id = 'slot:' || CAST(slot_at_ms AS TEXT)),
    PRIMARY KEY (writer_id, slot_id)
);
CREATE INDEX IF NOT EXISTS cloudflare_shared_writer_day_v0_3_idx
ON cloudflare_shared_writer_reservations_v0_3 (utc_day);
CREATE INDEX IF NOT EXISTS cloudflare_shared_writer_time_v0_3_idx
ON cloudflare_shared_writer_reservations_v0_3 (reserved_at_ms);

CREATE TRIGGER IF NOT EXISTS cloudflare_writer_reservation_writer_gate_v0_3
BEFORE INSERT ON cloudflare_shared_writer_reservations_v0_3
WHEN NOT EXISTS (
    SELECT 1
    FROM cloudflare_shared_writer_identities_v0_3
    WHERE writer_id = NEW.writer_id AND lifecycle_state = 'ACTIVE'
)
BEGIN
    SELECT RAISE(ABORT, 'BLOCKED_WRITER_REGISTRATION');
END;

CREATE TRIGGER IF NOT EXISTS cloudflare_writer_reservation_watermark_gate_v0_3
BEFORE INSERT ON cloudflare_shared_writer_reservations_v0_3
WHEN EXISTS (
    SELECT 1
    FROM cloudflare_shared_writer_retirement_watermarks_v0_3
    WHERE writer_id = NEW.writer_id
      AND NEW.slot_at_ms <= retired_through_slot_at_ms
)
BEGIN
    SELECT RAISE(ABORT, 'BLOCKED_STALE_WRITER_SLOT');
END;

CREATE TRIGGER IF NOT EXISTS cloudflare_writer_reservation_capacity_gate_v0_3
BEFORE INSERT ON cloudflare_shared_writer_reservations_v0_3
WHEN NOT EXISTS (
    SELECT 1
    FROM cloudflare_shared_writer_lifecycle_policy_v0_3
    WHERE policy_id = 1
      AND max_active_reservations IS NOT NULL
      AND retained_reservations < max_active_reservations
)
BEGIN
    SELECT RAISE(ABORT, 'BLOCKED_RESERVATION_CAPACITY');
END;

CREATE TRIGGER IF NOT EXISTS cloudflare_writer_reservation_insert_v0_3
AFTER INSERT ON cloudflare_shared_writer_reservations_v0_3
BEGIN
    UPDATE cloudflare_shared_writer_lifecycle_policy_v0_3
    SET retained_reservations = retained_reservations + 1
    WHERE policy_id = 1;
END;

CREATE TRIGGER IF NOT EXISTS cloudflare_writer_reservation_delete_v0_3
AFTER DELETE ON cloudflare_shared_writer_reservations_v0_3
BEGIN
    INSERT INTO cloudflare_shared_writer_retirement_watermarks_v0_3
        (writer_id, retired_through_slot_at_ms, retired_reservation_count)
    VALUES (OLD.writer_id, OLD.slot_at_ms, 1)
    ON CONFLICT(writer_id) DO UPDATE SET
        retired_through_slot_at_ms = MAX(
            cloudflare_shared_writer_retirement_watermarks_v0_3.retired_through_slot_at_ms,
            excluded.retired_through_slot_at_ms
        ),
        retired_reservation_count =
            cloudflare_shared_writer_retirement_watermarks_v0_3.retired_reservation_count + 1;

    UPDATE cloudflare_shared_writer_lifecycle_policy_v0_3
    SET retained_reservations = retained_reservations - 1
    WHERE policy_id = 1;
END;

CREATE TRIGGER IF NOT EXISTS cloudflare_writer_reservation_no_update_v0_3
BEFORE UPDATE ON cloudflare_shared_writer_reservations_v0_3
BEGIN
    SELECT RAISE(ABORT, 'RESERVATION_UPDATE_FORBIDDEN');
END;
