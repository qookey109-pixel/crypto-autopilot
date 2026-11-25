// Prepared adapter only: it is not an identity or account-budget boundary.
// The caller must prepay this write and supply verified, server-derived values.
// No Worker route, D1 binding, table creation or live execution is authorized.
import { isManualWriter, normalizeManualInputs } from "./manual-dispatch.mjs";
const INSERT = "INSERT INTO paper_job_claim_v0_1 " +
  "(repository_id, run_id, attempt, check_run_id, writer_id, slot_id, observed_at_ms, operation_scope_json) " +
  "SELECT ?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8 " +
  "WHERE NOT EXISTS (SELECT 1 FROM paper_job_claim_v0_1 INDEXED BY paper_job_observed_clock_v0_2 " +
  "WHERE observed_at_ms > ?7) AND NOT EXISTS " +
  "(SELECT 1 FROM paper_job_claim_v0_1 INDEXED BY paper_job_observed_clock_v0_2 " +
  "WHERE observed_at_ms IS NULL) ON CONFLICT DO NOTHING";
const id = x => typeof x === "string" && /^[1-9][0-9]{0,19}$/.test(x);
export async function claimJobSlot(database, claim, { enabled = false, limits } = {}) {
  if (enabled !== true) return "DISABLED";
  if (!limits || !Number.isSafeInteger(limits.rowsRead) || limits.rowsRead < 1 ||
      !Number.isSafeInteger(limits.rowsWritten) || limits.rowsWritten < 4 ||
      !Number.isSafeInteger(limits.maxDatabaseBytes) || limits.maxDatabaseBytes < 0) return "INVALID";
  if (!claim || !Number.isSafeInteger(claim.observedAtMs) || claim.observedAtMs < 0 ||
      !id(claim.repositoryId) || !id(claim.runId) || claim.attempt !== "1" ||
      !id(claim.checkRunId) || typeof claim.writerId !== "string" ||
      !/^[a-z0-9][a-z0-9:._/-]{0,127}$/.test(claim.writerId) ||
      typeof claim.slotId !== "string" || !/^slot:(0|[1-9][0-9]{0,15})$/.test(claim.slotId)) return "INVALID";
  const slotStart = Number(claim.slotId.slice(5));
  if (!Number.isSafeInteger(slotStart) || claim.observedAtMs < slotStart ||
      claim.observedAtMs - slotStart > 600000 ||
      Math.floor(claim.observedAtMs / 86400000) !== Math.floor(slotStart / 86400000)) return "INVALID";
  let scopeJson = null;
  if (isManualWriter(claim.writerId)) {
    const scope = claim.operationScope;
    const inputs = normalizeManualInputs(claim.writerId, scope?.inputs);
    if (!inputs || typeof scope.sourceSha !== "string" || !/^[a-f0-9]{40}$/.test(scope.sourceSha)) return "INVALID";
    scopeJson = JSON.stringify({ sourceSha: scope.sourceSha, inputs });
  } else if (claim.operationScope != null) return "INVALID";
  try {
    const result = await database.prepare(INSERT).bind(
      claim.repositoryId, claim.runId, claim.attempt, claim.checkRunId,
      claim.writerId, claim.slotId, claim.observedAtMs, scopeJson,
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
