from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from crypto_autopilot.detailed_history import (
    DetailedHistoryAuthorityError,
    DetailedMarketCoverage,
    build_catalog,
    build_shard_plan,
    load_authority_pair,
    month_range,
    months_from_interval_keys,
    parse_bucket_listing,
    require_execution_window,
    select_training_universe,
    symbols_from_root_prefixes,
    validate_authority_config,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/binance_usdm_detailed_history_v0_1.json"
AUTHORITY = (
    ROOT
    / "research/receipts/2026-08-24-binance-usdm-detailed-history-v0-1-authority.json"
)


def listing_xml(*, prefix: str, common: list[str], keys: list[str]) -> bytes:
    common_xml = "".join(
        f"<CommonPrefixes><Prefix>{value}</Prefix></CommonPrefixes>" for value in common
    )
    key_xml = "".join(f"<Contents><Key>{value}</Key></Contents>" for value in keys)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<Name>data.binance.vision</Name><Prefix>{prefix}</Prefix>"
        "<Marker></Marker><MaxKeys>1000</MaxKeys><IsTruncated>false</IsTruncated>"
        f"{common_xml}{key_xml}</ListBucketResult>"
    ).encode()


def coverage(
    symbol: str,
    *,
    asset_class: str = "crypto",
    reaches_end: bool = True,
    months: int = 48,
) -> DetailedMarketCoverage:
    all_months = month_range("2022-08", "2026-07")
    observed = all_months[:months] if not reaches_end else all_months[-months:]
    return DetailedMarketCoverage(
        symbol=symbol,
        base_asset=symbol.removesuffix("USDT"),
        quote_asset="USDT",
        asset_class=asset_class,
        classification_method="test",
        months_15m=observed,
        months_1h=observed,
        months_4h=observed,
        common_months=observed,
        first_common_month=observed[0],
        last_common_month=observed[-1],
        common_month_count=len(observed),
        missing_common_months_inside_span=(),
        reaches_window_end=reaches_end,
    )


class DetailedHistoryTests(unittest.TestCase):
    def test_official_s3_listing_and_checksum_periods_are_parsed(self) -> None:
        root = "data/futures/um/monthly/klines/"
        parsed = parse_bucket_listing(
            listing_xml(
                prefix=root,
                common=[f"{root}BTCUSDT/", f"{root}AAPLUSDT/", f"{root}OLDUSDTSETTLED/"],
                keys=[],
            ),
            expected_prefix=root,
        )
        self.assertEqual(symbols_from_root_prefixes(parsed.common_prefixes), ("AAPLUSDT", "BTCUSDT"))

        prefix = f"{root}BTCUSDT/15m/"
        archive = f"{prefix}BTCUSDT-15m-2025-01.zip"
        keys = (archive, f"{archive}.CHECKSUM", f"{prefix}BTCUSDT-15m-2025-02.zip")
        self.assertEqual(
            months_from_interval_keys(keys, symbol="BTCUSDT", interval="15m"),
            ("2025-01",),
        )

    def test_catalog_is_exactly_250_and_preserves_category_controls(self) -> None:
        config = json.loads(CONFIG.read_text())
        required = list(config["selection"]["required_continuity_symbols"])
        records = [coverage(symbol) for symbol in required]
        records.extend(
            coverage(f"STOCK{index:03d}USDT", asset_class="tokenized_stock_candidate", months=8)
            for index in range(30)
        )
        records.extend(
            coverage(f"OLD{index:03d}USDT", reaches_end=False, months=36)
            for index in range(19)
        )
        records.extend(
            coverage(f"COIN{index:03d}USDT", months=48)
            for index in range(260)
        )
        catalog = build_catalog(
            records,
            config=config,
            retrieved_at_utc="2026-09-04T02:00:00Z",
        )
        self.assertEqual(catalog["selected_market_count"], 250)
        self.assertEqual(catalog["shard_count"], 25)
        evidence = catalog["selection_evidence"]
        self.assertGreaterEqual(evidence["tokenized_stock_candidate_count"], 20)
        self.assertGreaterEqual(evidence["historical_absence_candidate_count"], 19)
        self.assertGreaterEqual(evidence["window_end_candidate_count"], 175)
        selected = {item["symbol"] for item in catalog["markets"]}
        self.assertTrue(set(required).issubset(selected))
        plan = build_shard_plan(catalog, shard_index=0)
        self.assertGreater(len(plan), 0)
        self.assertTrue(all(item.r2_key.startswith("market-data/binance_usdm/detailed-v0.1/") for item in plan))

    def test_required_symbols_count_toward_category_minimums(self) -> None:
        records = [
            coverage(
                "REQUIREDUSDT",
                asset_class="tokenized_stock_candidate",
                reaches_end=False,
            ),
            coverage("STOCKUSDT", asset_class="tokenized_stock_candidate"),
            coverage("OLDUSDT", reaches_end=False),
            coverage("RECENT1USDT"),
            coverage("RECENT2USDT"),
        ]
        selected = select_training_universe(
            records,
            target_size=5,
            required_symbols=("REQUIREDUSDT",),
            minimum_tokenized_stock_candidates=2,
            minimum_historical_absence_candidates=2,
            minimum_window_end_candidates=3,
        )
        self.assertEqual(len(selected), 5)
        self.assertEqual(
            sum(item.asset_class == "tokenized_stock_candidate" for item in selected),
            2,
        )
        self.assertEqual(sum(not item.reaches_window_end for item in selected), 2)

    def test_authority_is_hash_bound_and_does_not_open_holdout_or_trading(self) -> None:
        config, receipt, config_bytes = load_authority_pair(CONFIG, AUTHORITY)
        self.assertEqual(receipt["config_sha256"], hashlib.sha256(config_bytes).hexdigest())
        validate_authority_config(config)
        self.assertEqual(config["scope"]["target_market_count"], 250)
        self.assertEqual(len(month_range("2022-08", "2026-07")), 48)
        for name in (
            "replacement_holdout_access_authorized",
            "source_switch_authorized",
            "automatic_model_promotion_authorized",
            "real_money_order_authorized",
            "live_trading_authorized",
        ):
            self.assertFalse(config["authority"][name])
        with self.assertRaisesRegex(DetailedHistoryAuthorityError, "V0.10 window"):
            require_execution_window(
                config, observed_at=datetime(2026, 9, 4, 1, 59, 59, tzinfo=UTC)
            )
        require_execution_window(
            config, observed_at=datetime(2026, 9, 4, 2, 0, 0, tzinfo=UTC)
        )

    def test_pre_window_script_skips_without_constructing_r2_or_reading_provider(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            for name in (
                "CLOUDFLARE_ACCOUNT_ID",
                "R2_BUCKET_NAME",
                "R2_ACCESS_KEY_ID",
                "R2_SECRET_ACCESS_KEY",
            ):
                env.pop(name, None)
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/run_binance_detailed_history.py"),
                    "--config",
                    str(CONFIG),
                    "--authority",
                    str(AUTHORITY),
                    "--mode",
                    "auto",
                    "--run-id",
                    "pre-window-test",
                    "--now-utc",
                    "2026-09-04T01:59:59Z",
                    "--output",
                    str(output),
                ],
                check=True,
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            report = json.loads(output.read_text())
        self.assertEqual(report["status"], "SKIPPED")
        self.assertEqual(report["provider_requests_performed"], 0)
        self.assertFalse(report["r2_access_performed"])


if __name__ == "__main__":
    unittest.main()
