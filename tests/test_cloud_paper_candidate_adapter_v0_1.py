from __future__ import annotations

import hashlib
import json
import unittest
from dataclasses import asdict, dataclass

from crypto_autopilot.paper.cloud_candidate_adapter_v0_1 import (
    CloudCandidateRegistryBlocked,
    select_qualified_candidates,
    validate_strategy_registry,
)
from crypto_autopilot.paper.cloud_genesis_v0_1 import initialize_cloud_paper_state
from crypto_autopilot.paper.live_v0_1 import LivePaperMarketFrame
from crypto_autopilot.paper.cloud_loop_v0_1 import run_cloud_step
from crypto_autopilot.paper.run_store_v0_1 import PaperRunObjectAlreadyExistsError
from crypto_autopilot.risk import plan_position_size

TICK_MS = 420_000
SYMBOL = "BTC_USDT_PERP"


def sha256(payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def family_report() -> dict[str, object]:
    return {
        "schema": "qookey-strategy-family-validation-report-v0.1",
        "family": "TREND_FOLLOWING",
        "category": "fixture",
        "state": "FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW",
        "reasons": ["synthetic_ci_fixture"],
        "coverage": {},
        "policy": {},
        "lineage": {},
        "authority": {
            "research_evidence_only": True,
            "family_registry_mutated": False,
            "strategy_edge_claimed": False,
            "provider_requests_performed": False,
            "r2_accessed": False,
            "holdout_accessed": False,
            "promotion_authority": 0,
            "position_sizing_authorized": False,
            "paper_execution_authorized": False,
            "trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
        "limitations": [],
    }


def qualified_registry(*, model_dependency: str = "NONE") -> dict[str, object]:
    report = family_report()
    implementation_sha = "a" * 64
    qualification = {
        "state": "PAPER_ELIGIBLE",
        "receipt_path": "research/receipts/test-only-candidate-qualification.json",
        "receipt_sha256": "b" * 64,
        "implementation_sha256": implementation_sha,
        "family_validation_report_sha256": sha256(report),
        "paper_execution_authorized": True,
        "holdout_accessed": False,
        "source_switch_authorized": False,
        "model_promotion_authorized": False,
        "real_money_order_authorized": False,
        "live_trading_authorized": False,
    }
    return {
        "schema": "qookey-cloud-paper-strategy-registry-v0.1",
        "status": "QUALIFIED_PAPER_STRATEGIES_AVAILABLE",
        "provider": "PIONEX_PUBLIC",
        "strategies": [{
            "strategy_id": "test-only-trend",
            "strategy_family": "TREND_FOLLOWING",
            "provider": "PIONEX_PUBLIC",
            "symbols": [SYMBOL],
            "regimes": ["ALT_EXPANSION"],
            "implementation_sha256": implementation_sha,
            "model_dependency": model_dependency,
            "qualification": qualification,
        }],
        "model_quality": "REJECT",
        "production_fixture_admission": False,
        "automatic_promotion": False,
    }


def market_and_candidate() -> tuple[dict[str, object], dict[str, object]]:
    report = family_report()
    route = {
        "symbol": SYMBOL,
        "status": "ROUTE_MATCHED",
        "regime_state": "ALT_EXPANSION",
        "matches": [{
            "family": "TREND_FOLLOWING",
            "direction": "LONG",
            "regime_state": "ALT_EXPANSION",
            "reasons": ["fixture route"],
        }],
    }
    evidence = {
        "provider": "PIONEX_PUBLIC",
        "interval": "60M",
        "first_bar_ms": 1,
        "last_bar_ms": 360_000,
        "bar_count": 240,
        "sha256": "c" * 64,
        "technical": {},
    }
    registry = qualified_registry()
    registration = registry["strategies"][0]
    qualification = registration["qualification"]
    entry, stop, target = 100.0, 99.0, 105.0
    sizing = plan_position_size(
        direction="LONG", equity_usd=10_000.0,
        entry_price=entry, stop_price=stop,
    )
    candidate = {
        "strategy_id": registration["strategy_id"],
        "symbol": SYMBOL,
        "strategy_family": "TREND_FOLLOWING",
        "direction": "LONG",
        "regime_state": "ALT_EXPANSION",
        "provider": "PIONEX_PUBLIC",
        "as_of_ms": evidence["last_bar_ms"],
        "market_evidence_sha256": evidence["sha256"],
        "strategy_route_sha256": sha256(route),
        "qualification_receipt_sha256": qualification["receipt_sha256"],
        "strategy_implementation_sha256": registration["implementation_sha256"],
        "entry_price": entry,
        "stop_price": stop,
        "family_validation_report": report,
        "position_sizing_plan": asdict(sizing),
    }
    market = {
        "schema": "qookey-cloud-paper-market-report-v0.1",
        "provider": "PIONEX_PUBLIC",
        "as_of_ms": TICK_MS,
        "market_status": "CAPTURED",
        "context_status": "AVAILABLE",
        "market_evidence": {SYMBOL: evidence},
        "routes": [route],
        "candidate_specs": [{"candidate": candidate, "target_price": target}],
        "provider_requests_performed": 0,
    }
    return market, candidate



@dataclass
class Receipt:
    replayed: bool = False


class MemoryStore:
    def __init__(self):
        self.objects: dict[tuple[str, str], dict[str, object]] = {}

    def get_json(self, kind, object_id):
        return self.objects.get((kind, object_id))

    def list_json_ids(self, kind):
        return tuple(sorted(
            object_id for stored_kind, object_id in self.objects
            if stored_kind == kind
        ))

    def put_json(self, kind, object_id, payload):
        key = (kind, object_id)
        if key in self.objects and self.objects[key] != dict(payload):
            raise ValueError("immutable collision")
        self.objects[key] = dict(payload)
        return Receipt()

    def put_json_if_absent(self, kind, object_id, payload):
        key = (kind, object_id)
        if key in self.objects:
            raise PaperRunObjectAlreadyExistsError("already claimed")
        self.objects[key] = dict(payload)
        return Receipt()


class NeverCalledFeed:
    def fetch_frame(self, *args, **kwargs):
        raise AssertionError("no existing position needs a lifecycle frame")


class CloudPaperCandidateAdapterTests(unittest.TestCase):
    def test_empty_production_registry_returns_normal_no_trade(self):
        registry = {
            "schema": "qookey-cloud-paper-strategy-registry-v0.1",
            "status": "EMPTY_NO_ELIGIBLE_STRATEGIES",
            "strategies": [],
            "model_quality": "REJECT",
            "production_fixture_admission": False,
            "automatic_promotion": False,
        }
        market, _ = market_and_candidate()
        market["candidate_specs"] = []
        selection = select_qualified_candidates(
            market, initialize_cloud_paper_state(), registry,
            allowed_base_assets=frozenset({"BTC"}),
        )
        self.assertEqual(selection.status, "NO_CANDIDATES")
        self.assertEqual(selection.reasons, ("NO_ELIGIBLE_STRATEGY",))
        self.assertEqual(selection.candidates, ())

    def test_qualified_output_binds_to_market_route_and_equity_then_enters_core(self):
        market, _ = market_and_candidate()
        state = initialize_cloud_paper_state()
        registry = qualified_registry()
        selection = select_qualified_candidates(
            market, state, registry, allowed_base_assets=frozenset({"BTC"}),
        )
        self.assertEqual(selection.status, "READY")
        self.assertEqual(selection.candidates, tuple(market["candidate_specs"]))

        store = MemoryStore()

        class CandidateFeed:
            def fetch_frame(self, symbol, *, tick_time_ms, since_ms):
                return LivePaperMarketFrame(
                    provider="PIONEX_PUBLIC", symbol=symbol,
                    time_ms=tick_time_ms, source_time_ms=tick_time_ms,
                    open=100.0, high=100.2, low=99.8, close=100.0,
                    mark_price=100.0, available_notional_usd=4_000.0,
                    provider_request_count=0, source_trade_count=0,
                )

        def candidate_supplier(report, paper_state):
            selected = select_qualified_candidates(
                report, paper_state, registry,
                allowed_base_assets=frozenset({"BTC"}),
            )
            report["execution_selection_status"] = selected.status
            report["execution_selection_reasons"] = list(selected.reasons)
            return selected.candidates

        result = run_cloud_step(
            tick_ms=TICK_MS,
            previous_slot=None,
            store=store,
            feed=CandidateFeed(),
            market_supplier=lambda: market,
            candidate_supplier=candidate_supplier,
            strategy_registry=registry,
            before_external=lambda: None,
        )
        self.assertEqual(result["state"], "COMMITTED")
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["account"]["open_position_count"], 1)
        self.assertEqual(result["account"]["initial_equity_usd"], 10_000.0)

    def test_market_evidence_mismatch_rejects_entire_basket(self):
        market, _ = market_and_candidate()
        candidate = market["candidate_specs"][0]["candidate"]
        candidate["market_evidence_sha256"] = "d" * 64
        selection = select_qualified_candidates(
            market, initialize_cloud_paper_state(), qualified_registry(),
            allowed_base_assets=frozenset({"BTC"}),
        )
        self.assertEqual(selection.status, "REVIEW_REQUIRED")
        self.assertEqual(selection.reasons, ("CANDIDATE_LINEAGE_MISMATCH",))
        self.assertEqual(selection.candidates, ())

    def test_core100_quality_reject_blocks_registry_before_external_work(self):
        registry = qualified_registry(model_dependency="CORE100")
        with self.assertRaisesRegex(
            CloudCandidateRegistryBlocked, "MODEL_QUALITY_GATE_NOT_PASSED",
        ):
            validate_strategy_registry(registry)

    def test_missing_paper_authority_rejects_registry(self):
        registry = qualified_registry()
        qualification = registry["strategies"][0]["qualification"]
        qualification["paper_execution_authorized"] = False
        with self.assertRaisesRegex(
            CloudCandidateRegistryBlocked, "STRATEGY_QUALIFICATION_NOT_AUTHORIZED",
        ):
            validate_strategy_registry(registry)

    def test_review_required_market_selection_is_persisted_and_replayable(self):
        store = MemoryStore()
        registry = {
            "schema": "qookey-cloud-paper-strategy-registry-v0.1",
            "status": "EMPTY_NO_ELIGIBLE_STRATEGIES",
            "strategies": [],
            "model_quality": "REJECT",
            "production_fixture_admission": False,
            "automatic_promotion": False,
        }
        market = {
            "provider_requests_performed": 0,
            "market_status": "REVIEW_REQUIRED",
            "context_status": "AVAILABLE",
            "execution_selection_status": "REVIEW_REQUIRED",
            "execution_selection_reasons": ["CANDIDATE_LINEAGE_MISMATCH"],
        }

        def run():
            return run_cloud_step(
                tick_ms=TICK_MS,
                previous_slot=None,
                store=store,
                feed=NeverCalledFeed(),
                market_supplier=lambda: dict(market),
                candidate_supplier=lambda report, state: (),
                strategy_registry=registry,
                before_external=lambda: None,
            )

        first = run()
        self.assertEqual(first["state"], "REVIEW_REQUIRED")
        self.assertIn("CANDIDATE_SELECTION_REVIEW_REQUIRED", first["reason_codes"])
        self.assertIn("CANDIDATE_LINEAGE_MISMATCH", first["reason_codes"])
        replay = run()
        self.assertEqual(replay["state"], "REPLAYED")
        self.assertEqual(replay["report"]["state"], "REVIEW_REQUIRED")
        self.assertEqual(replay["provider_requests_performed"], 0)


if __name__ == "__main__":
    unittest.main()
