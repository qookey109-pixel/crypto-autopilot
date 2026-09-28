-- Cloud Paper settlement recovery audit V0.1.
-- Prepare-only additive migration: never run automatically and never provisions D1.
-- Recovery receipts prove that a RESERVED slot has a fully verified immutable
-- Cloud Paper result. They intentionally do not settle or release its envelope.
CREATE TABLE IF NOT EXISTS cloud_paper_settlement_recovery_receipts (
    slot_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    report_id TEXT NOT NULL CHECK (length(report_id) = 64),
    recovered_at_ms INTEGER NOT NULL CHECK (recovered_at_ms >= 0)
);

CREATE INDEX IF NOT EXISTS cloud_paper_settlement_recovery_run_idx
ON cloud_paper_settlement_recovery_receipts (run_id);
