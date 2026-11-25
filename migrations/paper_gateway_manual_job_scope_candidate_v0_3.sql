-- Synthetic candidate only. Preserve historical claims and prevent an older
-- client from creating a scope-free coordinator or recovery claim.
ALTER TABLE paper_job_claim_v0_1 ADD COLUMN operation_scope_json TEXT;
CREATE TRIGGER paper_job_scope_required_v0_3 BEFORE INSERT ON paper_job_claim_v0_1
WHEN CASE WHEN NEW.writer_id IN (
    'crypto-autopilot:live-paper-run-coordinator-v0-1', 'crypto-autopilot:live-paper-run-recovery-v0-1'
  ) THEN NEW.operation_scope_json IS NULL OR length(CAST(NEW.operation_scope_json AS BLOB)) NOT BETWEEN 1 AND 1024
    ELSE NEW.operation_scope_json IS NOT NULL END
BEGIN
  SELECT RAISE(ABORT, 'PAPER_JOB_SCOPE_INVALID');
END;
