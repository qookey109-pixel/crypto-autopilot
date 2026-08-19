from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.binance_historical import pionex_perp_to_binance_usdm
from crypto_autopilot.binance_vision import BinanceVisionArchiveKey, ingest_kline_archive
from crypto_autopilot.equivalence_forensics import analyze_direction_mismatches
from crypto_autopilot.provider_equivalence import (
    ProviderEquivalencePolicy,
    aggregate_provider_equivalence,
    compare_provider_pair,
)
from crypto_autopilot.storage.parquet import parquet_to_candles
from crypto_autopilot.storage.r2 import R2Store


M1A_AUTHORITY = Path("research/receipts/2026-08-17-m1a-pionex.json")
M1B_AUTHORITY = Path("research/receipts/2026-08-18-m1b-r2.json")
FROZEN_RESULT = Path("research/receipts/2026-08-19-pionex-binance-equivalence-v0-1.json")
POLICY_PATH = Path("config/provider_equivalence_v0_1.json")
BINANCE_INTERVAL = {"15M": "15m", "60M": "1h", "4H": "4h"}
EXPECTED_FROZEN_RESULT_SHA = "c4ddf68700b03c907fbf43101e9a8a39ead12fa80d395119aa53d3b52e527353"
EXPECTED_FROZEN_ARTIFACT_SHA = "16975dfcdc34c621b7abe8326cb3cdab0aebffcee27dce2720a8db7f28640af0"


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def validate_frozen_authorities(
    m1a: dict[str, object],
    m1b: dict[str, object],
    policy_json: dict[str, object],
    frozen: dict[str, object],
) -> tuple[int, int]:
    if m1a.get("stage") != "M1A_COMPLETE" or (m1a.get("audit") or {}).get("pass") is not True:
        raise RuntimeError("M1A authority must remain COMPLETE/PASS")
    if m1b.get("stage") != "M1B_COMPLETE" or m1b.get("status") != "PASS":
        raise RuntimeError("M1B authority must remain PASS")
    if (m1b.get("dataset") or {}).get("object_count") != 45:
        raise RuntimeError("M1B authority must contain 45 overlap objects")
    if policy_json.get("status") != "PROTOCOL_FROZEN_BEFORE_LIVE_EVIDENCE":
        raise RuntimeError("equivalence V0.1 policy is not frozen")
    if frozen.get("status") != "FAIL" or frozen.get("stage") != "PIONEX_BINANCE_EQUIVALENCE_GATE_FAIL":
        raise RuntimeError("forensics requires the frozen V0.1 FAIL authority")

    protocol = frozen.get("protocol") or {}
    execution = frozen.get("execution") or {}
    aggregate = frozen.get("aggregate") or {}
    boundary = frozen.get("authority_boundary") or {}
    if not all(isinstance(value, dict) for value in (protocol, execution, aggregate, boundary)):
        raise RuntimeError("frozen V0.1 authority shape changed")
    if execution.get("workflow_run_id") != 32206479914:
        raise RuntimeError("frozen V0.1 evidence run changed")
    if execution.get("artifact_zip_sha256") != EXPECTED_FROZEN_ARTIFACT_SHA:
        raise RuntimeError("frozen V0.1 artifact SHA changed")
    if execution.get("result_json_sha256") != EXPECTED_FROZEN_RESULT_SHA:
        raise RuntimeError("frozen V0.1 result SHA changed")
    if aggregate.get("gate_status") != "FAIL":
        raise RuntimeError("frozen V0.1 Gate result changed")
    if (
        aggregate.get("evaluated_pair_count"),
        aggregate.get("pass_count"),
        aggregate.get("review_count"),
        aggregate.get("fail_count"),
    ) != (45, 18, 18, 9):
        raise RuntimeError("frozen V0.1 aggregate counts changed")
    if boundary.get("source_switch_authorized") is not False:
        raise RuntimeError("source switching must remain unauthorized")
    if boundary.get("staged_trade_kline_w1_materialization_authorized") is not False:
        raise RuntimeError("W1 must remain unauthorized")
    if boundary.get("live_trading_authorized") is not False:
        raise RuntimeError("live trading must remain unauthorized")

    policy_window = policy_json.get("overlap_window") or {}
    if not isinstance(policy_window, dict):
        raise RuntimeError("policy overlap window shape changed")
    if protocol.get("overlap_start_utc") != policy_window.get("start_utc"):
        raise RuntimeError("receipt/policy overlap start mismatch")
    if protocol.get("overlap_end_utc") != policy_window.get("end_utc"):
        raise RuntimeError("receipt/policy overlap end mismatch")
    if m1a.get("sample", {}).get("requested_start_utc") != policy_window.get("start_utc"):
        raise RuntimeError("M1A/policy overlap start mismatch")
    if m1a.get("sample", {}).get("requested_end_utc") != policy_window.get("end_utc"):
        raise RuntimeError("M1A/policy overlap end mismatch")

    start_ms = int(
        datetime.fromisoformat(str(policy_window["start_utc"]).replace("Z", "+00:00")).timestamp()
        * 1000
    )
    end_ms = int(
        datetime.fromisoformat(str(policy_window["end_utc"]).replace("Z", "+00:00")).timestamp()
        * 1000
    )
    return start_ms, end_ms


def provider_policy(policy_json: dict[str, object]) -> ProviderEquivalencePolicy:
    price = policy_json["price_metrics_bps"]
    behavior = policy_json["behavior_metrics"]
    minimum = policy_json["minimum_rows"]
    return ProviderEquivalencePolicy(
        median_ohlc_bps_pass=float(price["median_ohlc"]["pass_max"]),
        median_ohlc_bps_review=float(price["median_ohlc"]["review_max"]),
        p95_open_close_bps_pass=float(price["p95_open_close"]["pass_max"]),
        p95_open_close_bps_review=float(price["p95_open_close"]["review_max"]),
        p95_high_low_bps_pass=float(price["p95_high_low"]["pass_max"]),
        p95_high_low_bps_review=float(price["p95_high_low"]["review_max"]),
        return_direction_agreement_pass=float(
            behavior["close_to_close_direction_agreement"]["pass_min"]
        ),
        return_direction_agreement_review=float(
            behavior["close_to_close_direction_agreement"]["review_min"]
        ),
        setup_60m_agreement_pass=float(behavior["setup_60m_agreement"]["pass_min"]),
        setup_60m_agreement_review=float(behavior["setup_60m_agreement"]["review_min"]),
        min_ready_setup_bars_60m=int(behavior["setup_60m_agreement"]["minimum_ready_bars"]),
        min_rows_15m=int(minimum["15M"]),
        min_rows_60m=int(minimum["60M"]),
        min_rows_4h=int(minimum["4H"]),
        max_review_fraction_for_aggregate_review=0.20,
    )


def download(url: str, *, retries: int = 3, timeout_seconds: float = 30.0) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(
                url,
                headers={"User-Agent": "qookey-equivalence-v0-1-forensics/0.1"},
            )
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                return response.read()
        except HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                break
        except (URLError, TimeoutError) as exc:
            last_error = exc
        if attempt + 1 < retries:
            time.sleep(0.75 * (attempt + 1))
    raise RuntimeError(f"failed to download frozen Binance Vision evidence: {url}: {last_error}") from last_error


def fetch_archive(key: BinanceVisionArchiveKey):
    return ingest_kline_archive(
        key,
        archive_bytes=download(key.url),
        checksum_payload=download(key.checksum_url),
    )


def date_periods(start_ms: int, end_ms: int) -> tuple[str, ...]:
    current = datetime.fromtimestamp(start_ms / 1000.0, tz=timezone.utc).date()
    end = datetime.fromtimestamp(end_ms / 1000.0, tz=timezone.utc).date()
    values: list[str] = []
    while current <= end:
        values.append(current.isoformat())
        current += timedelta(days=1)
    return tuple(values)


def fetch_binance_evidence(symbols: tuple[str, ...], periods: tuple[str, ...], workers: int):
    keys = [
        BinanceVisionArchiveKey("klines", "daily", symbol, interval, period)
        for symbol in symbols
        for interval in ("15m", "1h", "4h")
        for period in periods
    ]
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_archive, key): key for key in keys}
        for future in as_completed(futures):
            key = futures[future]
            results[(key.symbol, key.interval, key.period)] = future.result()
    if len(results) != len(keys):
        raise RuntimeError(f"Binance archive count mismatch: {len(results)} != {len(keys)}")
    return results


def add_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 0) + int(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/pionex-binance-equivalence-v0-1-forensics.json")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        raise ValueError("workers must be between 1 and 16")

    m1a = load_json(M1A_AUTHORITY)
    m1b = load_json(M1B_AUTHORITY)
    policy_json = load_json(POLICY_PATH)
    frozen = load_json(FROZEN_RESULT)
    start_ms, end_ms = validate_frozen_authorities(m1a, m1b, policy_json, frozen)
    policy = provider_policy(policy_json)

    selected = m1a.get("selected_universe") or []
    selected_pairs = tuple(
        (str(row["symbol"]), pionex_perp_to_binance_usdm(str(row["symbol"]))) for row in selected
    )
    if len(selected_pairs) != 15 or len({right for _, right in selected_pairs}) != 15:
        raise RuntimeError("forensics requires the frozen 15-symbol mapping")

    periods = date_periods(start_ms, end_ms)
    if len(periods) != 8:
        raise RuntimeError(f"frozen overlap should touch 8 UTC daily periods, got {len(periods)}")
    binance_archives = fetch_binance_evidence(
        tuple(right for _, right in selected_pairs), periods, args.workers
    )
    if len(binance_archives) != 360:
        raise RuntimeError("forensics requires the same 360 Binance daily archives as frozen evidence")

    store = R2Store(
        account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
        bucket=os.environ["R2_BUCKET_NAME"],
        access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )
    manifest_meta = m1b["manifest"]
    manifest_bytes = store.get_bytes_verified(
        str(manifest_meta["key"]), expected_sha256=str(manifest_meta["r2_sha256"])
    )
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    if manifest.get("object_count") != 45:
        raise RuntimeError("M1B manifest object count changed")
    if int(manifest.get("requested_start_ms")) != start_ms:
        raise RuntimeError("M1B manifest start changed")
    if int(manifest.get("requested_end_ms")) != end_ms:
        raise RuntimeError("M1B manifest end changed")
    object_index = {
        (str(item["symbol"]), str(item["interval"])): item for item in manifest.get("objects", [])
    }
    if len(object_index) != 45:
        raise RuntimeError("M1B manifest must contain 45 unique symbol/interval identities")

    pair_rows: list[dict[str, object]] = []
    reproduced_results = []
    interval_mismatch_counts: dict[str, int] = {"15M": 0, "60M": 0, "4H": 0}
    status_mismatch_counts: dict[str, int] = {"PASS": 0, "REVIEW": 0, "FAIL": 0}
    global_bin_counts: dict[str, int] = {}
    global_shape_counts: dict[str, int] = {}

    for pionex_symbol, binance_symbol in selected_pairs:
        for interval in ("15M", "60M", "4H"):
            source = object_index[(pionex_symbol, interval)]
            pionex_payload = store.get_bytes_verified(
                str(source["key"]), expected_sha256=str(source["sha256"])
            )
            pionex_candles = tuple(parquet_to_candles(pionex_payload))
            if len(pionex_candles) != int(source["rows"]):
                raise RuntimeError(f"Pionex R2 row mismatch: {pionex_symbol} {interval}")

            binance_interval = BINANCE_INTERVAL[interval]
            binance_candles = tuple(
                candle
                for period in periods
                for candle in binance_archives[(binance_symbol, binance_interval, period)].candles
                if start_ms <= candle.time_ms <= end_ms
            )
            reproduced = compare_provider_pair(
                pionex_symbol=pionex_symbol,
                binance_symbol=binance_symbol,
                interval=interval,
                pionex_candles=pionex_candles,
                binance_candles=binance_candles,
                policy=policy,
            )
            reproduced_results.append(reproduced)
            forensic = analyze_direction_mismatches(pionex_candles, binance_candles)
            if abs(float(forensic["direction_agreement"]) - float(reproduced.return_direction_agreement)) > 1e-12:
                raise RuntimeError(f"direction agreement reproduction mismatch: {pionex_symbol} {interval}")

            mismatch_count = int(forensic["direction_mismatch_count"])
            interval_mismatch_counts[interval] += mismatch_count
            status_mismatch_counts[reproduced.status] += mismatch_count
            add_counts(global_bin_counts, forensic["max_abs_return_bps_bin_counts"])
            add_counts(global_shape_counts, forensic["mismatch_shape_counts"])
            pair_rows.append(
                {
                    "pionex_symbol": pionex_symbol,
                    "binance_symbol": binance_symbol,
                    "interval": interval,
                    "v0_1_status": reproduced.status,
                    "v0_1_reasons": list(reproduced.reasons),
                    "v0_1_return_direction_agreement": reproduced.return_direction_agreement,
                    "forensics": forensic,
                }
            )

    aggregate = aggregate_provider_equivalence(reproduced_results, expected_pair_count=45, policy=policy)
    if (aggregate.status, aggregate.pass_count, aggregate.review_count, aggregate.fail_count) != (
        "FAIL",
        18,
        18,
        9,
    ):
        raise RuntimeError("forensic replay did not reproduce frozen V0.1 aggregate")

    failed_pairs = [row for row in pair_rows if row["v0_1_status"] == "FAIL"]
    if len(failed_pairs) != 9:
        raise RuntimeError("forensics did not reproduce exactly nine failed pairs")
    if any("return_direction_agreement_fail" not in row["v0_1_reasons"] for row in failed_pairs):
        raise RuntimeError("unexpected V0.1 fail reason during forensic replay")

    total_mismatches = sum(int(row["forensics"]["direction_mismatch_count"]) for row in pair_rows)
    failed_pair_mismatches = sum(
        int(row["forensics"]["direction_mismatch_count"]) for row in failed_pairs
    )

    payload = {
        "schema": "pionex-binance-equivalence-v0-1-direction-forensics-v0.1",
        "execution_status": "PASS",
        "analysis_status": "DESCRIPTIVE_ONLY",
        "date": "2026-08-19",
        "frozen_v0_1_authority": str(FROZEN_RESULT),
        "frozen_v0_1_gate_status": "FAIL",
        "frozen_v0_1_outcome_changed": False,
        "overlap": {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "start_utc": policy_json["overlap_window"]["start_utc"],
            "end_utc": policy_json["overlap_window"]["end_utc"],
            "daily_period_count": len(periods),
            "daily_periods": list(periods),
        },
        "source_replay": {
            "pionex_r2_manifest_read": True,
            "pionex_r2_object_count": 45,
            "binance_vision_daily_archive_count": len(binance_archives),
            "official_binance_checksums_verified": True,
            "r2_reads_performed": True,
            "r2_writes_performed": False,
            "r2_deletes_performed": False,
            "provider_splicing_used": False,
            "private_api_used": False,
        },
        "v0_1_reproduction": {
            "pair_count": len(pair_rows),
            "pass_count": aggregate.pass_count,
            "review_count": aggregate.review_count,
            "fail_count": aggregate.fail_count,
            "gate_status": aggregate.status,
            "all_nine_failures_return_direction_agreement": True,
        },
        "direction_forensics_summary": {
            "total_direction_mismatches_all_pairs": total_mismatches,
            "direction_mismatches_in_v0_1_fail_pairs": failed_pair_mismatches,
            "mismatches_by_interval": interval_mismatch_counts,
            "mismatches_by_v0_1_status": status_mismatch_counts,
            "mismatch_shape_counts": global_shape_counts,
            "max_abs_return_bps_bin_counts": global_bin_counts,
        },
        "pairs": pair_rows,
        "decision_boundary": {
            "descriptive_bins_are_gate_thresholds": False,
            "new_deadband_applied": False,
            "new_threshold_proposed": False,
            "v0_1_thresholds_changed": False,
            "v0_1_scope_changed": False,
            "source_switch_authorized": False,
            "staged_trade_kline_w1_materialization_authorized": False,
            "backtest_admission_authorized": False,
            "trade_plan_authorized": False,
            "live_trading_authorized": False,
        },
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_sha": os.getenv("GITHUB_SHA"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "execution_status": "PASS",
                "frozen_gate_status": "FAIL",
                "pairs": len(pair_rows),
                "fail_pairs": len(failed_pairs),
                "direction_mismatches": total_mismatches,
                "failed_pair_direction_mismatches": failed_pair_mismatches,
                "r2_writes_performed": False,
                "new_threshold_proposed": False,
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
