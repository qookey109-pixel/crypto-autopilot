-- DRAFT / SYNTHETIC ONLY. No database provisioning or execution authority.
-- Independent credentials, prepaid cost bounds and sole gateway remain unverified.
CREATE TABLE paper_job_claim_v0_1 (
  repository_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  attempt TEXT NOT NULL CHECK (attempt = '1'),
  check_run_id TEXT NOT NULL,
  writer_id TEXT NOT NULL,
  slot_id TEXT NOT NULL,
  PRIMARY KEY (repository_id, run_id, attempt, check_run_id, writer_id),
  UNIQUE (repository_id, writer_id, slot_id)
);

-- Defense in depth only: a schema administrator can remove these triggers.
CREATE TRIGGER paper_job_claim_no_update_v0_1
BEFORE UPDATE ON paper_job_claim_v0_1
BEGIN
  SELECT RAISE(ABORT, 'PAPER_JOB_CLAIM_IMMUTABLE');
END;
CREATE TRIGGER paper_job_claim_no_delete_v0_1
BEFORE DELETE ON paper_job_claim_v0_1
BEGIN
  SELECT RAISE(ABORT, 'PAPER_JOB_CLAIM_IMMUTABLE');
END;

-- Prevent INSERT OR REPLACE from deleting an existing claim, even where
-- SQLite recursive delete triggers are disabled. The two indexed probes add
-- D1 cost; production row-read/write ceilings remain unmeasured.
CREATE TRIGGER paper_job_claim_no_replace_v0_1
BEFORE INSERT ON paper_job_claim_v0_1
WHEN EXISTS (
  SELECT 1 FROM paper_job_claim_v0_1
  WHERE repository_id = NEW.repository_id AND run_id = NEW.run_id
    AND attempt = NEW.attempt AND check_run_id = NEW.check_run_id
    AND writer_id = NEW.writer_id
) OR EXISTS (
  SELECT 1 FROM paper_job_claim_v0_1
  WHERE repository_id = NEW.repository_id AND writer_id = NEW.writer_id
    AND slot_id = NEW.slot_id
)
BEGIN
  SELECT RAISE(IGNORE);
END;
