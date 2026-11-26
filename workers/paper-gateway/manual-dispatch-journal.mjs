// Synthetic protected sender storage. No handler, network client or credential.
import { normalizeManualInputs, processingSlot, registeredManualWorkflow, validGitOid } from "./manual-dispatch.mjs";

import { parseUnique } from "./github-oidc.mjs";

const api = "https://api.github.com/repos/qookey109-pixel/crypto-autopilot";
const html = "https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/";
const intent = "paper_dispatch_intent_v1";
const result = "paper_dispatch_result_v1";

export function prepareDispatchJournal(storage, enabled = false) {
  if (enabled !== true) return "DISABLED";
  storage.transactionSync(() => {
    storage.sql.exec("CREATE TABLE IF NOT EXISTS " + intent + " (writer TEXT NOT NULL, slot_ms INTEGER NOT NULL, " +
      "workflow_id TEXT NOT NULL, sha TEXT NOT NULL, inputs TEXT NOT NULL, intent_ms INTEGER NOT NULL, PRIMARY KEY(writer, slot_ms))");
    storage.sql.exec("CREATE TABLE IF NOT EXISTS " + result + " (run_id TEXT PRIMARY KEY NOT NULL, writer TEXT NOT NULL, " +
      "slot_ms INTEGER NOT NULL, sent_ms INTEGER NOT NULL, received_ms INTEGER NOT NULL, UNIQUE(writer, slot_ms))");
    for (const table of [intent, result]) {
      for (const operation of ["UPDATE", "DELETE"]) {
        storage.sql.exec("CREATE TRIGGER IF NOT EXISTS " + table + "_no_" + operation + " BEFORE " + operation +
          " ON " + table + " BEGIN SELECT RAISE(ABORT, 'IMMUTABLE'); END");
      }
      const collision = "writer=NEW.writer AND slot_ms=NEW.slot_ms" + (table === result ? " OR run_id=NEW.run_id" : "");
      storage.sql.exec("CREATE TRIGGER IF NOT EXISTS " + table + "_no_replace BEFORE INSERT ON " + table +
        " WHEN EXISTS (SELECT 1 FROM " + table + " WHERE " + collision + ") BEGIN SELECT RAISE(IGNORE); END");
    }
  });
  return "PREPARED";
}

function replyFor(id) {
  return { workflow_run_id: Number(id), run_url: api + "/actions/runs/" + id, html_url: html + id };
}

// Inputs are resolved against immutable Git objects. The sender supplies the transport;
// no URL from a response is followed and no blob payload is needed.
async function readGitObject(fetcher, path) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);
  let reader;
  try {
    const response = await fetcher(api + "/git/" + path, {
      method: "GET", redirect: "manual", signal: controller.signal,
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
  } finally {
    clearTimeout(timer);
    controller.abort();
    if (reader) await reader.cancel().catch(() => {});
  }
}

async function verifyInputBlob({ fetcher, prepay, sha, path, expected, slotMs, clock }) {
  const parts = path.split("/");
  if (typeof fetcher !== "function" || !validGitOid(expected) || parts.length > 12) return "INPUT_BLOCKED";
  let previous = slotMs;
  async function allowRead() {
    const now = clock();
    if (processingSlot(previous, now) !== slotMs) return "SLOT_BLOCKED";
    previous = now;
    return await prepay("GITHUB_INPUT_METADATA_GET") === true ? "READY" : "BUDGET_BLOCKED";
  }
  const start = await allowRead();
  if (start !== "READY") return start;
  const commit = await readGitObject(fetcher, "commits/" + sha);
  if (commit?.sha !== sha || !validGitOid(commit.tree?.sha)) return "INPUT_BLOCKED";
  let treeSha = commit.tree.sha;
  for (const [index, name] of parts.entries()) {
    const permitted = await allowRead();
    if (permitted !== "READY") return permitted;
    const tree = await readGitObject(fetcher, "trees/" + treeSha);
    if (tree?.sha !== treeSha || tree.truncated !== false || !Array.isArray(tree.tree)) return "INPUT_BLOCKED";
    const matches = tree.tree.filter(entry => entry?.path === name);
    if (matches.length !== 1 || !validGitOid(matches[0].sha)) return "INPUT_BLOCKED";
    const entry = matches[0];
    if (index === parts.length - 1) {
      if (entry.type !== "blob" || !["100644", "100755"].includes(entry.mode) || entry.sha !== expected ||
          !Number.isSafeInteger(entry.size) || entry.size < 1) return "INPUT_BLOCKED";
      return "VERIFIED";
    }
    if (entry.type !== "tree" || entry.mode !== "040000") return "INPUT_BLOCKED";
    treeSha = entry.sha;
  }
  return "INPUT_BLOCKED";
}

// prepay must charge protected account limits, including the journal itself.
// deliver is a single-attempt transport supplied only by a future authorized
// dispatcher. Tests inject a recorder. No response failure causes redelivery.
export async function sendApprovedManualJob({ enabled = false, storage, policy, slotMs, clock, prepay, deliver, fetcher } = {}) {
  if (enabled !== true) return "DISABLED";
  if (!registeredManualWorkflow(policy) || typeof clock !== "function" ||
      typeof prepay !== "function" || typeof deliver !== "function") return "INVALID";
  const inputs = normalizeManualInputs(policy.writerId, policy.approvedInputs);
  if (!inputs || !Number.isSafeInteger(slotMs)) return "INVALID";
  const { writerId, workflowId, sha } = policy;
  const request = { ref: "main", inputs };
  const inputBlobSha = policy.inputBlobSha;
  try {
    let journalInputs = inputs;
    if (Object.hasOwn(inputs, "input_path")) {
      const checked = await verifyInputBlob({ fetcher, prepay, sha, path: inputs.input_path, expected: inputBlobSha, slotMs, clock });
      if (checked !== "VERIFIED") return checked;
      journalInputs = { version: 2, inputs, inputBlobSha };
    }
    if (await prepay("DISPATCH_INTENT_INSERT") !== true) return "BUDGET_BLOCKED";
    const intended = clock();
    if (processingSlot(intended, intended) !== slotMs) return "SLOT_BLOCKED";
    const inserted = storage.transactionSync(() =>
      storage.sql.exec("INSERT INTO " + intent + " VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING RETURNING slot_ms",
        writerId, slotMs, workflowId, sha, JSON.stringify(journalInputs), intended).toArray());
    if (inserted.length !== 1) return "ALREADY_ATTEMPTED";
    if (await prepay("GITHUB_DISPATCH_POST") !== true) return "BUDGET_BLOCKED";
    const sent = clock();
    if (processingSlot(intended, sent) !== slotMs) return "SLOT_BLOCKED";
    const response = await deliver({ method: "POST", apiVersion: "2026-03-10",
      url: api + "/actions/workflows/" + workflowId + "/dispatches", request });
    const received = clock();
    const id = response?.body?.workflow_run_id;
    if (!Number.isSafeInteger(id) || id < 1 || response.status !== 200 ||
        !Number.isSafeInteger(received) || received < sent) return "REVIEW_REQUIRED";
    const expected = replyFor(id);
    if (response.body.run_url !== expected.run_url || response.body.html_url !== expected.html_url) return "REVIEW_REQUIRED";
    if (await prepay("DISPATCH_RESULT_INSERT") !== true) return "REVIEW_REQUIRED";
    const saved = storage.transactionSync(() =>
      storage.sql.exec("INSERT INTO " + result + " VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING RETURNING run_id",
        String(id), writerId, slotMs, sent, received).toArray());
    if (saved.length !== 1 || processingSlot(sent, received) !== slotMs) return "REVIEW_REQUIRED";
    return "RECORDED";
  } catch { return "REVIEW_REQUIRED"; }
}

export async function readConfirmedDispatch({ enabled = false, storage, runId, prepay } = {}) {
  if (enabled !== true || typeof prepay !== "function" ||
      typeof runId !== "string" || !/^[1-9][0-9]{0,15}$/.test(runId) || !Number.isSafeInteger(Number(runId))) return null;
  try {
    if (await prepay("DISPATCH_RECEIPT_LOOKUP") !== true) return null;
    const rows = storage.sql.exec("SELECT i.*, r.sent_ms, r.received_ms FROM " + result + " r JOIN " + intent +
      " i ON i.writer=r.writer AND i.slot_ms=r.slot_ms WHERE r.run_id=?", runId).toArray();
    if (rows.length !== 1) return null;
    const row = rows[0];
    const stored = JSON.parse(row.inputs);
    const coordinator = row.workflow_id === "361536775";
    if (coordinator && (stored?.version !== 2 || !validGitOid(stored.inputBlobSha))) return null;
    const inputs = normalizeManualInputs(row.writer, coordinator ? stored.inputs : stored);
    if (!inputs) return null;
    return { ...(coordinator ? { inputBlobSha: stored.inputBlobSha } : {}), apiVersion: "2026-03-10", method: "POST", url: api + "/actions/workflows/" + row.workflow_id + "/dispatches",
      sourceSha: row.sha, slotMs: row.slot_ms, sentAtMs: row.sent_ms, receivedAtMs: row.received_ms,
      request: { ref: "main", inputs }, status: 200, response: replyFor(runId) };
  } catch { return null; }
}
