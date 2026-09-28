-- Cloud Paper shared D1 daily row reservation V0.1.
-- Prepare-only additive migration: do not apply automatically or provision D1.
-- One row per UTC day holds monotonic shared reservations. Reservations are
-- never decremented during that day; failed or ambiguous calls stay charged.
CREATE TABLE IF NOT EXISTS cloud_paper_d1_daily_rows_budget (
    utc_day TEXT PRIMARY KEY,
    baseline_rows_read INTEGER NOT NULL CHECK (baseline_rows_read >= 0),
    baseline_rows_written INTEGER NOT NULL CHECK (baseline_rows_written >= 0),
    reserved_rows_read INTEGER NOT NULL CHECK (reserved_rows_read >= 0),
    reserved_rows_written INTEGER NOT NULL CHECK (reserved_rows_written >= 0),
    reservation_count INTEGER NOT NULL CHECK (reservation_count > 0)
);
