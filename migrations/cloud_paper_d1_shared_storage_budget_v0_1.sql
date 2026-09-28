-- Cloud Paper shared D1 daily storage-growth reservation V0.1.
-- Prepare-only successor migration; apply only under a separate execution authority.
-- Storage reservations are monotonic within each UTC day and never released.
ALTER TABLE cloud_paper_d1_daily_rows_budget
ADD COLUMN baseline_storage_bytes INTEGER NOT NULL DEFAULT 0
CHECK (baseline_storage_bytes >= 0);

ALTER TABLE cloud_paper_d1_daily_rows_budget
ADD COLUMN reserved_storage_bytes INTEGER NOT NULL DEFAULT 0
CHECK (reserved_storage_bytes >= 0);
