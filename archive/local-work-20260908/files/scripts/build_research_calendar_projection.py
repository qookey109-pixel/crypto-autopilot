from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re


V0_10_CUTOVER = Path("config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json")
DETAILED_HISTORY = Path("config/binance_usdm_detailed_history_v0_1_1.json")
SUCCESSOR_SCHEDULE = Path("config/post_window_research_successor_schedule_v0_1.json")
PROJECT_STATUS = Path("PROJECT_STATUS.md")
ROADMAP = Path("docs/CONTINUOUS_LEARNING_ROADMAP_V0_1.md")
SSTATE_INGESTION = Path("docs/HISTORICAL_SSTATE_EVIDENCE_INGESTION_V0_1.md")

SOURCE_AUTHORITIES = (
    PROJECT_STATUS,
    DETAILED_HISTORY,
    V0_10_CUTOVER,
    SUCCESSOR_SCHEDULE,
    ROADMAP,
    SSTATE_INGESTION,
)


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected object source: {path}")
    return payload


def require_dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RuntimeError(f"expected object: {label}")
    return value


def parse_utc(value: object, label: str) -> datetime:
    text = str(value or "")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"invalid UTC timestamp for {label}: {text}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise RuntimeError(f"timestamp must be UTC for {label}: {text}")
    return parsed


def normalized_utc(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return parse_utc(value, "projection-generated-at").isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def first_eligible_run(cron: object, not_before: datetime) -> datetime:
    match = re.fullmatch(r"(\d{1,2}) \*/(\d{1,2}) (\d{1,2})-(\d{1,2}) (\d{1,2}) \*", str(cron))
    if not match:
        raise RuntimeError("detailed-history cron shape changed; calendar projection fails closed")
    minute, hour_step, day_start, day_end, month = map(int, match.groups())
    if not (0 <= minute <= 59 and 1 <= hour_step <= 23 and 1 <= month <= 12):
        raise RuntimeError("detailed-history cron value is invalid")
    for day in range(day_start, day_end + 1):
        for hour in range(0, 24, hour_step):
            candidate = datetime(not_before.year, month, day, hour, minute, tzinfo=timezone.utc)
            if candidate >= not_before:
                return candidate
    raise RuntimeError("no eligible detailed-history run exists inside the configured cron window")


def build_projection(*, generated_at_utc: str | None = None) -> dict[str, object]:
    v0_10 = load_json(V0_10_CUTOVER)
    detailed = load_json(DETAILED_HISTORY)
    successor = load_json(SUCCESSOR_SCHEDULE)
    project_status = PROJECT_STATUS.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")
    sstate = SSTATE_INGESTION.read_text(encoding="utf-8")

    if v0_10.get("status") != "FINAL_ATOMIC_CUTOVER_AUTHORIZED_ON_MAIN_MERGE":
        raise RuntimeError("V0.10 cutover is not the expected effective authority")
    v0_scope = require_dict(v0_10.get("scientific_scope"), "V0.10 scientific_scope")
    v0_boundary = require_dict(v0_10.get("authorization_boundary"), "V0.10 boundary")
    if v0_boundary.get("backtest_admission_authorized") is not False:
        raise RuntimeError("calendar cannot project authorized backtest admission")
    if v0_boundary.get("holdout_candle_access_authorized") is not False:
        raise RuntimeError("calendar cannot project holdout access")

    v0_start = parse_utc(v0_scope.get("metadata_capture_start_utc"), "V0.10 start")
    v0_end = parse_utc(v0_scope.get("metadata_capture_end_utc"), "V0.10 end")
    if int(v0_scope.get("hourly_slot_count") or 0) != 194:
        raise RuntimeError("V0.10 hourly-slot count changed")

    if detailed.get("status") != "EXECUTION_AUTHORIZED_AFTER_V0_10_WINDOW":
        raise RuntimeError("detailed-history authority state changed")
    detailed_scope = require_dict(detailed.get("scope"), "detailed-history scope")
    detailed_execution = require_dict(detailed.get("execution"), "detailed-history execution")
    detailed_authority = require_dict(detailed.get("authority"), "detailed-history authority")
    not_before = parse_utc(detailed_execution.get("not_before_utc"), "detailed-history not-before")
    stop_exclusive = parse_utc(
        detailed_execution.get("backfill_stop_exclusive_utc"), "detailed-history stop"
    )
    first_run = first_eligible_run(detailed_execution.get("schedule_cron"), not_before)
    if first_run >= stop_exclusive:
        raise RuntimeError("detailed-history first run is outside its authority window")
    if detailed_authority.get("replacement_holdout_access_authorized") is not False:
        raise RuntimeError("detailed-history unexpectedly authorizes holdout access")
    if detailed_authority.get("backtest_admission_authorized") is not False:
        raise RuntimeError("detailed-history unexpectedly authorizes backtest admission")
    if int(detailed_scope.get("target_market_count") or 0) != 250:
        raise RuntimeError("detailed-history target market count changed")
    if detailed_scope.get("intervals") != ["15m", "1h", "4h"]:
        raise RuntimeError("detailed-history intervals changed")

    if successor.get("status") != "PREPARED_NOT_ACTIVE":
        raise RuntimeError("post-window successor schedule is no longer prepared-only")
    successor_authority = require_dict(successor.get("current_authority"), "successor authority")
    if not successor_authority or any(value is not False for value in successor_authority.values()):
        raise RuntimeError("prepared successor schedule gained runtime authority")

    required_status_markers = (
        "V0.10 FINAL ATOMIC METADATA CAPTURE CUTOVER EFFECTIVE",
        "REPLACEMENT HOLDOUT FROZEN_UNOPENED",
        "HISTORICAL UNIVERSE MEMBERSHIP NOT_READY",
    )
    for marker in required_status_markers:
        if marker not in project_status:
            raise RuntimeError(f"PROJECT_STATUS marker changed: {marker}")
    if "operational\ncompletion by **2026-09-30**" not in roadmap:
        raise RuntimeError("continuous-learning engineering target changed")
    if "does not yet contain a real historical SState evidence bundle" not in sstate:
        raise RuntimeError("historical SState evidence readiness changed")

    target_at = "2026-09-30T15:59:59.999Z"
    generated = normalized_utc(generated_at_utc)
    return {
        "schema": "qookey-research-calendar-projection-v0.1",
        "authority": False,
        "locale": "zh-Hant-TW",
        "timezone": "Asia/Taipei",
        "projectionGeneratedAtUtc": generated,
        "sourceAuthorities": [str(path) for path in SOURCE_AUTHORITIES],
        "items": [
            {
                "id": "bounded-dual-track",
                "windowLabel": "NOW → 08/27 08:00",
                "title": "既有雙軌研究",
                "detail": "Pionex 紙上訓練與 Binance Spot 研究維持既有邊界；到時停止 provider 讀取。",
                "status": "AUTHORIZED",
                "startsAtUtc": None,
                "endsAtUtc": v0_start.isoformat().replace("+00:00", "Z"),
                "kind": "window",
            },
            {
                "id": "v0-10-metadata-window",
                "windowLabel": "08/27 08:00 → 09/04 09:59",
                "title": "V0.10 Metadata-only",
                "detail": "Frozen window；只收集版本化 metadata，不開啟 holdout candle 或第二條執行路徑。",
                "status": "AUTHORIZED",
                "startsAtUtc": v0_start.isoformat().replace("+00:00", "Z"),
                "endsAtUtc": v0_end.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "kind": "window",
            },
            {
                "id": "detailed-history-backfill",
                "windowLabel": "首個符合排程 09/04 14:23",
                "title": "250 市場歷史回補",
                "detail": "已授權、尚未開始；25 個可續跑分片，Binance USD-M 15m／1h／4h 資料只進 R2。",
                "status": "AUTHORIZED",
                "startsAtUtc": first_run.isoformat(timespec="seconds").replace("+00:00", "Z"),
                "endsAtUtc": stop_exclusive.isoformat(timespec="seconds").replace("+00:00", "Z"),
                "kind": "window",
            },
            {
                "id": "sstate-evidence-calibration",
                "windowLabel": "DEPENDENCY GATE",
                "title": "SState 證據與校準",
                "detail": "必須先取得具真實可用時間的歷史 SState 證據；不得補造狀態，也不得把 60% 當交易勝率。",
                "status": "NOT_READY",
                "startsAtUtc": None,
                "endsAtUtc": None,
                "kind": "dependency",
            },
            {
                "id": "continuous-learning-target",
                "windowLabel": "ENGINEERING TARGET 09/30",
                "title": "研究型閉環",
                "detail": "工程目標，不是執行 authority、獲利承諾或模型自動晉升；完成仍需逐項證據。",
                "status": "PREPARED",
                "targetAtUtc": target_at,
                "kind": "target",
            },
        ],
        "safetyBoundary": {
            "automaticActivation": False,
            "providerAccessAuthorized": False,
            "r2ReadAuthorized": False,
            "r2WriteAuthorized": False,
            "holdoutAccessAuthorized": False,
            "backtestAdmissionAuthorized": False,
            "automaticModelPromotionAuthorized": False,
            "tradePlanAuthorized": False,
            "realMoneyOrderAuthorized": False,
            "liveTradingAuthorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="web/data/research-calendar.json")
    parser.add_argument("--generated-at-utc")
    args = parser.parse_args()
    projection = build_projection(generated_at_utc=args.generated_at_utc)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(projection, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "stage": "RESEARCH_CALENDAR_PROJECTION_V0_1_PASS",
                "authority": projection["authority"],
                "items": len(projection["items"]),
                "output": str(output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
