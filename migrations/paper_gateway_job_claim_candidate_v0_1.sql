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
