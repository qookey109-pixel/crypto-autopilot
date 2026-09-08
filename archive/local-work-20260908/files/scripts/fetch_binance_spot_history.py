from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from crypto_autopilot.binance_spot_history import (
    BinanceSpotHistoryError,
    BinanceSpotSeries,
    fetch_spot_history,
)
from crypto_autopilot.ephemeral_storage import require_ephemeral_output


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


def write_csv(path: Path, series: list[BinanceSpotSeries]) -> int:
    count = 0
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "provider",
                "symbol",
                "interval",
                "open_time_ms",
                "open",
                "high",
                "low",
                "close",
                "base_volume",
                "quote_volume",
                "trade_count",
                "taker_buy_base_volume",
                "taker_buy_quote_volume",
            ]
        )
        for item in series:
            for candle in item.candles:
                writer.writerow(
                    [
                        "binance_spot",
                        item.symbol,
                        item.interval,
                        candle.open_time_ms,
                        candle.open,
                        candle.high,
                        candle.low,
                        candle.close,
                        candle.base_volume,
                        candle.quote_volume,
                        candle.trade_count,
                        candle.taker_buy_base_volume,
                        candle.taker_buy_quote_volume,
                    ]
                )
                count += 1
    return count


def write_parquet(path: Path, series: list[BinanceSpotSeries]) -> int:
    rows: list[dict[str, object]] = []
    for item in series:
        rows.extend(
            {
                "provider": "binance_spot",
                "symbol": item.symbol,
                "interval": item.interval,
                "open_time_ms": candle.open_time_ms,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "base_volume": candle.base_volume,
                "quote_volume": candle.quote_volume,
                "trade_count": candle.trade_count,
                "taker_buy_base_volume": candle.taker_buy_base_volume,
                "taker_buy_quote_volume": candle.taker_buy_quote_volume,
            }
            for candle in item.candles
        )
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, path, compression="zstd")
    return len(rows)


def projection(config: dict[str, object], series: list[BinanceSpotSeries], generated_at: str) -> dict:
    sample_every = int((config.get("projection") or {}).get("sample_every_days", 7))
    markets = []
    for item in series:
        candles = list(item.candles)
        selected = candles[::sample_every]
        if candles and (not selected or selected[-1].open_time_ms != candles[-1].open_time_ms):
            selected.append(candles[-1])
        markets.append(
            {
                "symbol": item.symbol,
                "status": "PASS" if candles and item.audit_ok else "NO_DATA",
                "rowCount": len(candles),
                "firstTimeUtc": iso_utc(candles[0].open_time_ms) if candles else None,
                "lastTimeUtc": iso_utc(candles[-1].open_time_ms) if candles else None,
                "firstClose": candles[0].close if candles else None,
                "lastClose": candles[-1].close if candles else None,
                "points": [
                    [candle.open_time_ms, candle.close, candle.quote_volume]
                    for candle in selected
                ],
            }
        )
    return {
        "schema": "binance-spot-history-dashboard-v0.1",
        "authority": False,
        "locale": "zh-Hant-TW",
        "status": "PASS" if sum(bool(item.candles) for item in series) >= int(config["minimum_symbols"]) else "PARTIAL",
        "provider": "binance_spot",
        "delivery": "binance_public_rest",
        "interval": str(config["interval"]),
        "requestedStartUtc": str(config["start_utc"]),
        "generatedAtUtc": generated_at,
        "sourceEndpoint": "https://data-api.binance.vision/api/v3/klines",
        "interpretation": "Binance Spot research projection; not Pionex-native and not a trade signal.",
        "markets": markets,
        "authorityBoundary": config["authority"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch provider-separated Binance Spot daily history")
    parser.add_argument("--config", default="config/binance_spot_history_v0_1.json")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--web-output", required=True)
    parser.add_argument("--now-ms", type=int)
    args = parser.parse_args()
    output_dir = require_ephemeral_output(args.output_dir)
    web_path = require_ephemeral_output(args.web_output)

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    authority = config.get("authority") or {}
    forbidden_true = (
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
    if any(authority.get(key) is not False for key in forbidden_true):
        raise RuntimeError("Binance Spot local research authority boundary changed")
    if config.get("provider") != "binance_spot" or config.get("interval") != "1d":
        raise RuntimeError("V0.1 requires provider=binance_spot and interval=1d")

    now = datetime.fromtimestamp(args.now_ms / 1000, tz=UTC) if args.now_ms else datetime.now(UTC)
    last_complete_day = datetime(now.year, now.month, now.day, tzinfo=UTC) - timedelta(days=1)
    start_ms = parse_utc_ms(str(config["start_utc"]))
    end_ms = int(last_complete_day.timestamp() * 1000)
    if end_ms < start_ms:
        raise RuntimeError("no complete UTC day exists inside requested range")

    all_series = []
    errors: dict[str, str] = {}
    for symbol in config["symbols"]:
        try:
            item = fetch_spot_history(
                str(symbol),
                start_time_ms=start_ms,
                end_time_ms=end_ms,
                interval=str(config["interval"]),
                page_limit=int(config["page_limit"]),
                requests_per_second=float(config["requests_per_second"]),
            )
        except BinanceSpotHistoryError as exc:
            errors[str(symbol)] = str(exc)
            item = BinanceSpotSeries(
                symbol=str(symbol),
                interval=str(config["interval"]),
                requested_start_ms=start_ms,
                requested_end_ms=end_ms,
                pages_fetched=0,
                candles=(),
            )
        all_series.append(item)
        print(
            f"{item.symbol}: {len(item.candles)} rows / {item.pages_fetched} pages / "
            f"audit={item.audit_ok} / error={errors.get(item.symbol, 'none')}"
        )

    available = [item for item in all_series if item.candles and item.audit_ok]
    if len(available) < int(config["minimum_symbols"]):
        raise RuntimeError(
            f"only {len(available)} audited Binance Spot markets; minimum is {config['minimum_symbols']}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "binance-spot-daily-2020-to-present.csv.gz"
    parquet_path = output_dir / "binance-spot-daily-2020-to-present.parquet"
    receipt_path = output_dir / "receipt.json"
    web_path.parent.mkdir(parents=True, exist_ok=True)

    csv_rows = write_csv(csv_path, all_series)
    parquet_rows = write_parquet(parquet_path, all_series)
    if csv_rows != parquet_rows:
        raise RuntimeError("CSV/Parquet row count mismatch")

    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    web_payload = projection(config, all_series, generated_at)
    web_path.write_text(json.dumps(web_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "schema": "binance-spot-history-local-run-v0.1",
        "status": "PASS",
        "provider": "binance_spot",
        "delivery": "binance_public_rest",
        "generated_at_utc": generated_at,
        "requested_start_utc": str(config["start_utc"]),
        "captured_through_utc": iso_utc(end_ms),
        "market_count": len(available),
        "row_count": parquet_rows,
        "csv_gzip": {"path": str(csv_path), "sha256": sha256_file(csv_path), "bytes": csv_path.stat().st_size},
        "parquet": {"path": str(parquet_path), "sha256": sha256_file(parquet_path), "bytes": parquet_path.stat().st_size},
        "markets": [
            {
                "symbol": item.symbol,
                "status": "PASS" if item.candles and item.audit_ok else "NO_DATA",
                "rows": len(item.candles),
                "pages": item.pages_fetched,
                "first_time_utc": iso_utc(item.candles[0].open_time_ms) if item.candles else None,
                "last_time_utc": iso_utc(item.candles[-1].open_time_ms) if item.candles else None,
                "audit_ok": item.audit_ok,
                "error": errors.get(item.symbol),
            }
            for item in all_series
        ],
        "authority": authority,
    }
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "rows": parquet_rows, "output": str(output_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
