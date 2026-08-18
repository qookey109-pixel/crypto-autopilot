from __future__ import annotations

import argparse
import json
from pathlib import Path


M1A = Path("research/receipts/2026-08-17-m1a-pionex.json")
BINANCE_2025 = Path("research/receipts/2026-08-18-binance-2025-r2-pilot.json")
FUNDING_SOURCE = Path("research/receipts/2026-08-18-binance-funding-source-proof.json")
FUNDING_COVERAGE = Path("research/receipts/2026-08-18-binance-funding-coverage.json")
FUNDING_AUTHORITY = Path("research/receipts/2026-08-18-binance-funding-materialization-authority.json")
FUNDING_AMENDMENT = Path("research/receipts/2026-08-18-binance-funding-materialization-authority-amendment.json")
FUNDING_CONTINUITY_REVIEW = Path("research/receipts/2026-08-19-binance-funding-interior-continuity-review.json")
HISTORICAL_UNIVERSE = Path("research/receipts/2026-08-18-historical-universe-long-horizon-review.json")
PROJECT_STATUS = Path("PROJECT_STATUS.md")


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected object authority: {path}")
    return payload


def require_pass(payload: dict[str, object], path: Path) -> None:
    if payload.get("status") != "PASS":
        raise RuntimeError(f"authority is not PASS: {path}")


def normalize_binance_symbol(pionex_symbol: str) -> str:
    suffix = "_USDT_PERP"
    if not pionex_symbol.endswith(suffix):
        raise RuntimeError(f"unexpected Pionex candidate symbol: {pionex_symbol}")
    return pionex_symbol[: -len(suffix)] + "USDT"


def pipeline_item(name: str, detail: str, status: str) -> dict[str, str]:
    return {"name": name, "detail": detail, "status": status}


def gate(name: str, detail: str, status: str, tone: str, critical: bool) -> dict[str, object]:
    return {
        "name": name,
        "detail": detail,
        "status": status,
        "tone": tone,
        "critical": critical,
    }


def build_snapshot() -> dict[str, object]:
    m1a = load_json(M1A)
    binance_2025 = load_json(BINANCE_2025)
    funding_source = load_json(FUNDING_SOURCE)
    funding_coverage = load_json(FUNDING_COVERAGE)
    funding_authority = load_json(FUNDING_AUTHORITY)
    funding_amendment = load_json(FUNDING_AMENDMENT)
    continuity_review = load_json(FUNDING_CONTINUITY_REVIEW)
    universe_review = load_json(HISTORICAL_UNIVERSE)
    status_text = PROJECT_STATUS.read_text(encoding="utf-8")

    for payload, path in (
        (binance_2025, BINANCE_2025),
        (funding_source, FUNDING_SOURCE),
        (funding_coverage, FUNDING_COVERAGE),
        (funding_authority, FUNDING_AUTHORITY),
        (funding_amendment, FUNDING_AMENDMENT),
        (continuity_review, FUNDING_CONTINUITY_REVIEW),
        (universe_review, HISTORICAL_UNIVERSE),
    ):
        require_pass(payload, path)

    audit = m1a.get("audit") or {}
    if not isinstance(audit, dict) or audit.get("pass") is not True:
        raise RuntimeError("Pionex M1A authority is not PASS")
    selected = m1a.get("selected_universe") or []
    if not isinstance(selected, list) or len(selected) != 15:
        raise RuntimeError("expected frozen 15-symbol Pionex candidate universe")

    scan = funding_coverage.get("scan") or {}
    boundaries = funding_coverage.get("symbol_boundaries") or {}
    if not isinstance(scan, dict) or not isinstance(boundaries, dict):
        raise RuntimeError("Funding Coverage authority shape changed")
    if scan.get("candidate_count") != 15 or scan.get("monthly_available_checks") != 1010:
        raise RuntimeError("Funding Coverage authority counts changed")

    authorized_scope = funding_authority.get("authorized_scope") or {}
    authorized_actions = funding_authority.get("authorized_actions") or {}
    if not isinstance(authorized_scope, dict) or not isinstance(authorized_actions, dict):
        raise RuntimeError("Funding materialization authority shape changed")
    funding_storage_scope_authorized = (
        authorized_actions.get("funding_materialization_authorized") is True
        and authorized_actions.get("r2_writes_authorized") is True
    )

    checksum_bound = "checksum" in json.dumps(funding_amendment, sort_keys=True).lower()
    if not checksum_bound:
        raise RuntimeError("Funding authority amendment no longer binds source checksums")

    if continuity_review.get("review_outcome") != "SCOPE_REDUCTION_REQUIRED":
        raise RuntimeError("Funding continuity review outcome changed")
    materialization_effect = continuity_review.get("v0_1_materialization_effect") or {}
    scope_change = continuity_review.get("required_scope_change") or {}
    observed_gap = continuity_review.get("observed_gap") or {}
    if not isinstance(materialization_effect, dict) or not isinstance(scope_change, dict) or not isinstance(observed_gap, dict):
        raise RuntimeError("Funding continuity review shape changed")
    if materialization_effect.get("v0_1_write_execution_must_remain_blocked") is not True:
        raise RuntimeError("Funding V0.1 is no longer explicitly blocked by continuity review")
    if scope_change.get("remaining_expected_source_months") != 1003:
        raise RuntimeError("Funding V0.2 planning source-month target changed")
    if scope_change.get("remaining_expected_annual_canonical_objects") != 94:
        raise RuntimeError("Funding V0.2 annual-object target changed")

    funding_materialization_ready = False
    funding_materialization_state = "SCOPE_REDUCTION_REQUIRED"

    equivalence_pending = "PIONEX-BINANCE EQUIVALENCE GATE PENDING SOURCE PUBLICATION" in status_text
    equivalence_status = "PENDING" if equivalence_pending else "NOT_READY"

    universe_status = "NOT_READY"
    review_text = json.dumps(universe_review, sort_keys=True)
    if "NOT_READY" not in review_text:
        raise RuntimeError("Historical Universe review no longer declares membership NOT_READY")

    candidate_symbols: list[str] = []
    for row in selected:
        if not isinstance(row, dict):
            raise RuntimeError("invalid Pionex selected_universe row")
        candidate_symbols.append(normalize_binance_symbol(str(row["symbol"])))
    if set(candidate_symbols) != set(boundaries):
        raise RuntimeError("Pionex candidate universe and Funding boundary universe differ")

    gap_symbol = str(observed_gap.get("symbol") or "")
    markets: list[dict[str, object]] = []
    for symbol in candidate_symbols:
        boundary = boundaries[symbol]
        if not isinstance(boundary, dict):
            raise RuntimeError(f"invalid Funding boundary row: {symbol}")
        funding_status = "REVIEW_REQUIRED" if symbol == gap_symbol else "PASS"
        row_status = "REVIEW_REQUIRED" if symbol == gap_symbol else "READY"
        markets.append(
            {
                "symbol": symbol,
                "trade": "PASS",
                "mark": "PASS",
                "funding": funding_status,
                "provider": "BINANCE USD-M",
                "status": row_status,
                "fundingFirstPeriod": boundary.get("first_available_period"),
                "fundingLastPeriod": boundary.get("last_available_period"),
                "fundingFirstUtc": boundary.get("earliest_funding_time_utc"),
                "fundingLastUtc": boundary.get("latest_funding_time_utc"),
                "fundingAvailableMonths": boundary.get("available_months"),
                "pionexSymbol": boundary.get("pionex_symbol"),
                "nativeToExecutionExchange": False,
                "fundingContinuityReview": (
                    {
                        "state": "SCOPE_REDUCTION_REQUIRED",
                        "deferredYear": int(scope_change["deferred_year"]),
                        "gapPeriod": observed_gap.get("period"),
                        "gapExpectedSlotUtc": observed_gap.get("expected_cadence_slot_between_observed_rows_utc"),
                    }
                    if symbol == gap_symbol
                    else None
                ),
            }
        )

    return {
        "schema": "qookey-dashboard-authority-snapshot-v0.1",
        "authority": False,
        "snapshotType": "NORMALIZED_VIEW_OF_FROZEN_REPOSITORY_AUTHORITIES",
        "snapshotLabel": "Repository authority snapshot",
        "project": {
            "name": "Qookey Crypto Autopilot",
            "mode": "PAPER-ONLY",
            "marketCount": len(candidate_symbols),
            "fundingMonthsObserved": int(scan["monthly_available_checks"]),
            "tradePlanAuthorized": False,
            "liveTradingAuthorized": False,
            "fundingStorageScopeAuthorized": funding_storage_scope_authorized,
            "fundingMaterializationReady": funding_materialization_ready,
            "fundingMaterializationState": funding_materialization_state,
            "fundingV0_1CanonicalScopeSha256": authorized_scope.get("canonical_scope_sha256"),
            "fundingV0_2PlannedSourceMonths": int(scope_change["remaining_expected_source_months"]),
            "fundingV0_2PlannedAnnualObjects": int(scope_change["remaining_expected_annual_canonical_objects"]),
            "fundingV0_2PlannedR2Identities": int(scope_change["remaining_expected_total_r2_object_identities"]),
        },
        "pipeline": [
            pipeline_item("Pionex M1A Dataset", "15-symbol / 15M / 60M / 4H frozen evidence", "PASS"),
            pipeline_item("Binance 2025 R2 Pilot", "Provider-separated Trade-Kline materialization authority", "PASS"),
            pipeline_item("Funding Source Proof", "Checksum / schema / cadence source semantics", "PASS"),
            pipeline_item("Funding Coverage", f"{scan['monthly_available_checks']:,} observed symbol-months across 15 symbols", "PASS"),
            pipeline_item("Funding V0.1 Scope Authority", "Exact 1,010-month storage scope was authorized and checksum-set bound", "AUTHORIZED"),
            pipeline_item("Funding Materialization Execution", "Full interior preflight found HYPEUSDT 2026-06 cadence discontinuity; V0.2 scope reduction required", funding_materialization_state),
            pipeline_item("Pionex ↔ Binance Equivalence", "Frozen 45-pair source gate", equivalence_status),
            pipeline_item("Historical Universe Membership", "Long-horizon review PASS; membership evidence still required", universe_status),
        ],
        "gates": [
            gate("R2 Budget", "Observed historical-data budget authorities remain PASS.", "PASS", "pass", False),
            gate("Provider Equivalence", "Source switch remains blocked until the frozen Pionex ↔ Binance gate resolves.", equivalence_status, "pending", True),
            gate("Historical Universe", "Review PASS is not membership authority.", universe_status, "pending", True),
            gate("Funding Materialization", "V0.1 execution is blocked. HYPEUSDT 2026 is deferred and V0.2 exact scope must be re-frozen before writes.", "NOT_READY", "pending", True),
            gate("Paper Broker", "Production-grade lifecycle and reconciliation are not yet authority-complete.", "NOT_READY", "pending", True),
            gate("Live Trading", "No real-money order or private execution route is authorized.", "NOT_AUTHORIZED", "blocked", True),
        ],
        "markets": markets,
        "sourceAuthorities": [
            str(M1A),
            str(BINANCE_2025),
            str(FUNDING_SOURCE),
            str(FUNDING_COVERAGE),
            str(FUNDING_AUTHORITY),
            str(FUNDING_AMENDMENT),
            str(FUNDING_CONTINUITY_REVIEW),
            str(HISTORICAL_UNIVERSE),
            str(PROJECT_STATUS),
        ],
        "securityBoundary": {
            "containsSecrets": False,
            "containsPrivateExchangeResponses": False,
            "authorizesSourceSwitch": False,
            "authorizesPionexNativeRelabeling": False,
            "authorizesTradePlans": False,
            "authorizesLiveTrading": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/dashboard/dashboard.json")
    args = parser.parse_args()
    snapshot = build_snapshot()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PASS",
                "stage": "DASHBOARD_D2_AUTHORITY_SNAPSHOT_PASS",
                "market_count": snapshot["project"]["marketCount"],
                "funding_months_observed": snapshot["project"]["fundingMonthsObserved"],
                "funding_materialization_state": snapshot["project"]["fundingMaterializationState"],
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
