// Synthetic composition only. It is deliberately not a Worker fetch handler.
// The injected policy, clock, reserve, transport and database are not a
// production trust boundary. Never connect real credentials or bindings here.
import { readGithubKeys } from "./github-keys.mjs";
import { verifyGithubJob } from "./github-oidc.mjs";
import { readJobMetadata } from "./github-metadata-reader-v0-2.mjs";
import { checkJobMetadata } from "./github-metadata.mjs";
import { confirmedManualScope, processingSlot } from "./manual-dispatch.mjs";
export { processingSlot };
import { claimJobSlot } from "./d1-job-claim.mjs";


const repository = "qookey109-pixel/crypto-autopilot";
const repositoryId = "1336841226";
const scheduledWriters = new Map([
  ["crypto-autopilot:research-signal-layer-v0-2", {
    workflowId: "340924790", file: "research-signal-layer-v0-2.yml", job: "collect",
    minuteOfDay: 2 * 60 + 17, sundayOnly: false,
  }],
  ["crypto-autopilot:binance-usdm-detailed-training-v0-1", {
    workflowId: "340899183", file: "binance-usdm-detailed-training-v0-1.yml", job: "train",
    minuteOfDay: 4 * 60 + 37, sundayOnly: true,
  }],
]);

export function processingSlotForJob(policy, now, after, createdAt) {
  if (typeof policy?.writerId !== "string" || typeof policy.workflowRef !== "string") return null;
  // Preserve the generic synthetic Paper fixture. This path cannot select
  // a project writer, repository or project workflow reference.
  if (policy.repository !== repository && policy.repositoryId !== repositoryId &&
      !policy.writerId.startsWith("crypto-autopilot:") &&
      !policy.workflowRef.startsWith(repository + "/")) return processingSlot(now, after);

  const writer = scheduledWriters.get(policy.writerId);
  if (!writer || policy.repository !== repository || policy.repositoryId !== repositoryId ||
      policy.workflowId !== writer.workflowId || policy.jobName !== writer.job) return null;
  const path = ".github/workflows/" + writer.file;
  if (policy.workflowPath !== path || policy.workflowRef !== repository + "/" + path + "@refs/heads/main" ||
      policy.workflowSha !== policy.sha) return null;
  if (!Number.isSafeInteger(now) || !Number.isSafeInteger(after) || after < now || now < 0) return null;
  const dayStart = now - now % 86400000;
  if (writer.sundayOnly && new Date(dayStart).getUTCDay() !== 0) return null;
  const slot = dayStart + writer.minuteOfDay * 60000;
  // GitHub exposes creation time, not the intended cron occurrence. Admit
  // only work created and processed inside the same fresh window.
  const created = Date.parse(createdAt);
  return Number.isSafeInteger(created) && slot <= created && created <= now &&
    slot <= now && after - slot <= 600000 ? slot : null;
}

export function admitScheduledJob(options) {
  return admitJob("schedule", options);
}

export function admitManualJob(options) {
  return admitJob("workflow_dispatch", options);
}

async function admitJob(event, { enabled = false, policy, token, githubToken, fetcher, db, clock, reserve, readDispatch } = {}) {
  if (enabled !== true) return { status: "DISABLED" };
  try {
    if (!policy || typeof clock !== "function" || typeof reserve !== "function") return { status: "INVALID" };
    const fixed = structuredClone(policy);
    if (typeof fixed.writerId !== "string" ||
        !/^[a-z0-9][a-z0-9:._/-]{0,127}$/.test(fixed.writerId)) return { status: "INVALID" };
    // Values are synthetic upper bounds. Real ceilings must be independently
    // measured, account-scoped, server-owned and prepaid before any access.
    // Four written rows is a fixture floor for the table and three indexes;
    // it is not an upper bound or a substitute for real D1 calibration.
    const costs = fixed.admissionCosts;
    const minimum = { workerRequests: 1, githubRequests: 4, d1Queries: 1,
      d1RowsRead: 1, d1RowsWritten: 4, d1StorageBytes: 1 };
    if (!costs || typeof costs !== "object" || Array.isArray(costs) ||
        Object.keys(costs).length !== Object.keys(minimum).length ||
        Object.entries(minimum).some(([key, min]) =>
          !Number.isSafeInteger(costs[key]) || costs[key] < min)) return { status: "INVALID" };
    if (!Number.isSafeInteger(fixed.databaseBytesBefore) || fixed.databaseBytesBefore < 0 ||
        !Number.isSafeInteger(fixed.databaseBytesBefore + costs.d1StorageBytes)) return { status: "INVALID" };
    if (await reserve(Object.freeze({ ...costs })) !== true) return { status: "BUDGET_BLOCKED" };
    const now = clock();
    if (!Number.isSafeInteger(now)) return { status: "INVALID" };
    const identity = await verifyGithubJob(token, {
      enabled: true, policy: fixed, now: Math.floor(now / 1000),
      fetchKeys: () => readGithubKeys({ enabled: true, fetcher }),
    });
    if (!identity || identity.eventName !== event) return { status: "IDENTITY_BLOCKED" };
    const metadata = await readJobMetadata({
      enabled: true, repository: fixed.repository, identity, token: githubToken, fetcher,
    });
    const after = clock();
    if (!metadata || metadata.main?.commit?.sha !== fixed.sha || !Number.isSafeInteger(after) || Math.floor(after / 1000) >= identity.expiresAt ||
        !checkJobMetadata(identity, metadata.run, metadata.job,
          { ...fixed, allowedEvents: [event] }, after)) return { status: "IDENTITY_BLOCKED" };
    // Processing time only; never claim to know the scheduler's nominal slot.
    const manual = event === "workflow_dispatch";
    const slotAt = end => manual ? processingSlot(now, end) : processingSlotForJob(fixed, now, end, metadata.run.created_at);
    const slot = slotAt(after);
    if (slot === null) return { status: "SLOT_BLOCKED" };
    if (manual && typeof readDispatch !== "function") return { status: "DISPATCH_SCOPE_BLOCKED" };
    const receipt = manual ? await readDispatch(identity.runId) : null;
    const scope = manual ? confirmedManualScope(fixed, identity, metadata.run.created_at, slot, now, receipt) : null;
    if (manual && !scope) return { status: "DISPATCH_SCOPE_BLOCKED" };
    if (scope && JSON.stringify(scope).length > costs.d1StorageBytes) return { status: "BUDGET_BLOCKED" };
    const claimTime = manual ? clock() : after;
    if (!Number.isSafeInteger(claimTime) || claimTime < after || slotAt(claimTime) !== slot ||
        Math.floor(claimTime / 1000) >= identity.expiresAt) return { status: "SLOT_BLOCKED" };
    const slotId = "slot:" + slot;
    const status = await claimJobSlot(db, { repositoryId: identity.repositoryId, runId: identity.runId,
      attempt: "1", checkRunId: identity.checkRunId, writerId: fixed.writerId, slotId, operationScope: scope, observedAtMs: claimTime }, { enabled: true,
      limits: { rowsRead: costs.d1RowsRead, rowsWritten: costs.d1RowsWritten,
        maxDatabaseBytes: fixed.databaseBytesBefore + costs.d1StorageBytes } });
    if (status !== "CLAIMED") return { status };
    // A commit can succeed after identity or processing-window expiry.
    // Keep the consumed claim and require review; never release work.
    const finished = clock();
    if (!Number.isSafeInteger(finished) || finished < claimTime || Math.floor(finished / 1000) >= identity.expiresAt ||
        slotAt(finished) !== slot) return { status: "REVIEW_REQUIRED" };
    return manual ? { status, slotId, operationScope: scope } : { status, slotId };
  } catch { return { status: "REVIEW_REQUIRED" }; }
}
