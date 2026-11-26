import { parseUnique } from "./github-oidc.mjs";

// Prepared for a protected dispatcher. The job must never supply policy,
// approvedInputs or the dispatch receipt. Public policy reads use an injected transport.
const repository = "qookey109-pixel/crypto-autopilot";
const repositoryId = "1336841226";
const prefix = "crypto-autopilot:";
const coordinator = prefix + "live-paper-run-coordinator-v0-1";
const recovery = prefix + "live-paper-run-recovery-v0-1";
const jobs = new Map([
  [coordinator, { id: "361536775", name: "run-one-step" }],
  [recovery, { id: "361556331", name: "reconcile" }],
]);
export const isManualWriter = writer => jobs.has(writer);

export const validGitOid = value => typeof value === "string" && /^[a-f0-9]{40}$/.test(value);

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

export async function readPublicGithubJson(fetcher, url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);
  let reader;
  try {
    const response = await fetcher(url, {
      method: "GET", redirect: "manual", credentials: "omit", signal: controller.signal,
      headers: { Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28" },
    });
    if (response.status !== 200 || !response.body) return null;
    reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8", { fatal: true });
    let text = "", bytes = 0;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > 131072) return null;
      text += decoder.decode(value, { stream: true });
    }
    return parseUnique(text + decoder.decode());
  } catch { return null; }
  finally {
    clearTimeout(timer);
    controller.abort();
    if (reader) await reader.cancel().catch(() => {});
  }
}

export async function readCoordinatorInputApproval(fetcher, sha, path) {
  if (typeof fetcher !== "function" || !validGitOid(sha) || !normalizeManualInputs(coordinator, { input_path: path })) return null;
  const url = "https://raw.githubusercontent.com/" + repository + "/" + sha + "/config/live_paper_coordinator_input_registry_v0_1.json";
  const registry = await readPublicGithubJson(fetcher, url);
  if (!keysAre(registry, ["schema", "workflow_id", "approved_inputs"]) ||
      registry.schema !== "qookey-live-paper-coordinator-input-registry-v0.1" || registry.workflow_id !== jobs.get(coordinator).id ||
      !Array.isArray(registry.approved_inputs) || registry.approved_inputs.length > 64) return null;
  const entries = new Map();
  for (const entry of registry.approved_inputs) {
    if (!keysAre(entry, ["input_path", "blob_sha"]) || !validGitOid(entry.blob_sha) ||
        !normalizeManualInputs(coordinator, { input_path: entry.input_path }) ||
        entry.input_path.split("/").length > 12 || entries.has(entry.input_path)) return null;
    entries.set(entry.input_path, entry.blob_sha);
  }
  return entries.get(path) ?? null;
}

export function registeredManualWorkflow(policy) {
  if (!policy) return false;
  const writer = policy.writerId;
  const job = jobs.get(writer);
  if (!job || policy.repository !== repository || policy.repositoryId !== repositoryId ||
      policy.jobName !== job.name || policy.workflowId !== job.id) return false;
  const path = ".github/workflows/" + writer.slice(prefix.length) + ".yml";
  if (policy.workflowPath !== path || policy.workflowRef !== repository + "/" + path + "@refs/heads/main" ||
      policy.workflowSha !== policy.sha || typeof policy.sha !== "string" || !/^[a-f0-9]{40}$/.test(policy.sha)) return false;
  return true;
}

export function processingSlot(now, after) {
  if (!Number.isSafeInteger(now) || !Number.isSafeInteger(after) || after < now) return null;
  const quarter = 15 * 60 * 1000, offset = 7 * 60 * 1000, day = 86400000;
  const slot = Math.floor((now - offset) / quarter) * quarter + offset;
  const afterSlot = Math.floor((after - offset) / quarter) * quarter + offset;
  if (!Number.isSafeInteger(slot) || slot < 0 || afterSlot !== slot ||
      after - slot > 600000 || Math.floor(slot / day) !== Math.floor(after / day)) return null;
  return slot;
}

// Both the signed job and the run/job/main API metadata are verified by the
// caller. A dispatcher's recorded POST response links that exact run to inputs.
export function confirmedManualScope(policy, identity, createdAt, slot, now, receipt, approvedBlobSha) {
  const writer = policy.writerId;
  if (!registeredManualWorkflow(policy)) return null;
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
  if (writer === coordinator) {
    if (!validGitOid(receipt.inputBlobSha) || receipt.inputBlobSha !== approvedBlobSha ||
        (policy.inputBlobSha !== undefined && policy.inputBlobSha !== approvedBlobSha)) return null;
    return { sourceSha: policy.sha, inputs: approved, inputBlobSha: receipt.inputBlobSha };
  }
  return { sourceSha: policy.sha, inputs: approved };
}
