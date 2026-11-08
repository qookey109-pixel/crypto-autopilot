// Prepared adapter only: it is not an identity or account-budget boundary.
// The caller must prepay this write and supply verified, server-derived values.
// No Worker route, D1 binding, table creation or live execution is authorized.
const INSERT = "INSERT INTO paper_job_claim_v0_1 " +
  "(repository_id, run_id, attempt, check_run_id, writer_id, slot_id) " +
  "VALUES (?1, ?2, ?3, ?4, ?5, ?6) ON CONFLICT DO NOTHING";
const id = x => typeof x === "string" && /^[1-9][0-9]{0,19}$/.test(x);
export async function claimJobSlot(database, claim, { enabled = false, limits } = {}) {
  if (enabled !== true) return "DISABLED";
  if (!limits || !Number.isSafeInteger(limits.rowsRead) || limits.rowsRead < 0 ||
      !Number.isSafeInteger(limits.rowsWritten) || limits.rowsWritten < 0 ||
      !Number.isSafeInteger(limits.maxDatabaseBytes) || limits.maxDatabaseBytes < 0) return "INVALID";
  if (!claim || !id(claim.repositoryId) || !id(claim.runId) || claim.attempt !== "1" ||
      !id(claim.checkRunId) || typeof claim.writerId !== "string" ||
      !/^[a-z0-9][a-z0-9:._/-]{0,127}$/.test(claim.writerId) ||
      typeof claim.slotId !== "string" || !/^slot:(0|[1-9][0-9]{0,15})$/.test(claim.slotId)) return "INVALID";
  try {
    const result = await database.prepare(INSERT).bind(
      claim.repositoryId, claim.runId, claim.attempt, claim.checkRunId,
      claim.writerId, claim.slotId,
    ).run();
    if (result?.success !== true || result.meta?.total_attempts !== 1 ||
        !Number.isSafeInteger(result.meta?.rows_read) || result.meta.rows_read < 0 ||
        result.meta.rows_read > limits.rowsRead || !Number.isSafeInteger(result.meta?.rows_written) ||
        result.meta.rows_written < 0 || result.meta.rows_written > limits.rowsWritten ||
        !Number.isSafeInteger(result.meta.size_after) || result.meta.size_after < 0 ||
        result.meta.size_after > limits.maxDatabaseBytes) return "REVIEW_REQUIRED";
    if (result.meta.changes === 1 && result.meta.rows_written >= 1) return "CLAIMED";
    if (result.meta.changes === 0 && result.meta.rows_written === 0) return "DUPLICATE_OR_CONFLICT";
    return "REVIEW_REQUIRED";
  } catch { return "REVIEW_REQUIRED"; }
}
