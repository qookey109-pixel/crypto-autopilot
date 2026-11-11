// Synthetic arithmetic only: never an account evidence or execution authority.
// A production boundary must authenticate a complete telemetry watermark and
// complete, immutable, account-wide reservations including all open claims.
// This module does not fetch usage, verify the source, claim budgets or spend.
const integer = n => Number.isSafeInteger(n) && n >= 0;
const keys = Object.freeze(["worker", "github", "provider", "r2a", "r2b", "bytes",
  "d1queries", "d1read", "d1write", "d1bytes", "doReq", "doGbMs", "doRead", "doWrite", "doBytes"]);
const ident = x => typeof x === "string" && /^[a-zA-Z0-9:._/-]{1,128}$/.test(x);

export function conservativeRemaining({ enabled = false, nowMs, observedAtMs, maxObservationAgeMs,
  maxDataLagMs, ledgerAsOfMs, completeCoverage, counters, reservations } = {}) {
  if (enabled !== true) return { status: "DISABLED" };
  try {
    if (!integer(nowMs) || !integer(observedAtMs) || !integer(ledgerAsOfMs) ||
        !integer(maxObservationAgeMs) || maxObservationAgeMs < 1 || maxObservationAgeMs > 60000 ||
        !integer(maxDataLagMs) || maxDataLagMs < 1 || maxDataLagMs > 2678400000 ||
        observedAtMs > nowMs || nowMs - observedAtMs > maxObservationAgeMs ||
        ledgerAsOfMs !== nowMs || completeCoverage !== true || !counters ||
        Object.keys(counters).length !== keys.length || !Array.isArray(reservations) ||
        reservations.length > 4096) return { status: "INVALID" };
    const ids = new Set();
    for (const reservation of reservations) {
      if (!reservation || !ident(reservation.id) || ids.has(reservation.id) ||
          !integer(reservation.reservedMs) || reservation.reservedMs > nowMs ||
          (reservation.closedMs !== null && (!integer(reservation.closedMs) ||
            reservation.closedMs < reservation.reservedMs || reservation.closedMs > nowMs)) ||
          !reservation.envelope || Object.keys(reservation.envelope).length !== keys.length ||
          keys.some(k => !integer(reservation.envelope[k]))) return { status: "INVALID" };
      ids.add(reservation.id);
    }
    const remaining = {};
    for (const k of keys) {
      const c = counters[k];
      if (!c || !integer(c.used) || !integer(c.cap) || !integer(c.margin) ||
          !integer(c.periodStartMs) || !integer(c.periodEndMs) ||
          !integer(c.measuredThroughMs) || c.periodStartMs > c.measuredThroughMs ||
          c.measuredThroughMs > observedAtMs || observedAtMs > nowMs ||
          nowMs >= c.periodEndMs || nowMs - c.measuredThroughMs > maxDataLagMs)
        return { status: "INVALID" };
      let total = c.used + c.margin;
      if (!integer(total)) return { status: "INVALID" };
      for (const reservation of reservations) {
        // A reservation spanning the watermark is charged in full, even if
        // some of its operations may already appear in measured usage.
        if (reservation.closedMs === null || reservation.closedMs >= c.measuredThroughMs) {
          total += reservation.envelope[k];
          if (!integer(total)) return { status: "INVALID" };
        }
      }
      if (total > c.cap) return { status: "BUDGET_BLOCKED" };
      remaining[k] = c.cap - total;
    }
    return { status: "READY_FOR_REVIEW", remaining };
  } catch { return { status: "INVALID" }; }
}
