// Preparation only. No route, binding, migration, or live execution is authorized.
// The caller must independently authenticate identity and supply protected policy,
// trusted time, fresh account-wide headroom, and a uniquely owned storage namespace.
// Incoming invocation and ledger operations need separate prepaid allowances.
const integer = x => Number.isSafeInteger(x) && x >= 0;
const metrics = Object.freeze(["worker", "github", "provider", "r2a", "r2b", "bytes", "d1queries", "d1read", "d1write", "d1bytes"]);
const identity = x => typeof x === "string" && /^[a-zA-Z0-9:._/-]{1,128}$/.test(x);
const schema = [
  "CREATE TABLE IF NOT EXISTS envelope_namespace (id INTEGER PRIMARY KEY CHECK (id = 1), scope TEXT NOT NULL)",
  "CREATE TABLE IF NOT EXISTS envelope_scope (scope TEXT PRIMARY KEY, policy_hash TEXT NOT NULL, policy_contract TEXT NOT NULL, " + metrics.map(k => k + " INTEGER NOT NULL").join(", ") + ")",
  "CREATE TABLE IF NOT EXISTS envelope_claim (scope TEXT NOT NULL, writer TEXT NOT NULL, slot TEXT NOT NULL, run TEXT NOT NULL, reserved_ms INTEGER NOT NULL, " + metrics.map(k => k + " INTEGER NOT NULL").join(", ") + ", PRIMARY KEY(scope,writer,slot), UNIQUE(scope,writer,run))",
  "CREATE TRIGGER IF NOT EXISTS envelope_claim_no_update BEFORE UPDATE ON envelope_claim BEGIN SELECT RAISE(ABORT, 'IMMUTABLE'); END",
  "CREATE TRIGGER IF NOT EXISTS envelope_claim_no_delete BEFORE DELETE ON envelope_claim BEGIN SELECT RAISE(ABORT, 'IMMUTABLE'); END",
];
export function prepareEnvelopeSchema(storage, enabled = false) {
  if (enabled !== true) return "DISABLED";
  try {
    storage.transactionSync(() => { for (const sql of schema) storage.sql.exec(sql); });
    return "PREPARED";
  } catch { return "REVIEW_REQUIRED"; }
}
export function reserveEnvelope(storage, { enabled = false, policy, claim, nowMs } = {}) {
  if (enabled !== true) return "DISABLED";
  if (!policy || !claim || !identity(policy.scope) ||
      !/^[a-f0-9]{64}$/.test(policy.policyHash || "") ||
      !identity(claim.writer) || !identity(claim.slot) || !identity(claim.run) ||
      !integer(nowMs) || !integer(policy.startsMs) || !integer(policy.endsMs) ||
      nowMs < policy.startsMs || nowMs >= policy.endsMs ||
      !policy.caps || !claim.cost ||
      metrics.some(k => !integer(policy.caps[k]) || !integer(claim.cost[k]) ||
        claim.cost[k] > policy.caps[k])) return "INVALID";
  try {
    const contract = JSON.stringify([policy.startsMs, policy.endsMs, ...metrics.map(k => policy.caps[k])]);
    return storage.transactionSync(() => {
      const sql = storage.sql;
      sql.exec("INSERT INTO envelope_namespace VALUES (1, ?) ON CONFLICT(id) DO NOTHING", policy.scope);
      const namespace = sql.exec("SELECT scope FROM envelope_namespace WHERE id = 1").toArray();
      if (namespace.length !== 1 || namespace[0].scope !== policy.scope) return "SCOPE_MISMATCH";
      sql.exec("INSERT INTO envelope_scope VALUES (?, ?, ?, " + metrics.map(() => "0").join(", ") + ") ON CONFLICT(scope) DO NOTHING",
        policy.scope, policy.policyHash, contract);
      const prior = sql.exec("SELECT policy_hash, policy_contract, " + metrics.join(", ") + " FROM envelope_scope WHERE scope = ?", policy.scope).toArray();
      if (prior.length !== 1 || (prior[0].policy_hash !== policy.policyHash || prior[0].policy_contract !== contract)) return "POLICY_MISMATCH";
      const duplicate = sql.exec("SELECT 1 FROM envelope_claim WHERE scope = ? AND writer = ? AND (slot = ? OR run = ?) LIMIT 1", policy.scope, claim.writer, claim.slot, claim.run).toArray();
      if (duplicate.length) return "DUPLICATE";
      const totals = metrics.map(k => prior[0][k] + claim.cost[k]);
      if (totals.some((v, i) => !integer(v) || v > policy.caps[metrics[i]])) return "BUDGET_BLOCKED";
      sql.exec("INSERT INTO envelope_claim VALUES (?, ?, ?, ?, ?, " + metrics.map(() => "?").join(", ") + ")", policy.scope, claim.writer, claim.slot, claim.run, nowMs, ...metrics.map(k => claim.cost[k]));
      sql.exec("UPDATE envelope_scope SET " + metrics.map(k => k + "=?").join(", ") + " WHERE scope=?",
        ...totals, policy.scope);
      return "RESERVED";
    });
  } catch { return "REVIEW_REQUIRED"; }
}

/** Synthetic snapshot; all claims remain charged and account coverage is unproven. */
export function snapshotEnvelopes(storage, { scope, nowMs, enabled = false } = {}) {
  if (enabled !== true) return { status: "DISABLED" };
  if (!identity(scope) || !integer(nowMs)) return { status: "INVALID" };
  try {
    return storage.transactionSync(() => {
      const sql = storage.sql;
      const ns = sql.exec("SELECT scope FROM envelope_namespace WHERE id=1").toArray();
      if (ns.length !== 1 || ns[0].scope !== scope) return { status: "SCOPE_MISMATCH" };
      const totals = sql.exec("SELECT " + metrics.join(", ") + " FROM envelope_scope WHERE scope=?", scope).toArray();
      if (totals.length !== 1) return { status: "REVIEW_REQUIRED" };
      const rows = sql.exec("SELECT rowid AS rid, reserved_ms, " + metrics.join(", ") +
        " FROM envelope_claim WHERE scope=? ORDER BY rowid LIMIT 4097", scope).toArray();
      if (rows.length > 4096) return { status: "REVIEW_REQUIRED" };
      const sums = Object.fromEntries(metrics.map(k => [k, 0]));
      const reservations = [];
      for (const row of rows) {
        if (!integer(row.rid) || row.rid < 1 || !integer(row.reserved_ms) || row.reserved_ms > nowMs ||
            metrics.some(k => !integer(row[k]))) return { status: "REVIEW_REQUIRED" };
        for (const k of metrics) { sums[k] += row[k]; if (!integer(sums[k])) return { status: "REVIEW_REQUIRED" }; }
        reservations.push({ id: String(row.rid), reservedMs: row.reserved_ms, closedMs: null,
          envelope: Object.fromEntries(metrics.map(k => [k, row[k]])) });
      }
      if (metrics.some(k => !integer(totals[0][k]) || totals[0][k] !== sums[k])) return { status: "REVIEW_REQUIRED" };
      return { status: "READY_FOR_REVIEW", ledgerAsOfMs: nowMs, reservations };
    });
  } catch { return { status: "REVIEW_REQUIRED" }; }
}

/** Synthetic ingress prepayment only; not a Worker handler or authority.
 * Policy, clock and attempt IDs must be independently protected in production.
 * The incoming invocation and the ledger's own operations are already underway;
 * they need a separate account-scoped allocation outside this function.
 */
export function createIngressReservation({ storage, policy, clock, nextId, admissionCosts, enabled = false } = {}) {
  if (enabled !== true) return async () => false;
  if (!storage || !policy || typeof clock !== "function" || typeof nextId !== "function" || !admissionCosts)
    throw new TypeError("invalid synthetic ingress configuration");
  const fixedPolicy = structuredClone(policy);
  const fixedCosts = structuredClone(admissionCosts);
  const fields = ["workerRequests", "githubRequests", "d1Queries", "d1RowsRead", "d1RowsWritten", "d1StorageBytes"];
  if (Object.keys(fixedCosts).length !== fields.length || fields.some(k => !integer(fixedCosts[k]) || fixedCosts[k] < 1))
    throw new TypeError("invalid synthetic ingress costs");
  return async actual => {
    try {
      if (!actual || Object.keys(actual).length !== fields.length || fields.some(k => actual[k] !== fixedCosts[k]))
        return false;
      const id = nextId();
      if (!identity(id)) return false;
      const cost = { worker: fixedCosts.workerRequests, github: fixedCosts.githubRequests,
        provider: 0, r2a: 0, r2b: 0, bytes: 0, d1queries: fixedCosts.d1Queries,
        d1read: fixedCosts.d1RowsRead, d1write: fixedCosts.d1RowsWritten, d1bytes: fixedCosts.d1StorageBytes };
      return reserveEnvelope(storage, { enabled: true, policy: fixedPolicy, nowMs: clock(),
        claim: { writer: "gateway-ingress", slot: id, run: id, cost } }) === "RESERVED";
    } catch { return false; }
  };
}
