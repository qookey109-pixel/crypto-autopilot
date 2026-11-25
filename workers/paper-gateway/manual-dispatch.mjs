// Prepared for a protected dispatcher. The job must never supply policy,
// approvedInputs or the dispatch receipt. This module performs no I/O.
const repository = "qookey109-pixel/crypto-autopilot";
const repositoryId = "1336841226";
const prefix = "crypto-autopilot:";
const coordinator = prefix + "live-paper-run-coordinator-v0-1";
const recovery = prefix + "live-paper-run-recovery-v0-1";
const jobs = new Map([[coordinator, "run-one-step"], [recovery, "reconcile"]]);
export const isManualWriter = writer => jobs.has(writer);

function keysAre(value, required, optional = []) {
  return value !== null && typeof value === "object" && !Array.isArray(value) &&
    required.every(key => Object.hasOwn(value, key)) &&
    Object.keys(value).every(key => required.includes(key) || optional.includes(key));
}

export function normalizeManualInputs(writer, inputs) {
  if (writer === coordinator && keysAre(inputs, ["input_path"])) {
    const path = inputs.input_path;
    if (typeof path === "string" && path.length <= 384 &&
        /^research\/inputs\/live-paper\/(?:[A-Za-z0-9_-][A-Za-z0-9._-]*\/)*[A-Za-z0-9_-][A-Za-z0-9._-]*\.json$/.test(path)) {
      return { input_path: path };
    }
  }
  if (writer === recovery && keysAre(inputs, ["run_id"], ["repair_missing_result_seals"])) {
    if (typeof inputs.run_id !== "string" || !/^live-paper-run-v0-1-[a-f0-9]{64}$/.test(inputs.run_id)) return null;
    const repair = Object.hasOwn(inputs, "repair_missing_result_seals") ? inputs.repair_missing_result_seals : false;
    if (typeof repair === "boolean") return { run_id: inputs.run_id, repair_missing_result_seals: repair };
  }
  return null;
}

// Both the signed job and the run/job/main API metadata are verified by the
// caller. A dispatcher's recorded POST response links that exact run to inputs.
export function confirmedManualScope(policy, identity, createdAt, slot, now) {
  const writer = policy.writerId;
  if (!isManualWriter(writer) || policy.repository !== repository || policy.repositoryId !== repositoryId ||
      policy.jobName !== jobs.get(writer) || !/^[1-9]\d{0,15}$/.test(policy.workflowId)) return null;
  const path = ".github/workflows/" + writer.slice(prefix.length) + ".yml";
  if (policy.workflowPath !== path || policy.workflowRef !== repository + "/" + path + "@refs/heads/main" ||
      policy.workflowSha !== policy.sha || !/^[a-f0-9]{40}$/.test(policy.sha)) return null;
  const receipt = policy.manualDispatch;
  const root = "https://api.github.com/repos/" + repository;
  if (!receipt || receipt.apiVersion !== "2026-03-10" || receipt.method !== "POST" ||
      receipt.url !== root + "/actions/workflows/" + policy.workflowId + "/dispatches" ||
      receipt.sourceSha !== policy.sha || receipt.status !== 200 || receipt.slotMs !== slot ||
      !keysAre(receipt.request, ["ref", "inputs"]) || receipt.request.ref !== "main") return null;
  const reply = receipt.response;
  if (!Number.isSafeInteger(reply?.workflow_run_id) || String(reply.workflow_run_id) !== identity.runId ||
      reply.run_url !== root + "/actions/runs/" + identity.runId ||
      reply.html_url !== "https://github.com/" + repository + "/actions/runs/" + identity.runId) return null;
  const created = Date.parse(createdAt);
  const { sentAtMs, receivedAtMs } = receipt;
  if (![slot, now, sentAtMs, receivedAtMs, created].every(Number.isSafeInteger) ||
      sentAtMs < slot || receivedAtMs < sentAtMs || receivedAtMs > now ||
      created < Math.floor(sentAtMs / 1000) * 1000 || created > receivedAtMs) return null;
  const approved = normalizeManualInputs(writer, policy.approvedInputs);
  const sent = normalizeManualInputs(writer, receipt.request.inputs);
  if (!approved || !sent || JSON.stringify(approved) !== JSON.stringify(sent)) return null;
  return { sourceSha: policy.sha, inputs: approved };
}
