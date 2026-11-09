// Synthetic metadata comparison only. Inputs must be read by a trusted
// server-side caller from fixed GitHub endpoints under a separate authority.
// The OIDC identity must already have been signature-verified; this function
// does not fetch, authenticate, authorize a slot, or prepay any operation.
const numberId = x => typeof x === "string" && /^[1-9][0-9]{0,15}$/.test(x);
const matchId = (value, expected) => Number.isSafeInteger(value) && value > 0 &&
  numberId(expected) && String(value) === expected;
const dateMs = x => {
  if (typeof x !== "string" || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(x)) return NaN;
  const ms = Date.parse(x);
  if (!Number.isFinite(ms) || new Date(ms).toISOString() !== x.replace("Z", ".000Z")) return NaN;
  return ms;
};
export function checkJobMetadata(identity, run, job, policy, nowMs) {
  try {
    if (!identity || !run || !job || !policy || !Number.isSafeInteger(nowMs) ||
        identity.runAttempt !== "1" || !numberId(identity.runId) || !numberId(identity.checkRunId) ||
        !numberId(policy.repositoryId) || identity.repositoryId !== policy.repositoryId || !numberId(policy.workflowId) ||
        typeof policy.workflowPath !== "string" ||
        !/^\.github\/workflows\/[A-Za-z0-9_.-]+\.ya?ml$/.test(policy.workflowPath) ||
        typeof policy.jobName !== "string" || !policy.jobName || policy.jobName.length > 100 ||
        typeof policy.sha !== "string" || !/^[a-f0-9]{40}$/.test(policy.sha) ||
        !Number.isSafeInteger(policy.maxAgeSeconds) || policy.maxAgeSeconds < 1 || policy.maxAgeSeconds > 600 ||
        !Array.isArray(policy.allowedEvents) || !policy.allowedEvents.length ||
        policy.allowedEvents.some(e => !["schedule", "workflow_dispatch"].includes(e))) return false;
    if (!matchId(run.id, identity.runId) || !matchId(job.run_id, identity.runId) ||
        !matchId(job.id, identity.checkRunId) ||
        !matchId(run.repository?.id, policy.repositoryId) || !matchId(run.workflow_id, policy.workflowId) ||
        run.run_attempt !== 1 || job.run_attempt !== 1 ||
        run.path !== policy.workflowPath || run.head_branch !== "main" ||
        run.head_sha !== policy.sha || job.head_sha !== policy.sha ||
        run.status !== "in_progress" || job.status !== "in_progress" || job.completed_at !== null ||
        job.name !== policy.jobName || identity.eventName !== run.event || !policy.allowedEvents.includes(run.event)) return false;
    const created = dateMs(run.created_at), started = dateMs(job.started_at);
    if (!Number.isFinite(created) || !Number.isFinite(started) || started < created ||
        created > nowMs + 30000 || started > nowMs + 30000 ||
        nowMs - created > policy.maxAgeSeconds * 1000) return false;
    return true;
  } catch { return false; }
}
