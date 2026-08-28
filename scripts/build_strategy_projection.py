from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "baseline": ROOT / "config" / "strategy_v0_1.json",
    "technical": ROOT / "config" / "technical_analysis_v0_2.json",
    "parameter_sweep": ROOT / "config" / "strategy_parameter_sweep_v0_1.json",
    "shadow": ROOT / "config" / "binance_spot_shadow_v0_6.json",
    "edge": ROOT / "config" / "strategy_edge_validation_v0_1.json",
    "research_loop": ROOT / "config" / "strategy_research_loop_v0_1.json",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo != timezone.utc:
        raise RuntimeError("generated timestamp must be explicit UTC")
    return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")


def _assert_false(mapping: dict[str, Any], keys: tuple[str, ...], source: str) -> None:
    for key in keys:
        if mapping.get(key) is not False:
            raise RuntimeError(f"{source}.{key} must remain false")


def build_projection(
    *, generated_at_utc: str | None = None, checked_in_fixture: bool = False
) -> dict[str, Any]:
    loaded = {name: _load(path) for name, path in SOURCES.items()}
    baseline = loaded["baseline"]
    technical = loaded["technical"]
    sweep = loaded["parameter_sweep"]
    shadow = loaded["shadow"]
    edge = loaded["edge"]
    loop = loaded["research_loop"]

    _assert_false(
        technical["authority"],
        (
            "strategy_gate_change_authorized",
            "holdout_access_authorized",
            "production_r2_access_authorized",
            "trade_plan_authorized",
            "live_trading_authorized",
        ),
        "technical.authority",
    )
    _assert_false(
        shadow["authority"],
        (
            "provider_reads_authorized",
            "r2_writes_authorized",
            "automatic_model_promotion_authorized",
            "automatic_trade_plan_authorized",
            "real_money_order_authorized",
            "live_trading_authorized",
        ),
        "shadow.authority",
    )
    _assert_false(
        edge["execution"],
        (
            "production_dataset_execution_authorized",
            "provider_requests_authorized",
            "r2_list_read_write_authorized",
            "persistent_local_training_artifacts_authorized",
        ),
        "edge.execution",
    )
    _assert_false(
        loop["execution"],
        (
            "production_dataset_execution_authorized",
            "candidate_return_materialization_authorized",
            "provider_requests_authorized",
            "r2_list_read_write_authorized",
            "second_broker_created",
        ),
        "research_loop.execution",
    )
    if sweep.get("trade_plan_authorized") is not False:
        raise RuntimeError("parameter_sweep.trade_plan_authorized must remain false")
    if loop["composition"].get("automatic_promotion") is not False:
        raise RuntimeError("research_loop automatic promotion must remain false")

    families = loop["candidate_search"]["families"]
    horizons = sorted({horizon for family in families for horizon in family["horizons"]})
    feature_groups = shadow["training"]["groups"]
    return {
        "schema": "qookey-dashboard-strategy-projection-v0.1",
        "authority": False,
        "locale": "zh-Hant-TW",
        "generatedAtUtc": None if checked_in_fixture else _utc_timestamp(generated_at_utc),
        "sourceConfigs": [str(path.relative_to(ROOT)) for path in SOURCES.values()],
        "baseline": baseline,
        "summary": {
            "candidateCount": loop["candidate_search"]["expected_candidate_count"],
            "familyCount": len(families),
            "horizonCount": len(horizons),
            "edgeMethodCount": len(edge["methods"]),
            "technicalIntervalCount": len(technical["supported_intervals"]),
            "shadowFeatureGroupCount": len(feature_groups),
        },
        "analysisLayers": [
            {
                "id": "baseline",
                "name": "Paper 策略基線",
                "status": "PAPER_BASELINE",
                "detail": "SState 准入、100 分技術品質與結構風控；目前仍為 LONG_ONLY。",
            },
            {
                "id": "technical",
                "name": "技術特徵 V0.2",
                "status": "RESEARCH_ONLY",
                "detail": f"{len(technical['supported_intervals'])} 個週期；只允許閉合 K 線與因果特徵。",
            },
            {
                "id": "shadow",
                "name": "Shadow Ablation V0.6",
                "status": shadow["status"],
                "detail": f"{len(feature_groups)} 組特徵逐組比較，不自動晉升模型。",
            },
            {
                "id": "research_loop",
                "name": "策略研究閉環 V0.1",
                "status": loop["status"],
                "detail": f"{loop['candidate_search']['expected_candidate_count']} 個預註冊候選，synthetic only。",
            },
            {
                "id": "edge",
                "name": "Edge 驗證 V0.1",
                "status": edge["status"],
                "detail": f"{len(edge['methods'])} 種抗過擬合方法；通過也只進人工審查。",
            },
            {
                "id": "parameter_sweep",
                "name": "參數搜尋 V0.1",
                "status": sweep["status"],
                "detail": "候選值與驗證切分尚未凍結，不執行正式搜尋。",
            },
        ],
        "safetyBoundary": {
            "providerAccessAuthorized": False,
            "r2AccessAuthorized": False,
            "holdoutAccessAuthorized": False,
            "backtestAdmissionAuthorized": False,
            "automaticModelPromotionAuthorized": False,
            "tradePlanAuthorized": False,
            "realMoneyOrderAuthorized": False,
            "liveTradingAuthorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the safe dashboard strategy projection")
    parser.add_argument("--output", default="web/data/strategy.json")
    parser.add_argument("--generated-at-utc")
    parser.add_argument("--checked-in-fixture", action="store_true")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            build_projection(
                generated_at_utc=args.generated_at_utc,
                checked_in_fixture=args.checked_in_fixture,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
