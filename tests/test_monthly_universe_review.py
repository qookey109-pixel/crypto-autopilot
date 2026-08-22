from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from crypto_autopilot.binance_training_catalog import TrainingMarket, catalog_payload
from crypto_autopilot.monthly_universe_review import (
    build_monthly_universe_objects,
    build_monthly_universe_review,
)
from crypto_autopilot.training_quality import (
    TrainingQualityError,
    V0_3_BASELINE_EVIDENCE_SHA256,
    load_v0_5_authority_pair,
    validate_monthly_review_contract,
)
import scripts.review_binance_spot_universe_monthly as monthly_script
from scripts.review_binance_spot_universe_monthly import _previous_review


MONTHLY_NAMESPACE = "research/binance_spot/universe-review/v0.4"
LATEST_KEY = f"{MONTHLY_NAMESPACE}/latest.json"
ROOT = Path(__file__).resolve().parents[1]
V0_5_CONFIG_PATH = ROOT / "config/binance_spot_r2_training_governance_v0_5.json"


class PreviousReviewStore:
    def __init__(self, latest: dict, review_payload: bytes):
        self.objects = {
            LATEST_KEY: (json.dumps(latest, sort_keys=True) + "\n").encode(),
            str(latest["review_key"]): review_payload,
        }
        self.pointer_reads: list[str] = []
        self.verified_reads: list[str] = []

    def get_bytes_if_exists(self, key: str) -> bytes | None:
        self.pointer_reads.append(key)
        return self.objects.get(key)

    def get_bytes_verified(self, key: str, *, expected_sha256: str) -> bytes:
        self.verified_reads.append(key)
        payload = self.objects[key]
        if hashlib.sha256(payload).hexdigest() != expected_sha256:
            raise ValueError("fixture SHA-256 mismatch")
        return payload


def previous_review_fixture() -> tuple[dict, bytes, dict]:
    review = {
        "schema": "binance-spot-monthly-universe-review-v0.4",
        "status": "PASS",
        "mode": "RESEARCH_CATALOG_REVIEW_ONLY",
        "provider": "binance_spot",
        "market_count": 0,
        "market_snapshot": {},
        "authority": {
            "formal_delisting_determination_authorized": False,
            "historical_universe_membership_authorized": False,
            "formal_backtest_admission_authorized": False,
            "automatic_model_promotion_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
    review_payload = (json.dumps(review, sort_keys=True) + "\n").encode()
    latest = {
        "schema": "binance-spot-monthly-universe-review-latest-v0.4",
        "provider": "binance_spot",
        "run_id": "monthly-1",
        "review_key": f"{MONTHLY_NAMESPACE}/runs/run=monthly-1/universe-review.json",
        "review_sha256": hashlib.sha256(review_payload).hexdigest(),
    }
    config = {
        "provider": "binance_spot",
        "monthly_universe_review": {
            "namespace": MONTHLY_NAMESPACE,
            "latest_pointer_key": LATEST_KEY,
        },
    }
    return latest, review_payload, config


def market(symbol: str, asset_class: str = "crypto") -> dict:
    return {
        "symbol": symbol,
        "base_asset": symbol.removesuffix("USDT"),
        "quote_asset": "USDT",
        "asset_class": asset_class,
        "classification_method": "default_crypto"
        if asset_class == "crypto"
        else "trailing_B_heuristic",
        "classification_confidence": "default"
        if asset_class == "crypto"
        else "heuristic",
    }


def governed_catalog(
    count: int, *, retrieved_at_utc: str = "2026-08-23T00:00:00Z"
) -> dict:
    markets = [
        TrainingMarket(
            symbol=f"ASSET{index:04d}USDT",
            base_asset=f"ASSET{index:04d}",
            quote_asset="USDT",
            status="TRADING",
            market_type="spot",
            asset_class="crypto",
            classification_method="test_fixture",
            classification_confidence="high",
            is_spot_trading_allowed=True,
        )
        for index in range(count)
    ]
    return catalog_payload(
        markets,
        retrieved_at_utc=retrieved_at_utc,
        quotes=["USDT", "USDC"],
        all_quotes=False,
    )


def current_v05_governance() -> tuple[dict, dict]:
    config_payload = V0_5_CONFIG_PATH.read_bytes()
    config = json.loads(config_payload)
    _, governance_contract = load_v0_5_authority_pair(
        config,
        config_path=V0_5_CONFIG_PATH,
        config_payload=config_payload,
        repository_root=ROOT,
    )
    return config, governance_contract


def v05_previous_review_store(
    count: int = 600,
    *,
    mutate_latest: Callable[[dict], None] | None = None,
    mutate_catalog: Callable[[dict], None] | None = None,
    mutate_review: Callable[[dict], None] | None = None,
) -> MagicMock:
    config, governance_contract = current_v05_governance()
    generated_at_utc = "2026-08-23T00:00:00Z"
    catalog = governed_catalog(count, retrieved_at_utc=generated_at_utc)
    if mutate_catalog is not None:
        mutate_catalog(catalog)
    review = build_monthly_universe_review(
        catalog,
        previous_review=None,
        generated_at_utc=generated_at_utc,
        schema_version="v0.5",
    )
    review["governance"] = {
        "config": governance_contract,
        "comparison_baseline": {
            "source": "FROZEN_V0_3_PASS_RECEIPT",
            "reference": config["data_quality"]["baseline_evidence"],
            "sha256": V0_3_BASELINE_EVIDENCE_SHA256,
            "market_count": 748,
            "bootstrap_used": True,
        },
    }
    if mutate_review is not None:
        mutate_review(review)
    catalog_payload = (json.dumps(catalog, sort_keys=True) + "\n").encode()
    review_payload = (json.dumps(review, sort_keys=True) + "\n").encode()
    run_id = "monthly-v05-previous"
    run_prefix = (
        "research/binance_spot/universe-review/v0.5/" f"runs/run={run_id}"
    )
    catalog_key = f"{run_prefix}/market-catalog.json"
    review_key = (
        f"{run_prefix}/universe-review.json"
    )
    latest = {
        "schema": "binance-spot-monthly-universe-review-latest-v0.5",
        "provider": "binance_spot",
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "catalog_key": catalog_key,
        "catalog_sha256": hashlib.sha256(catalog_payload).hexdigest(),
        "review_key": review_key,
        "review_sha256": hashlib.sha256(review_payload).hexdigest(),
    }
    if mutate_latest is not None:
        mutate_latest(latest)
    objects = {
        catalog_key: catalog_payload,
        review_key: review_payload,
    }
    store = MagicMock()
    store.get_bytes_if_exists.return_value = (
        json.dumps(latest, sort_keys=True) + "\n"
    ).encode()
    store.verified_reads = []

    def verified_read(key: str, *, expected_sha256: str) -> bytes:
        store.verified_reads.append(key)
        payload = objects[key]
        if hashlib.sha256(payload).hexdigest() != expected_sha256:
            raise ValueError("fixture SHA-256 mismatch")
        return payload

    store.get_bytes_verified.side_effect = verified_read
    store.fixture_latest = latest
    store.fixture_catalog = catalog
    store.fixture_review = review
    store.fixture_governance_contract = governance_contract
    return store


class MonthlyUniverseReviewTests(unittest.TestCase):
    def test_changes_are_reported_without_claiming_delisting_or_membership(self) -> None:
        previous = build_monthly_universe_review(
            {"markets": [market("OLDUSDT"), market("TSLABUSDT", "tokenized_stock_candidate")]},
            previous_review=None,
            generated_at_utc="2026-07-01T00:00:00Z",
        )
        current = build_monthly_universe_review(
            {"markets": [market("NEWUSDT"), market("TSLABUSDT", "crypto")]},
            previous_review=previous,
            generated_at_utc="2026-08-01T00:00:00Z",
        )
        self.assertEqual(current["added_since_previous_monthly_review"], ["NEWUSDT"])
        self.assertEqual(current["absent_from_current_active_catalog"], ["OLDUSDT"])
        self.assertEqual(len(current["classification_changes"]), 1)
        survivorship = current["survivorship_bias_review"]
        self.assertEqual(survivorship["status"], "REVIEW_REQUIRED")
        self.assertFalse(survivorship["absence_from_current_catalog_is_delisting_proof"])
        self.assertFalse(current["authority"]["historical_universe_membership_authorized"])

    def test_latest_pointer_is_last(self) -> None:
        config = {
            "monthly_universe_review": {
                "namespace": "research/binance/universe/v0.4",
                "latest_pointer_key": "research/binance/universe/v0.4/latest.json",
            }
        }
        objects = build_monthly_universe_objects(
            config=config,
            run_id="monthly-1",
            catalog=b"{}\n",
            review=b"{}\n",
            generated_at_utc="2026-08-01T00:00:00Z",
        )
        self.assertEqual([item.role for item in objects], [
            "monthly_catalog",
            "monthly_universe_review",
            "latest_pointer",
        ])
        self.assertFalse(objects[-1].immutable)

    def test_v05_uses_distinct_review_and_pointer_schemas(self) -> None:
        config = {
            "monthly_universe_review": {
                "schema_version": "v0.5",
                "namespace": "research/binance/universe/v0.5",
                "latest_pointer_key": "research/binance/universe/v0.5/latest.json",
            }
        }
        review = build_monthly_universe_review(
            {"markets": [market("BTCUSDT")]},
            previous_review=None,
            generated_at_utc="2026-08-23T00:00:00Z",
            schema_version="v0.5",
        )
        payload = (json.dumps(review) + "\n").encode()
        objects = build_monthly_universe_objects(
            config=config,
            run_id="monthly-v05",
            catalog=b"{}\n",
            review=payload,
            generated_at_utc="2026-08-23T00:00:00Z",
        )
        self.assertEqual(review["schema"], "binance-spot-monthly-universe-review-v0.5")
        latest = json.loads(objects[-1].payload)
        self.assertEqual(
            latest["schema"],
            "binance-spot-monthly-universe-review-latest-v0.5",
        )

    def test_v05_current_review_contract_requires_exact_governance_evidence(self) -> None:
        catalog = governed_catalog(600)
        governance_contract = {
            "status": "PASS",
            "config_version": "0.5.0",
            "config_sha256": "a" * 64,
            "authority_receipt": "authority.json",
            "provider": "binance_spot",
        }
        comparison_baseline = {
            "source": "FROZEN_V0_3_PASS_RECEIPT",
            "reference": "baseline.json",
            "sha256": "b" * 64,
            "market_count": 748,
            "bootstrap_used": True,
        }
        review = build_monthly_universe_review(
            catalog,
            previous_review=None,
            generated_at_utc="2026-08-23T00:00:00Z",
            schema_version="v0.5",
        )
        review["governance"] = {
            "config": governance_contract,
            "comparison_baseline": comparison_baseline,
        }
        evidence = validate_monthly_review_contract(
            review,
            catalog=catalog,
            previous_review=None,
            governance_contract=governance_contract,
            comparison_baseline=comparison_baseline,
            expected_generated_at_utc="2026-08-23T00:00:00Z",
        )
        self.assertEqual(evidence["status"], "PASS")

        for field in ("governance", "authority"):
            with self.subTest(field=field):
                invalid = copy.deepcopy(review)
                if field == "governance":
                    invalid["governance"]["comparison_baseline"]["market_count"] = 1
                else:
                    invalid["authority"]["live_trading_authorized"] = True
                with self.assertRaises(TrainingQualityError):
                    validate_monthly_review_contract(
                        invalid,
                        catalog=catalog,
                        previous_review=None,
                        governance_contract=governance_contract,
                        comparison_baseline=comparison_baseline,
                        expected_generated_at_utc="2026-08-23T00:00:00Z",
                    )

    def test_previous_review_accepts_only_verified_monthly_review_object(self) -> None:
        latest, review_payload, config = previous_review_fixture()
        store = PreviousReviewStore(latest, review_payload)
        previous = _previous_review(store, config)
        self.assertEqual(previous["schema"], "binance-spot-monthly-universe-review-v0.4")
        self.assertEqual(store.pointer_reads, [LATEST_KEY])
        self.assertEqual(store.verified_reads, [latest["review_key"]])

    def test_previous_review_rejects_raw_holdout_and_other_namespaces_before_read(self) -> None:
        latest, review_payload, config = previous_review_fixture()
        invalid_keys = (
            f"{MONTHLY_NAMESPACE}/raw/provider-response.json",
            "holdout/binance_spot/replacement/universe-review.json",
            "research/binance_spot/other/v0.4/runs/run=monthly-1/universe-review.json",
        )
        for invalid_key in invalid_keys:
            with self.subTest(review_key=invalid_key):
                invalid = {**latest, "review_key": invalid_key}
                store = PreviousReviewStore(invalid, review_payload)
                with self.assertRaisesRegex(ValueError, "outside the authorized run namespace"):
                    _previous_review(store, config)
                self.assertEqual(store.verified_reads, [])

    def test_previous_review_rejects_wrong_pointer_schema_or_provider_before_read(self) -> None:
        latest, review_payload, config = previous_review_fixture()
        for field, value, message in (
            ("schema", "wrong-schema", "pointer schema mismatch"),
            ("provider", "pionex", "pointer provider mismatch"),
        ):
            with self.subTest(field=field):
                invalid = {**latest, field: value}
                store = PreviousReviewStore(invalid, review_payload)
                with self.assertRaisesRegex(ValueError, message):
                    _previous_review(store, config)
                self.assertEqual(store.verified_reads, [])

    def test_previous_review_rejects_malformed_or_mismatched_sha(self) -> None:
        latest, review_payload, config = previous_review_fixture()
        malformed = {**latest, "review_sha256": "not-a-sha256"}
        malformed_store = PreviousReviewStore(malformed, review_payload)
        with self.assertRaisesRegex(ValueError, "SHA-256 is invalid"):
            _previous_review(malformed_store, config)
        self.assertEqual(malformed_store.verified_reads, [])

        mismatched = {**latest, "review_sha256": "0" * 64}
        mismatched_store = PreviousReviewStore(mismatched, review_payload)
        with self.assertRaisesRegex(ValueError, "fixture SHA-256 mismatch"):
            _previous_review(mismatched_store, config)

    def test_previous_review_rejects_wrong_review_schema_or_provider(self) -> None:
        latest, _, config = previous_review_fixture()
        for field, value, message in (
            ("schema", "wrong-schema", "review schema mismatch"),
            ("provider", "pionex", "review provider mismatch"),
        ):
            with self.subTest(field=field):
                review = {
                    "schema": "binance-spot-monthly-universe-review-v0.4",
                    "status": "PASS",
                    "mode": "RESEARCH_CATALOG_REVIEW_ONLY",
                    "provider": "binance_spot",
                    "market_count": 0,
                    "market_snapshot": {},
                    "authority": {
                        "formal_delisting_determination_authorized": False,
                        "historical_universe_membership_authorized": False,
                        "formal_backtest_admission_authorized": False,
                        "automatic_model_promotion_authorized": False,
                        "automatic_trade_plan_authorized": False,
                        "real_money_order_authorized": False,
                        "live_trading_authorized": False,
                    },
                    field: value,
                }
                payload = (json.dumps(review, sort_keys=True) + "\n").encode()
                pointer = {**latest, "review_sha256": hashlib.sha256(payload).hexdigest()}
                store = PreviousReviewStore(pointer, payload)
                with self.assertRaisesRegex(ValueError, message):
                    _previous_review(store, config)

    def test_v05_previous_review_reads_bound_catalog_and_review(self) -> None:
        config, governance_contract = current_v05_governance()
        store = v05_previous_review_store()
        access_checks = []
        previous = _previous_review(
            store,
            config,
            governance_contract=governance_contract,
            before_access=lambda: access_checks.append("checked"),
        )
        self.assertEqual(previous["schema"], "binance-spot-monthly-universe-review-v0.5")
        self.assertEqual(previous["market_count"], 600)
        self.assertEqual(previous["_verified_catalog_key"], store.fixture_latest["catalog_key"])
        self.assertEqual(previous["_verified_review_key"], store.fixture_latest["review_key"])
        self.assertEqual(
            store.verified_reads,
            [store.fixture_latest["catalog_key"], store.fixture_latest["review_key"]],
        )
        self.assertEqual(access_checks, ["checked", "checked", "checked"])

    def test_v05_previous_review_rejects_cross_object_and_governance_drift(self) -> None:
        config, governance_contract = current_v05_governance()
        cases = (
            (
                "catalog_key",
                {
                    "mutate_latest": lambda latest: latest.__setitem__(
                        "catalog_key", "holdout/binance_spot/catalog.json"
                    )
                },
                "catalog key is outside",
            ),
            (
                "catalog_sha",
                {
                    "mutate_latest": lambda latest: latest.__setitem__(
                        "catalog_sha256", "not-a-sha"
                    )
                },
                "catalog SHA-256 is invalid",
            ),
            (
                "catalog_contract",
                {
                    "mutate_catalog": lambda catalog: catalog.__setitem__(
                        "provider", "pionex"
                    )
                },
                "catalog provider or market type mismatch",
            ),
            (
                "generated_timestamp",
                {
                    "mutate_latest": lambda latest: latest.__setitem__(
                        "generated_at_utc", "2026-08-23T00:00:01Z"
                    )
                },
                "timestamps do not match",
            ),
            (
                "snapshot",
                {
                    "mutate_review": lambda review: review[
                        "market_snapshot"
                    ][next(iter(review["market_snapshot"]))].__setitem__(
                        "classification_confidence", "drift"
                    )
                },
                "does not match its catalog",
            ),
            (
                "asset_counts",
                {
                    "mutate_review": lambda review: review.__setitem__(
                        "asset_class_counts", {"crypto": 1}
                    )
                },
                "does not match its catalog",
            ),
            (
                "quote_counts",
                {
                    "mutate_review": lambda review: review.__setitem__(
                        "quote_asset_counts", {"USDT": 1}
                    )
                },
                "does not match its catalog",
            ),
            (
                "interpretation",
                {
                    "mutate_review": lambda review: review.__setitem__(
                        "interpretation", "unsafe interpretation"
                    )
                },
                "does not match its catalog",
            ),
            (
                "governance_config",
                {
                    "mutate_review": lambda review: review["governance"][
                        "config"
                    ].__setitem__("provider", "pionex")
                },
                "governance config mismatch",
            ),
            (
                "comparison_baseline",
                {
                    "mutate_review": lambda review: review["governance"][
                        "comparison_baseline"
                    ].__setitem__("bootstrap_used", False)
                },
                "frozen comparison baseline mismatch",
            ),
        )
        for name, store_kwargs, message in cases:
            with self.subTest(name=name):
                store = v05_previous_review_store(**store_kwargs)
                with self.assertRaisesRegex(ValueError, message):
                    _previous_review(
                        store,
                        config,
                        governance_contract=governance_contract,
                    )

    def test_first_v05_monthly_review_uses_frozen_count_without_fake_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.json"
            catalog_path.write_text(json.dumps(governed_catalog(600)) + "\n")
            argv = [
                "review_binance_spot_universe_monthly.py",
                "--config",
                "config/binance_spot_r2_training_governance_v0_5.json",
                "--catalog",
                str(catalog_path),
                "--event-name",
                "workflow_dispatch",
                "--activation-mode",
                "ONE_TIME_MANUAL_WORKFLOW_DISPATCH",
                "--review-output",
                str(root / "review.json"),
                "--receipt-output",
                str(root / "receipt.json"),
                "--dry-run",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(monthly_script, "R2Store") as r2_store,
            ):
                self.assertEqual(monthly_script.main(), 0)
            r2_store.assert_not_called()
            review = json.loads((root / "review.json").read_text())
            receipt = json.loads((root / "receipt.json").read_text())
            self.assertTrue(review["baseline_created"])
            self.assertEqual(review["added_since_previous_monthly_review"], [])
            self.assertEqual(review["governance"]["config"]["status"], "PASS")
            self.assertEqual(receipt["monthly_review_contract"]["status"], "PASS")
            self.assertEqual(receipt["comparison_baseline"]["market_count"], 748)
            self.assertTrue(receipt["comparison_baseline"]["bootstrap_used"])

    def test_first_manual_activation_is_allowed_without_previous_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.json"
            catalog_path.write_text(json.dumps(governed_catalog(600)) + "\n")
            argv = [
                "review_binance_spot_universe_monthly.py",
                "--config",
                "config/binance_spot_r2_training_governance_v0_5.json",
                "--catalog",
                str(catalog_path),
                "--event-name",
                "workflow_dispatch",
                "--activation-mode",
                "ONE_TIME_MANUAL_WORKFLOW_DISPATCH",
                "--review-output",
                str(root / "review.json"),
                "--receipt-output",
                str(root / "receipt.json"),
            ]
            store = MagicMock()
            store.get_bytes_if_exists.return_value = None
            publish_result = {
                "status": "PASS",
                "stage": "BINANCE_SPOT_MONTHLY_UNIVERSE_REVIEW_PUBLISHED_V0_5",
                "objects": [],
                "r2_writes_performed": True,
            }
            with (
                patch.object(sys, "argv", argv),
                patch.dict(
                    os.environ,
                    {
                        "CLOUDFLARE_ACCOUNT_ID": "account",
                        "R2_BUCKET_NAME": "bucket",
                        "R2_ACCESS_KEY_ID": "key",
                        "R2_SECRET_ACCESS_KEY": "secret",
                    },
                ),
                patch.object(monthly_script, "R2Store", return_value=store),
                patch.object(
                    monthly_script,
                    "utc_now",
                    return_value=datetime(2026, 8, 23, tzinfo=UTC),
                ),
                patch.object(
                    monthly_script,
                    "publish_online_objects",
                    return_value=publish_result,
                ) as publish,
            ):
                self.assertEqual(monthly_script.main(), 0)
            publish.assert_called_once()
            receipt = json.loads((root / "receipt.json").read_text())
            self.assertEqual(
                receipt["execution_route"]["activation_mode"],
                "ONE_TIME_MANUAL_WORKFLOW_DISPATCH",
            )
            self.assertTrue(receipt["execution_route"]["manual_activation"])

    def test_second_manual_activation_is_rejected_before_publish(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.json"
            catalog_path.write_text(json.dumps(governed_catalog(600)) + "\n")
            argv = [
                "review_binance_spot_universe_monthly.py",
                "--config",
                "config/binance_spot_r2_training_governance_v0_5.json",
                "--catalog",
                str(catalog_path),
                "--event-name",
                "workflow_dispatch",
                "--activation-mode",
                "ONE_TIME_MANUAL_WORKFLOW_DISPATCH",
                "--review-output",
                str(root / "review.json"),
                "--receipt-output",
                str(root / "receipt.json"),
            ]
            store = v05_previous_review_store()
            with (
                patch.object(sys, "argv", argv),
                patch.dict(
                    os.environ,
                    {
                        "CLOUDFLARE_ACCOUNT_ID": "account",
                        "R2_BUCKET_NAME": "bucket",
                        "R2_ACCESS_KEY_ID": "key",
                        "R2_SECRET_ACCESS_KEY": "secret",
                    },
                ),
                patch.object(monthly_script, "R2Store", return_value=store),
                patch.object(
                    monthly_script,
                    "utc_now",
                    return_value=datetime(2026, 8, 23, tzinfo=UTC),
                ),
                patch.object(monthly_script, "publish_online_objects") as publish,
                self.assertRaisesRegex(
                    TrainingQualityError,
                    "manual activation already completed",
                ),
            ):
                monthly_script.main()
            publish.assert_not_called()
            store.put_bytes.assert_not_called()

    def test_schedule_cannot_create_the_required_initial_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.json"
            catalog_path.write_text(json.dumps(governed_catalog(600)) + "\n")
            argv = [
                "review_binance_spot_universe_monthly.py",
                "--config",
                "config/binance_spot_r2_training_governance_v0_5.json",
                "--catalog",
                str(catalog_path),
                "--event-name",
                "schedule",
                "--activation-mode",
                "SCHEDULED_REVIEW",
                "--review-output",
                str(root / "review.json"),
                "--receipt-output",
                str(root / "receipt.json"),
            ]
            store = MagicMock()
            store.get_bytes_if_exists.return_value = None
            with (
                patch.object(sys, "argv", argv),
                patch.dict(
                    os.environ,
                    {
                        "CLOUDFLARE_ACCOUNT_ID": "account",
                        "R2_BUCKET_NAME": "bucket",
                        "R2_ACCESS_KEY_ID": "key",
                        "R2_SECRET_ACCESS_KEY": "secret",
                    },
                ),
                patch.object(monthly_script, "R2Store", return_value=store),
                patch.object(
                    monthly_script,
                    "utc_now",
                    return_value=datetime(2026, 8, 23, tzinfo=UTC),
                ),
                patch.object(monthly_script, "publish_online_objects") as publish,
                self.assertRaisesRegex(
                    TrainingQualityError,
                    "baseline requires the authorized manual activation",
                ),
            ):
                monthly_script.main()
            publish.assert_not_called()

    def test_malformed_present_v05_evidence_never_falls_back_or_publishes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.json"
            catalog_path.write_text(json.dumps(governed_catalog(600)) + "\n")
            argv = [
                "review_binance_spot_universe_monthly.py",
                "--config",
                "config/binance_spot_r2_training_governance_v0_5.json",
                "--catalog",
                str(catalog_path),
                "--event-name",
                "schedule",
                "--activation-mode",
                "SCHEDULED_REVIEW",
                "--review-output",
                str(root / "review.json"),
                "--receipt-output",
                str(root / "receipt.json"),
            ]
            store = v05_previous_review_store(
                mutate_catalog=lambda catalog: catalog.__setitem__(
                    "provider", "pionex"
                )
            )
            with (
                patch.object(sys, "argv", argv),
                patch.dict(
                    os.environ,
                    {
                        "CLOUDFLARE_ACCOUNT_ID": "account",
                        "R2_BUCKET_NAME": "bucket",
                        "R2_ACCESS_KEY_ID": "key",
                        "R2_SECRET_ACCESS_KEY": "secret",
                    },
                ),
                patch.object(monthly_script, "R2Store", return_value=store),
                patch.object(
                    monthly_script,
                    "utc_now",
                    return_value=datetime(2026, 8, 23, tzinfo=UTC),
                ),
                patch.object(monthly_script, "publish_online_objects") as publish,
                self.assertRaisesRegex(
                    TrainingQualityError,
                    "catalog provider or market type mismatch",
                ),
            ):
                monthly_script.main()
            publish.assert_not_called()
            store.put_bytes.assert_not_called()

    def test_scheduled_route_keeps_running_and_passes_fresh_stop_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.json"
            catalog_path.write_text(json.dumps(governed_catalog(600)) + "\n")
            argv = [
                "review_binance_spot_universe_monthly.py",
                "--config",
                "config/binance_spot_r2_training_governance_v0_5.json",
                "--catalog",
                str(catalog_path),
                "--event-name",
                "schedule",
                "--activation-mode",
                "SCHEDULED_REVIEW",
                "--review-output",
                str(root / "review.json"),
                "--receipt-output",
                str(root / "receipt.json"),
            ]
            store = v05_previous_review_store()
            publish_result = {
                "status": "PASS",
                "stage": "BINANCE_SPOT_MONTHLY_UNIVERSE_REVIEW_PUBLISHED_V0_5",
                "objects": [],
                "r2_writes_performed": True,
            }
            with (
                patch.object(sys, "argv", argv),
                patch.dict(
                    os.environ,
                    {
                        "CLOUDFLARE_ACCOUNT_ID": "account",
                        "R2_BUCKET_NAME": "bucket",
                        "R2_ACCESS_KEY_ID": "key",
                        "R2_SECRET_ACCESS_KEY": "secret",
                    },
                ),
                patch.object(monthly_script, "R2Store", return_value=store),
                patch.object(
                    monthly_script,
                    "utc_now",
                    return_value=datetime(2026, 8, 23, tzinfo=UTC),
                ),
                patch.object(
                    monthly_script,
                    "publish_online_objects",
                    return_value=publish_result,
                ) as publish,
            ):
                self.assertEqual(monthly_script.main(), 0)
            publish.assert_called_once()
            fresh_stop_guard = publish.call_args.kwargs["before_write"]
            self.assertTrue(callable(fresh_stop_guard))
            with (
                patch.object(
                    monthly_script,
                    "utc_now",
                    return_value=datetime(2026, 8, 27, tzinfo=UTC),
                ),
                self.assertRaisesRegex(
                    TrainingQualityError,
                    "online write window is closed",
                ),
            ):
                fresh_stop_guard()

    def test_unsafe_current_monthly_review_stops_before_r2_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = governed_catalog(600)
            catalog_path = root / "catalog.json"
            catalog_path.write_text(json.dumps(catalog) + "\n")
            unsafe_review = build_monthly_universe_review(
                catalog,
                previous_review=None,
                generated_at_utc="2026-08-23T00:00:00Z",
                schema_version="v0.5",
            )
            unsafe_review["authority"]["live_trading_authorized"] = True
            argv = [
                "review_binance_spot_universe_monthly.py",
                "--config",
                "config/binance_spot_r2_training_governance_v0_5.json",
                "--catalog",
                str(catalog_path),
                "--event-name",
                "workflow_dispatch",
                "--activation-mode",
                "ONE_TIME_MANUAL_WORKFLOW_DISPATCH",
                "--review-output",
                str(root / "review.json"),
                "--receipt-output",
                str(root / "receipt.json"),
            ]
            store = MagicMock()
            store.get_bytes_if_exists.return_value = None
            with (
                patch.object(sys, "argv", argv),
                patch.dict(
                    os.environ,
                    {
                        "CLOUDFLARE_ACCOUNT_ID": "account",
                        "R2_BUCKET_NAME": "bucket",
                        "R2_ACCESS_KEY_ID": "key",
                        "R2_SECRET_ACCESS_KEY": "secret",
                    },
                ),
                patch.object(monthly_script, "R2Store", return_value=store),
                patch.object(
                    monthly_script,
                    "utc_now",
                    return_value=datetime(2026, 8, 23, tzinfo=UTC),
                ),
                patch.object(
                    monthly_script,
                    "build_monthly_universe_review",
                    return_value=unsafe_review,
                ),
                patch.object(monthly_script, "publish_online_objects") as publish,
                self.assertRaisesRegex(
                    TrainingQualityError,
                    "unsafe current monthly review authority",
                ),
            ):
                monthly_script.main()
            publish.assert_not_called()
            store.put_bytes.assert_not_called()

    def test_first_v05_monthly_market_collapse_stops_before_publish(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.json"
            catalog_path.write_text(json.dumps(governed_catalog(550)) + "\n")
            argv = [
                "review_binance_spot_universe_monthly.py",
                "--config",
                "config/binance_spot_r2_training_governance_v0_5.json",
                "--catalog",
                str(catalog_path),
                "--event-name",
                "workflow_dispatch",
                "--activation-mode",
                "ONE_TIME_MANUAL_WORKFLOW_DISPATCH",
                "--review-output",
                str(root / "review.json"),
                "--receipt-output",
                str(root / "receipt.json"),
            ]
            store = MagicMock()
            store.get_bytes_if_exists.return_value = None
            with (
                patch.object(sys, "argv", argv),
                patch.dict(
                    os.environ,
                    {
                        "CLOUDFLARE_ACCOUNT_ID": "account",
                        "R2_BUCKET_NAME": "bucket",
                        "R2_ACCESS_KEY_ID": "key",
                        "R2_SECRET_ACCESS_KEY": "secret",
                    },
                ),
                patch.object(monthly_script, "R2Store", return_value=store),
                patch.object(
                    monthly_script,
                    "utc_now",
                    return_value=datetime(2026, 8, 23, tzinfo=UTC),
                ),
                patch.object(monthly_script, "publish_online_objects") as publish,
                self.assertRaisesRegex(
                    ValueError,
                    "CATALOG_MARKET_COUNT_COLLAPSED_VS_PREVIOUS",
                ),
            ):
                monthly_script.main()
            publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
