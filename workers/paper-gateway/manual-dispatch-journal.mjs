// Synthetic protected sender storage. No handler, network client or credential.
import { normalizeManualInputs, processingSlot, registeredManualWorkflow } from "./manual-dispatch.mjs";

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

// prepay must charge protected account limits, including the journal itself.
// deliver is a single-attempt transport supplied only by a future authorized
// dispatcher. Tests inject a recorder. No response failure causes redelivery.
export async function sendApprovedManualJob({ enabled = false, storage, policy, slotMs, clock, prepay, deliver } = {}) {
  if (enabled !== true) return "DISABLED";
  if (!registeredManualWorkflow(policy) || typeof clock !== "function" ||
      typeof prepay !== "function" || typeof deliver !== "function") return "INVALID";
  const inputs = normalizeManualInputs(policy.writerId, policy.approvedInputs);
  if (!inputs || !Number.isSafeInteger(slotMs)) return "INVALID";
  const { writerId, workflowId, sha } = policy;
  const request = { ref: "main", inputs };
  try {
    if (await prepay("DISPATCH_INTENT_INSERT") !== true) return "BUDGET_BLOCKED";
    const intended = clock();
    if (processingSlot(intended, intended) !== slotMs) return "SLOT_BLOCKED";
    const inserted = storage.transactionSync(() =>
      storage.sql.exec("INSERT INTO " + intent + " VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING RETURNING slot_ms",
        writerId, slotMs, workflowId, sha, JSON.stringify(inputs), intended).toArray());
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
    return { apiVersion: "2026-03-10", method: "POST", url: api + "/actions/workflows/" + row.workflow_id + "/dispatches",
      sourceSha: row.sha, slotMs: row.slot_ms, sentAtMs: row.sent_ms, receivedAtMs: row.received_ms,
      request: { ref: "main", inputs: JSON.parse(row.inputs) }, status: 200, response: replyFor(runId) };
  } catch { return null; }
}
