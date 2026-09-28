-- Cloud Paper D1 reservation ledger V0.1.
-- Prepare-only migration: never run automatically and never provisions a database.
CREATE TABLE IF NOT EXISTS cloud_paper_budget_meta (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    reservation_count INTEGER NOT NULL CHECK (reservation_count >= 0)
);

INSERT OR IGNORE INTO cloud_paper_budget_meta (singleton, reservation_count)
VALUES (1, 0);

CREATE TABLE IF NOT EXISTS cloud_paper_budget_reservations (
    slot_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    reserved_at_ms INTEGER NOT NULL CHECK (reserved_at_ms >= 0),
    measured_through_ms INTEGER NOT NULL CHECK (measured_through_ms >= 0),
    state TEXT NOT NULL CHECK (state IN ('RESERVED', 'SETTLED')),
    reserved_provider_requests INTEGER NOT NULL CHECK (reserved_provider_requests >= 0),
    reserved_class_a INTEGER NOT NULL CHECK (reserved_class_a >= 0),
    reserved_class_b INTEGER NOT NULL CHECK (reserved_class_b >= 0),
    reserved_new_bytes INTEGER NOT NULL CHECK (reserved_new_bytes >= 0),
    actual_provider_requests INTEGER CHECK (actual_provider_requests >= 0),
    actual_class_a INTEGER CHECK (actual_class_a >= 0),
    actual_class_b INTEGER CHECK (actual_class_b >= 0),
    actual_new_bytes INTEGER CHECK (actual_new_bytes >= 0),
    CHECK (
        (state = 'RESERVED' AND actual_provider_requests IS NULL
         AND actual_class_a IS NULL AND actual_class_b IS NULL
         AND actual_new_bytes IS NULL)
        OR
        (state = 'SETTLED' AND actual_provider_requests IS NOT NULL
         AND actual_class_a IS NOT NULL AND actual_class_b IS NOT NULL
         AND actual_new_bytes IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS cloud_paper_budget_reserved_at_idx
ON cloud_paper_budget_reservations (reserved_at_ms);

CREATE INDEX IF NOT EXISTS cloud_paper_budget_run_id_idx
ON cloud_paper_budget_reservations (run_id);

CREATE TRIGGER IF NOT EXISTS cloud_paper_budget_count_insert
AFTER INSERT ON cloud_paper_budget_reservations
BEGIN
    UPDATE cloud_paper_budget_meta
    SET reservation_count = reservation_count + 1
    WHERE singleton = 1;
END;
