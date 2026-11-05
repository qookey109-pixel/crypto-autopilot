// Synthetic composition only. It is deliberately not a Worker fetch handler.
// The injected policy, clock, reserve, transport and database are not a
// production trust boundary. Never connect real credentials or bindings here.
import { readGithubKeys } from "./github-keys.mjs";
import { verifyGithubJob } from "./github-oidc.mjs";
import { readJobMetadata } from "./github-metadata-reader.mjs";
import { checkJobMetadata } from "./github-metadata.mjs";
import { claimJobSlot } from "./d1-job-claim.mjs";

export async function admitScheduledJob({ policy, token, githubToken, fetcher, db, clock, reserve } = {}) {
  try {
    if (!policy || typeof clock !== "function" || typeof reserve !== "function") return { status: "INVALID" };
    const fixed = structuredClone(policy);
    if (typeof fixed.writerId !== "string" ||
        !/^[a-z0-9][a-z0-9:._/-]{0,127}$/.test(fixed.writerId)) return { status: "INVALID" };
    // Synthetic reservation: production must independently prepay the full
    // account-wide worst case, including claim and possible retries.
    if (await reserve({ githubReads: 3, d1Writes: 1 }) !== true) return { status: "BUDGET_BLOCKED" };
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
    if (!metadata || !Number.isSafeInteger(after) || Math.floor(after / 1000) >= identity.expiresAt ||
        !checkJobMetadata(identity, metadata.run, metadata.job,
          { ...fixed, allowedEvents: ["schedule"] }, after)) return { status: "IDENTITY_BLOCKED" };
    // Processing time only; never claim to know the scheduler's nominal slot.
    const quarter = 15 * 60 * 1000, offset = 7 * 60 * 1000;
    const slot = Math.floor((now - offset) / quarter) * quarter + offset;
    const afterSlot = Math.floor((after - offset) / quarter) * quarter + offset;
    if (!Number.isSafeInteger(slot) || slot < 0 || after < now || afterSlot !== slot)
      return { status: "SLOT_BLOCKED" };
    const slotId = "slot:" + slot;
    const status = await claimJobSlot(db, { repositoryId: identity.repositoryId, runId: identity.runId,
      attempt: "1", checkRunId: identity.checkRunId, writerId: fixed.writerId, slotId }, { enabled: true });
    if (status !== "CLAIMED") return { status };
    return { status, slotId };
  } catch { return { status: "REVIEW_REQUIRED" }; }
}
