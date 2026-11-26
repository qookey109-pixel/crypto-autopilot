-- Preparation only. Apply once after the V0.1 candidate schema in an isolated CI database.
-- Unknown historical observations remain NULL; the V0.2 adapter blocks on any such row.
ALTER TABLE paper_job_claim_v0_1 ADD COLUMN observed_at_ms INTEGER
  CHECK (observed_at_ms IS NULL OR (typeof(observed_at_ms) = 'integer'
         AND observed_at_ms BETWEEN 0 AND 9007199254740991));

CREATE INDEX paper_job_observed_clock_v0_2 ON paper_job_claim_v0_1(observed_at_ms);

-- A legacy client cannot create an unclocked claim after migration.
CREATE TRIGGER paper_job_require_observation_v0_2
BEFORE INSERT ON paper_job_claim_v0_1 WHEN NEW.observed_at_ms IS NULL
BEGIN
  SELECT RAISE(ABORT, 'PAPER_JOB_CLOCK_REQUIRED');
END;
