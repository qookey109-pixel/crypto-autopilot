// Synthetic composition only. It is deliberately not a Worker fetch handler.
// The injected policy, clock, reserve, transport and database are not a
// production trust boundary. Never connect real credentials or bindings here.
import { readGithubKeys } from "./github-keys.mjs";
import { verifyGithubJob } from "./github-oidc.mjs";
import { readJobMetadata } from "./github-metadata-reader.mjs";
import { checkJobMetadata } from "./github-metadata.mjs";
import { claimJobSlot } from "./d1-job-claim.mjs";

export function processingSlot(now, after) {
  if (!Number.isSafeInteger(now) || !Number.isSafeInteger(after) || after < now) return null;
  const quarter = 15 * 60 * 1000, offset = 7 * 60 * 1000, day = 86400000;
  const slot = Math.floor((now - offset) / quarter) * quarter + offset;
  const afterSlot = Math.floor((after - offset) / quarter) * quarter + offset;
  if (!Number.isSafeInteger(slot) || slot < 0 || afterSlot !== slot ||
      after - slot > 600000 || Math.floor(slot / day) !== Math.floor(after / day)) return null;
  return slot;
}

export async function admitScheduledJob({ enabled = false, policy, token, githubToken, fetcher, db, clock, reserve } = {}) {
  if (enabled !== true) return { status: "DISABLED" };
  try {
    if (!policy || typeof clock !== "function" || typeof reserve !== "function") return { status: "INVALID" };
    const fixed = structuredClone(policy);
    if (typeof fixed.writerId !== "string" ||
        !/^[a-z0-9][a-z0-9:._/-]{0,127}$/.test(fixed.writerId)) return { status: "INVALID" };
    // Values are synthetic upper bounds. Real ceilings must be independently
    // measured, account-scoped, server-owned and prepaid before any access.
    // Three written rows is only a fixture floor for table plus two indexes;
    // it is not an upper bound or a substitute for real D1 calibration.
    const costs = fixed.admissionCosts;
    const minimum = { workerRequests: 1, githubRequests: 4, d1Queries: 1,
      d1RowsRead: 1, d1RowsWritten: 3, d1StorageBytes: 1 };
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
    if (!identity || identity.eventName !== "schedule") return { status: "IDENTITY_BLOCKED" };
    const metadata = await readJobMetadata({
      enabled: true, repository: fixed.repository, identity, token: githubToken, fetcher,
    });
    const after = clock();
    if (!metadata || metadata.main?.commit?.sha !== fixed.sha || !Number.isSafeInteger(after) || Math.floor(after / 1000) >= identity.expiresAt ||
        !checkJobMetadata(identity, metadata.run, metadata.job,
          { ...fixed, allowedEvents: ["schedule"] }, after)) return { status: "IDENTITY_BLOCKED" };
    // Processing time only; never claim to know the scheduler's nominal slot.
    const slot = processingSlot(now, after);
    if (slot === null) return { status: "SLOT_BLOCKED" };
    const slotId = "slot:" + slot;
    const status = await claimJobSlot(db, { repositoryId: identity.repositoryId, runId: identity.runId,
      attempt: "1", checkRunId: identity.checkRunId, writerId: fixed.writerId, slotId }, { enabled: true,
      limits: { rowsRead: costs.d1RowsRead, rowsWritten: costs.d1RowsWritten,
        maxDatabaseBytes: fixed.databaseBytesBefore + costs.d1StorageBytes } });
    if (status !== "CLAIMED") return { status };
    // A commit can succeed after identity or processing-window expiry.
    // Keep the consumed claim and require review; never release work.
    const finished = clock();
    if (!Number.isSafeInteger(finished) || finished < after || Math.floor(finished / 1000) >= identity.expiresAt ||
        processingSlot(now, finished) !== slot) return { status: "REVIEW_REQUIRED" };
    return { status, slotId };
  } catch { return { status: "REVIEW_REQUIRED" }; }
}
