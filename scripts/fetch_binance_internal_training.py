from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from crypto_autopilot.binance_spot_history import (
    BinanceSpotCandle,
    BinanceSpotHistoryError,
    BinanceSpotSeries,
    fetch_spot_history,
    provider_read_stop_ms_from_v0_5_config,
)
from crypto_autopilot.ephemeral_storage import require_ephemeral_output
from crypto_autopilot.training_quality import load_v0_5_authority_pair


FORBIDDEN_AUTHORITY_KEYS = (
    "production_r2_access_authorized",
    "provider_splicing_authorized",
    "pionex_native_relabel_authorized",
    "source_switch_authorized",
    "holdout_access_authorized",
    "trade_kline_w1_materialization_authorized",
    "formal_trade_plan_authorized",
    "real_money_order_authorized",
    "live_trading_authorized",
)
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = (
    REPOSITORY_ROOT / "config/binance_spot_r2_training_governance_v0_5.json"
)


def parse_utc_ms(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def iso_utc(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows_for(series: list[BinanceSpotSeries], metadata: dict[str, dict]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in series:
        meta = metadata[item.symbol]
        audit_ok = item.audit_ok
        rows.extend(
            {
                "provider": "binance_spot",
                "market_type": meta["market_type"],
                "asset_class": meta["asset_class"],
                "classification_method": meta["classification_method"],
                "classification_confidence": meta["classification_confidence"],
                "base_asset": meta["base_asset"],
                "quote_asset": meta["quote_asset"],
                "symbol": item.symbol,
                "interval": item.interval,
                "audit_ok": audit_ok,
                "open_time_ms": candle.open_time_ms,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "base_volume": candle.base_volume,
                "quote_volume": candle.quote_volume,
                "trade_count": candle.trade_count,
            }
            for candle in item.candles
        )
    return rows


def write_outputs(output_dir: Path, rows: list[dict[str, object]]) -> tuple[Path, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = output_dir / "binance-spot-internal-training-1d.parquet"
    pq.write_table(pa.Table.from_pylist(rows), parquet_path, compression="zstd")
    return parquet_path, len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ephemeral Binance Spot history for R2 publishing")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--start-utc", default="2020-01-01T00:00:00Z")
    parser.add_argument("--interval", default="1d", choices=("1d",))
    parser.add_argument("--requests-per-second", type=float, default=5.0)
    parser.add_argument("--now-ms", type=int)
    parser.add_argument("--asset-classes", nargs="*")
    args = parser.parse_args()
    output_dir = require_ephemeral_output(args.output_dir)
    config_path = Path(args.config)
    config_payload = config_path.read_bytes()
    config = json.loads(config_payload)
    load_v0_5_authority_pair(
        config,
        config_path=config_path,
        config_payload=config_payload,
        repository_root=REPOSITORY_ROOT,
    )
    provider_read_stop_ms = provider_read_stop_ms_from_v0_5_config(config)

    catalog_payload = Path(args.catalog).read_bytes()
    catalog = json.loads(catalog_payload)
    if catalog.get("schema") != "binance-internal-training-market-catalog-v0.2":
        raise RuntimeError("unsupported training catalog schema")
    authority = catalog.get("authority") or {}
    if any(authority.get(key) is not False for key in FORBIDDEN_AUTHORITY_KEYS):
        raise RuntimeError("training catalog authority boundary changed")
    selected = catalog.get("markets") or []
    if args.asset_classes:
        allowed = set(args.asset_classes)
        selected = [item for item in selected if item.get("asset_class") in allowed]
    if not selected:
        raise RuntimeError("training catalog contains no selected markets")
    metadata = {str(item["symbol"]): item for item in selected}

    now = datetime.fromtimestamp(args.now_ms / 1000, tz=UTC) if args.now_ms else datetime.now(UTC)
    end_ms = int((datetime(now.year, now.month, now.day, tzinfo=UTC) - timedelta(days=1)).timestamp() * 1000)
    start_ms = parse_utc_ms(args.start_utc)
    if end_ms < start_ms:
        raise RuntimeError("no complete UTC day exists inside requested range")

    cache_dir = output_dir / "series-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    series: list[BinanceSpotSeries] = []
    errors: dict[str, str] = {}
    for index, item in enumerate(selected, start=1):
        symbol = str(item["symbol"])
        cache_path = cache_dir / f"{symbol}.json"
        result: BinanceSpotSeries | None = None
        cache_hit = False
        if cache_path.is_file():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                if (
                    cached.get("start_time_ms") == start_ms
                    and cached.get("end_time_ms") == end_ms
                    and cached.get("interval") == args.interval
                ):
                    candles = tuple(BinanceSpotCandle(**row) for row in cached.get("candles", []))
                    result = BinanceSpotSeries(
                        symbol,
                        args.interval,
                        start_ms,
                        end_ms,
                        int(cached.get("pages_fetched", 0)),
                        candles,
                    )
                    if cached.get("error"):
                        errors[symbol] = str(cached["error"])
                    cache_hit = True
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                result = None
        if result is None:
            try:
                result = fetch_spot_history(
                    symbol,
                    start_time_ms=start_ms,
                    end_time_ms=end_ms,
                    interval=args.interval,
                    page_limit=1000,
                    requests_per_second=args.requests_per_second,
                    provider_read_stop_ms=provider_read_stop_ms,
                )
            except (BinanceSpotHistoryError, ValueError, TimeoutError, OSError) as exc:
                errors[symbol] = str(exc)
                result = BinanceSpotSeries(symbol, args.interval, start_ms, end_ms, 0, ())
            cache_path.write_text(
                json.dumps(
                    {
                        "symbol": symbol,
                        "interval": args.interval,
                        "start_time_ms": start_ms,
                        "end_time_ms": end_ms,
                        "pages_fetched": result.pages_fetched,
                        "candles": [asdict(candle) for candle in result.candles],
                        "error": errors.get(symbol),
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
        series.append(result)
        print(
            f"[{index}/{len(selected)}] {symbol}: {len(result.candles)} rows / "
            f"audit={result.audit_ok} / error={errors.get(symbol, 'none')} / "
            f"{'cached' if cache_hit else 'fetched'}",
            flush=True,
        )

    with_rows = [item for item in series if item.candles]
    audited = [item for item in with_rows if item.audit_ok]
    if not audited:
        raise RuntimeError("no audited Binance Spot history was fetched")
    rows = rows_for(with_rows, metadata)
    parquet_path, row_count = write_outputs(output_dir, rows)
    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    receipt = {
        "schema": "binance-internal-training-run-v0.2",
        "status": "PASS" if not errors else "PARTIAL",
        "provider": "binance_spot",
        "market_type": "spot",
        "interval": args.interval,
        "generated_at_utc": generated_at,
        "requested_start_utc": args.start_utc,
        "captured_through_utc": iso_utc(end_ms),
        "market_count_requested": len(selected),
        "market_count_with_rows": len(with_rows),
        "market_count_audited": len(audited),
        "row_count": row_count,
        "asset_class_counts": dict(Counter(metadata[item.symbol]["asset_class"] for item in with_rows)),
        "quote_asset_counts": dict(Counter(metadata[item.symbol]["quote_asset"] for item in with_rows)),
        "audit_failures": [item.symbol for item in with_rows if not item.audit_ok],
        "market_audit_evidence": {
            item.symbol: {**item.audit_evidence, "audit_ok": item.audit_ok}
            for item in sorted(series, key=lambda value: value.symbol)
        },
        "errors": errors,
        "catalog": {
            "sha256": hashlib.sha256(catalog_payload).hexdigest(),
            "bytes": len(catalog_payload),
        },
        "parquet": {"path": str(parquet_path), "sha256": sha256_file(parquet_path), "bytes": parquet_path.stat().st_size},
        "website_projection": {"authorized": False, "written": False},
        "authority": authority,
    }
    (output_dir / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "rows": row_count, "with_rows": len(with_rows), "audited": len(audited), "requested": len(selected)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
