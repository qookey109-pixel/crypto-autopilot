from __future__ import annotations

import argparse
import json
from pathlib import Path


M1A = Path("research/receipts/2026-08-17-m1a-pionex.json")
BINANCE_2025 = Path("research/receipts/2026-08-18-binance-2025-r2-pilot.json")
FUNDING_SOURCE = Path("research/receipts/2026-08-18-binance-funding-source-proof.json")
FUNDING_COVERAGE = Path("research/receipts/2026-08-18-binance-funding-coverage.json")
FUNDING_CONTINUITY_REVIEW = Path("research/receipts/2026-08-19-binance-funding-interior-continuity-review.json")
FUNDING_AUTHORITY_V0_2 = Path(
    "research/receipts/2026-08-19-binance-funding-materialization-authority-v0-2.json"
)
HISTORICAL_UNIVERSE = Path("research/receipts/2026-08-18-historical-universe-long-horizon-review.json")
PROJECT_STATUS = Path("PROJECT_STATUS.md")

EXPECTED_V0_2_SCOPE_SHA = "1e0ff54daeec8e5e47376fedb631c663687dd6fb6a4c297d269c33acdf99ad58"
EXPECTED_V0_2_CHECKSUM_SHA = "881c14d3b3c780b8a0d56ca2f7fd57d2abff310fcd7cb4b13dc01f506b9b64f3"


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
    continuity_review = load_json(FUNDING_CONTINUITY_REVIEW)
    funding_v0_2 = load_json(FUNDING_AUTHORITY_V0_2)
    universe_review = load_json(HISTORICAL_UNIVERSE)
    status_text = PROJECT_STATUS.read_text(encoding="utf-8")

    for payload, path in (
        (binance_2025, BINANCE_2025),
        (funding_source, FUNDING_SOURCE),
        (funding_coverage, FUNDING_COVERAGE),
        (continuity_review, FUNDING_CONTINUITY_REVIEW),
        (funding_v0_2, FUNDING_AUTHORITY_V0_2),
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

    if continuity_review.get("review_outcome") != "SCOPE_REDUCTION_REQUIRED":
        raise RuntimeError("Funding continuity review outcome changed")
    observed_gap = continuity_review.get("observed_gap") or {}
    if not isinstance(observed_gap, dict) or observed_gap.get("symbol") != "HYPEUSDT":
        raise RuntimeError("Funding continuity gap identity changed")

    if funding_v0_2.get("stage") != "BINANCE_FUNDING_R2_MATERIALIZATION_V0_2_AUTHORIZED":
        raise RuntimeError("Funding V0.2 authority stage changed")
    if funding_v0_2.get("authority_type") != "STORAGE_MATERIALIZATION_ONLY":
        raise RuntimeError("Funding V0.2 authority type changed")
    authorized_scope = funding_v0_2.get("authorized_scope") or {}
    authorized_actions = funding_v0_2.get("authorized_actions") or {}
    blocked_actions = funding_v0_2.get("explicitly_not_authorized") or {}
    deferred_scope = funding_v0_2.get("deferred_scope") or {}
    if not all(
        isinstance(value, dict)
        for value in (authorized_scope, authorized_actions, blocked_actions, deferred_scope)
    ):
        raise RuntimeError("Funding V0.2 authority shape changed")

    if authorized_scope.get("canonical_scope_sha256") != EXPECTED_V0_2_SCOPE_SHA:
        raise RuntimeError("Funding V0.2 scope SHA changed")
    if authorized_scope.get("source_checksum_set_sha256") != EXPECTED_V0_2_CHECKSUM_SHA:
        raise RuntimeError("Funding V0.2 checksum-set SHA changed")
    if authorized_scope.get("source_archive_count") != 1003:
        raise RuntimeError("Funding V0.2 source archive count changed")
    if authorized_scope.get("annual_canonical_objects") != 94:
        raise RuntimeError("Funding V0.2 annual object count changed")
    if authorized_scope.get("planned_total_r2_object_identities") != 192:
        raise RuntimeError("Funding V0.2 R2 identity count changed")
    if authorized_actions.get("funding_materialization_authorized") is not True:
        raise RuntimeError("Funding V0.2 storage materialization authority missing")
    if authorized_actions.get("r2_writes_authorized") is not True:
        raise RuntimeError("Funding V0.2 exact storage write authority missing")
    if blocked_actions.get("live_trading_authorized") is not False:
        raise RuntimeError("live trading boundary changed")
    if blocked_actions.get("source_switch_authorized") is not False:
        raise RuntimeError("source switch boundary changed")
    if deferred_scope.get("symbol") != "HYPEUSDT" or deferred_scope.get("year") != 2026:
        raise RuntimeError("Funding deferred scope changed")

    equivalence_pending = "PIONEX-BINANCE EQUIVALENCE GATE PENDING SOURCE PUBLICATION" in status_text
    equivalence_status = "PENDING" if equivalence_pending else "NOT_READY"

    universe_text = json.dumps(universe_review, sort_keys=True)
    if "NOT_READY" not in universe_text:
        raise RuntimeError("Historical Universe review no longer declares membership NOT_READY")

    candidate_symbols: list[str] = []
    for row in selected:
        if not isinstance(row, dict):
            raise RuntimeError("invalid Pionex selected_universe row")
        candidate_symbols.append(normalize_binance_symbol(str(row["symbol"])))
    if set(candidate_symbols) != set(boundaries):
        raise RuntimeError("Pionex candidate universe and Funding boundary universe differ")

    markets: list[dict[str, object]] = []
    for symbol in candidate_symbols:
        boundary = boundaries[symbol]
        if not isinstance(boundary, dict):
            raise RuntimeError(f"invalid Funding boundary row: {symbol}")
        is_hype = symbol == "HYPEUSDT"
        markets.append(
            {
                "symbol": symbol,
                "trade": "PASS",
                "mark": "PASS",
                "funding": "REVIEW_REQUIRED" if is_hype else "PASS",
                "provider": "BINANCE USD-M",
                "status": "REVIEW_REQUIRED" if is_hype else "READY",
                "fundingFirstPeriod": boundary.get("first_available_period"),
                "fundingLastPeriod": boundary.get("last_available_period"),
                "fundingFirstUtc": boundary.get("earliest_funding_time_utc"),
                "fundingLastUtc": boundary.get("latest_funding_time_utc"),
                "fundingAvailableMonths": boundary.get("available_months"),
                "pionexSymbol": boundary.get("pionex_symbol"),
                "nativeToExecutionExchange": False,
                "fundingContinuityReview": (
                    {
                        "state": "DEFERRED_2026",
                        "deferredYear": 2026,
                        "gapPeriod": observed_gap.get("period"),
                        "gapExpectedSlotUtc": observed_gap.get(
                            "expected_cadence_slot_between_observed_rows_utc"
                        ),
                    }
                    if is_hype
                    else None
                ),
            }
        )

    return {
        "schema": "qookey-dashboard-authority-snapshot-v0.2",
        "authority": False,
        "locale": "zh-Hant-TW",
        "snapshotType": "NORMALIZED_VIEW_OF_FROZEN_REPOSITORY_AUTHORITIES",
        "snapshotLabel": "Repository 正式 Authority 狀態快照",
        "project": {
            "name": "Qookey Crypto Autopilot",
            "mode": "PAPER-ONLY",
            "marketCount": len(candidate_symbols),
            "fundingMonthsObserved": int(scan["monthly_available_checks"]),
            "tradePlanAuthorized": False,
            "liveTradingAuthorized": False,
            "fundingV0_2StorageAuthorized": True,
            "fundingWriterReady": False,
            "fundingWriterState": "NOT_READY",
            "fundingV0_2SourceMonths": int(authorized_scope["source_archive_count"]),
            "fundingV0_2AnnualObjects": int(authorized_scope["annual_canonical_objects"]),
            "fundingV0_2R2Identities": int(authorized_scope["planned_total_r2_object_identities"]),
            "fundingV0_2CanonicalScopeSha256": EXPECTED_V0_2_SCOPE_SHA,
            "fundingV0_2ChecksumSetSha256": EXPECTED_V0_2_CHECKSUM_SHA,
        },
        "pipeline": [
            pipeline_item(
                "Pionex M1A 資料集",
                "15 個標的、15M / 60M / 4H 的 Pionex-native 凍結證據",
                "PASS",
            ),
            pipeline_item(
                "Binance 2025 R2 資料",
                "Provider 分離的 Trade-Kline 歷史資料已完成 2025 R2 pilot",
                "PASS",
            ),
            pipeline_item(
                "Funding 來源證明",
                "官方 checksum、schema、時間順序與 cadence 語意已驗證",
                "PASS",
            ),
            pipeline_item(
                "Funding 覆蓋範圍",
                f"15 個標的共觀察到 {scan['monthly_available_checks']:,} 個 symbol-month",
                "PASS",
            ),
            pipeline_item(
                "Funding V0.2 R2 儲存授權",
                "精確 1,003 個來源月份 / 94 個年度 Parquet / 192 個 R2 identities 已授權",
                "AUTHORIZED",
            ),
            pipeline_item(
                "Funding V0.2 Writer / Full Preflight",
                "Writer 尚未以新 V0.2 scope 完成 1,003 archive + 94 annual partition 全量 preflight",
                "NOT_READY",
            ),
            pipeline_item(
                "Pionex ↔ Binance 等價性",
                "45 組凍結比對仍等待來源 publication evidence；source switch 尚未授權",
                equivalence_status,
            ),
            pipeline_item(
                "歷史 Universe Membership",
                "Long-horizon review 已 PASS，但正式 membership 證據尚未完成",
                "NOT_READY",
            ),
        ],
        "gates": [
            gate(
                "R2 儲存預算",
                "目前歷史資料預算 authority 維持 PASS；V0.2 Funding scope 比原預算更小。",
                "PASS",
                "pass",
                False,
            ),
            gate(
                "Provider 等價性",
                "Pionex ↔ Binance Equivalence Gate 尚未 PASS，因此 source switch 仍被阻擋。",
                equivalence_status,
                "pending",
                True,
            ),
            gate(
                "歷史 Universe",
                "Long-horizon review PASS 不等於正式 Historical Universe membership authority。",
                "NOT_READY",
                "pending",
                True,
            ),
            gate(
                "Funding Materialization",
                "V0.2 儲存 scope 已授權，但 Writer / Full Preflight 尚未完成，因此尚未宣稱 R2 materialization PASS。",
                "NOT_READY",
                "pending",
                True,
            ),
            gate(
                "HYPEUSDT 2026 Funding",
                "2026 年度 partition 因 2026-06 官方 archive cadence gap 而整年 defer；禁止插值或跨 provider 補值。",
                "REVIEW_REQUIRED",
                "pending",
                False,
            ),
            gate(
                "模擬券商 Paper Broker",
                "Production-grade lifecycle 與 reconciliation authority 尚未完成。",
                "NOT_READY",
                "pending",
                True,
            ),
            gate(
                "真實交易",
                "目前沒有任何真實資金下單或私人 execution route 授權。",
                "NOT_AUTHORIZED",
                "blocked",
                True,
            ),
        ],
        "markets": markets,
        "sourceAuthorities": [
            str(M1A),
            str(BINANCE_2025),
            str(FUNDING_SOURCE),
            str(FUNDING_COVERAGE),
            str(FUNDING_CONTINUITY_REVIEW),
            str(FUNDING_AUTHORITY_V0_2),
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
                "stage": "DASHBOARD_ZH_HANT_AUTHORITY_SNAPSHOT_PASS",
                "market_count": snapshot["project"]["marketCount"],
                "funding_months_observed": snapshot["project"]["fundingMonthsObserved"],
                "funding_v0_2_storage_authorized": snapshot["project"][
                    "fundingV0_2StorageAuthorized"
                ],
                "funding_writer_state": snapshot["project"]["fundingWriterState"],
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
