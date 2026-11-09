// Preparation only. No route, binding, migration, or live execution is authorized.
// The caller must independently authenticate identity and supply protected policy,
// trusted time, fresh account-wide headroom, and a uniquely owned storage namespace.
// Incoming invocation and ledger operations need separate prepaid allowances.
const integer = x => Number.isSafeInteger(x) && x >= 0;
const metrics = ["r2a", "r2b", "bytes", "provider", "d1read", "d1write"];
const identity = x => typeof x === "string" && /^[a-zA-Z0-9:._/-]{1,128}$/.test(x);
const schema = [
  "CREATE TABLE IF NOT EXISTS envelope_scope (scope TEXT PRIMARY KEY, policy_hash TEXT NOT NULL, r2a INTEGER NOT NULL, r2b INTEGER NOT NULL, bytes INTEGER NOT NULL, provider INTEGER NOT NULL, d1read INTEGER NOT NULL, d1write INTEGER NOT NULL)",
  "CREATE TABLE IF NOT EXISTS envelope_claim (scope TEXT NOT NULL, writer TEXT NOT NULL, slot TEXT NOT NULL, run TEXT NOT NULL, PRIMARY KEY(scope,writer,slot), UNIQUE(scope,writer,run))",
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
    return storage.transactionSync(() => {
      const sql = storage.sql;
      sql.exec("INSERT INTO envelope_scope VALUES (?, ?, 0, 0, 0, 0, 0, 0) ON CONFLICT(scope) DO NOTHING",
        policy.scope, policy.policyHash);
      const prior = sql.exec("SELECT policy_hash, r2a, r2b, bytes, provider, d1read, d1write FROM envelope_scope WHERE scope = ?", policy.scope).toArray();
      if (prior.length !== 1 || prior[0].policy_hash !== policy.policyHash) return "POLICY_MISMATCH";
      const totals = metrics.map(k => prior[0][k] + claim.cost[k]);
      if (totals.some((v, i) => !integer(v) || v > policy.caps[metrics[i]])) return "BUDGET_BLOCKED";
      const duplicate = sql.exec("SELECT 1 FROM envelope_claim WHERE scope = ? AND writer = ? AND (slot = ? OR run = ?) LIMIT 1", policy.scope, claim.writer, claim.slot, claim.run).toArray();
      if (duplicate.length) return "DUPLICATE";
      sql.exec("INSERT INTO envelope_claim VALUES (?, ?, ?, ?)", policy.scope, claim.writer, claim.slot, claim.run);
      sql.exec("UPDATE envelope_scope SET r2a=?, r2b=?, bytes=?, provider=?, d1read=?, d1write=? WHERE scope=?",
        ...totals, policy.scope);
      return "RESERVED";
    });
  } catch { return "REVIEW_REQUIRED"; }
}
