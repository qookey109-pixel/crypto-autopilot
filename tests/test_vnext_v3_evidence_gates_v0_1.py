"""VNext V3 provenance guard RED tests: must fail before production code exists."""
from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("delivery_v3", ROOT / "scripts/build_delivery_overview.py")
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)


def observed_fixture() -> dict[str, object]:
    return {
        "schema": "qookey-vnext-shadow-observed-metadata-v0.1",
        "metadata_checked_date_utc": "2026-10-25",
        "source": "GITHUB_ACTIONS_EXISTING_NATURAL_RUN_METADATA_ONLY",
        "run": {
            "id": 40162915838,
            "attempt": 1,
            "event": "schedule",
            "created_at_utc": "2026-10-25T04:43:22Z",
            "head_sha": "944895170f80af21e8f9b544ec42b279c45c0d6e",
            "conclusion": "success",
        },
        "artifact": {
            "id": 12586364157,
            "name": "prospective-shadow-v0-1-40162915838-1",
            "created_at_utc": "2026-10-25T04:43:42Z",
            "digest": "sha256:191fa626fbddd7f4a2a639618157605ab382a343936584fa2755ec2f6c08f03d",
            "size_bytes": 31975,
            "expired": False,
        },
        "assurance": {
            "original_zip_content_authenticated": False,
            "source_candle_timestamp_authenticated": False,
            "feature_coverage_authenticated": False,
            "production_eligibility_proven": False,
            "additional_verified_shadow_batch": False,
            "paper_cycle_executed": False,
        },
    }


def latest_observed_fixture() -> dict[str, object]:
    return delivery.read_json(delivery.SHADOW_OBSERVED_METADATA)


class VNextV3ProvenanceTests(unittest.TestCase):
    def test_newest_natural_shadow_run_keeps_archive_verification_unknown(self):
        new = latest_observed_fixture()
        panel = delivery.observed_shadow_metadata_panel(new, verified_count=16)
        self.assertEqual(new["run"]["id"], 40196502726)
        self.assertEqual(new["artifact"]["id"], 12599619291)
        self.assertEqual(new["run"]["created_at_utc"], "2026-10-25T13:11:49Z")
        self.assertEqual(new["artifact"]["created_at_utc"], "2026-10-25T13:12:06Z")
        self.assertIn("40196502726", panel)
        self.assertIn("12599619291", panel)
        self.assertIn("2026-10-25T13:11:49Z", panel)
        self.assertIn("2026-10-25T13:12:06Z", panel)
        self.assertIn("原始 ZIP 內容：尚未驗證", panel)
        self.assertIn("16/21", panel)
        self.assertIn("來源 K 線可用時間：UNKNOWN", panel)
        self.assertNotIn("正式 NO_TRADE", panel)
        self.assertNotIn("17/21", panel)
        # The already-audited older source is intentionally kept separate.
        old = delivery.authenticated_shadow_singleton_panel(
            delivery.read_json(delivery.SHADOW_SINGLETON_RECEIPT),
            prior_sixteen_verified=True,
        )
        self.assertIn("40162915838", old)
        self.assertNotIn("40196502726", old)

    def test_latest_observation_identity_pairing_and_times_fail_closed(self):
        newest = latest_observed_fixture()
        for field, path, invalid in (
            ("run_sha", ("run", "head_sha"), "944895170f80af21e8f9b544ec42b279c45c0d6e"),
            ("run_time", ("run", "created_at_utc"), "2026-10-25T04:43:22Z"),
            ("artifact_id", ("artifact", "id"), 12586364157),
            ("artifact_time", ("artifact", "created_at_utc"), "2026-10-25T04:43:42Z"),
            ("digest", ("artifact", "digest"), "sha256:191fa626fbddd7f4a2a639618157605ab382a343936584fa2755ec2f6c08f03d"),
            ("fake_zip_claim", ("assurance", "original_zip_content_authenticated"), True),
        ):
            changed = copy.deepcopy(newest)
            changed[path[0]][path[1]] = invalid
            with self.subTest(field=field):
                panel = delivery.observed_shadow_metadata_panel(changed, verified_count=16)
                self.assertIn("UNKNOWN", panel)
                self.assertNotIn("40196502726", panel)

    def test_latest_observed_run_is_not_a_seventeenth_authenticated_shadow_batch(self):
        panel = delivery.observed_shadow_metadata_panel(observed_fixture(), verified_count=16)
        self.assertIn("40162915838", panel)
        self.assertIn("12586364157", panel)
        self.assertIn("2026-10-25T04:43:22Z", panel)
        self.assertIn("2026-10-25T04:43:42Z", panel)
        self.assertIn("原始 ZIP 內容：尚未驗證", panel)
        self.assertIn("來源 K 線可用時間：UNKNOWN", panel)
        self.assertIn("16/21", panel)
        self.assertIn('href="https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40162915838"', panel)
        self.assertNotIn("17/21", panel)
        self.assertNotIn("正式 NO_TRADE", panel)

    def test_observed_artifact_metadata_alone_cannot_claim_verified_count(self):
        view = delivery.observed_shadow_metadata_panel(observed_fixture())
        self.assertIn("已驗證批次 UNKNOWN", view)
        self.assertNotIn("16/21", view)
        view = delivery.observed_shadow_metadata_panel(observed_fixture(), verified_count=15)
        self.assertIn("已驗證批次 UNKNOWN", view)
        self.assertNotIn("16/21", view)

    def test_new_original_zip_audit_is_explicitly_isolated_not_continuous(self):
        receipt = delivery.read_json(delivery.SHADOW_SINGLETON_RECEIPT)
        card = delivery.authenticated_shadow_singleton_panel(
            receipt, prior_sixteen_verified=True
        )
        self.assertIn("原始 ZIP 獨立驗證：PASS（單批）", card)
        self.assertIn("2026-10-25T04:43:38.396000Z", card)
        self.assertIn("40183609493", card)
        self.assertIn("5 市場 × 各 240 根", card)
        self.assertIn("這不是連續 17/21", card)
        self.assertIn("跨批重疊、因果特徵覆蓋與正式 PAPER 資格：UNKNOWN", card)
        self.assertNotIn("已完成正式 PAPER", card)
        isolated = delivery.authenticated_shadow_singleton_panel(
            receipt, prior_sixteen_verified=False
        )
        self.assertIn("歷史批次稽核狀態 UNKNOWN", isolated)
        self.assertNotIn("既有 16 批已通過", isolated)

    def test_original_zip_receipt_mutations_fail_closed(self):
        original = delivery.read_json(delivery.SHADOW_SINGLETON_RECEIPT)
        for key, modified in (
            ("audit_job_conclusion", "failure"),
            ("original_zip_sha256", "a" * 64),
            ("source_run_id", 1),
            ("verified_governed_market_count", 0),
            ("adjacent_pair_overlap_verified", True),
            ("multi_timeframe_feature_coverage_verified", True),
            ("live_paper_cycle_executed", True),
            ("provider_requests_by_audit", None),
            ("audit_pr_state", "OPEN"),
        ):
            mutated = copy.deepcopy(original)
            mutated[key] = modified
            with self.subTest(key=key):
                html = delivery.authenticated_shadow_singleton_panel(
                    mutated, prior_sixteen_verified=True
                )
                self.assertIn("稽核：UNKNOWN", html)
                self.assertNotIn("獨立驗證：PASS", html)

    def test_decision_trace_binds_archived_source_and_production_state(self):
        receipt = delivery.read_json(delivery.SHADOW_SINGLETON_RECEIPT)
        trace = delivery.shadow_decision_lineage_panel(
            receipt, prior_sixteen_verified=True, production_disabled=True
        )
        self.assertIn("Decision Trace · 證據到正式決策", trace)
        self.assertIn("16/21", trace)
        self.assertIn("非連續第十七份獨立 ZIP", trace)
        self.assertIn("40162915838", trace)
        self.assertIn("12586364157", trace)
        self.assertIn("40183609493", trace)
        self.assertIn("2026-10-25T04:43:38.396000Z", trace)
        self.assertIn("來源 K 線可用時間：UNKNOWN", trace)
        self.assertIn("15M／4H：UNKNOWN", trace)
        self.assertIn("策略准入：REJECT", trace)
        self.assertIn("正式 PAPER：NOT_RUN（非 NO_TRADE）", trace)
        self.assertNotIn("成交紀錄", trace)

    def test_decision_trace_rejects_tampered_source_and_unknown_status(self):
        original = delivery.read_json(delivery.SHADOW_SINGLETON_RECEIPT)
        mutated = copy.deepcopy(original)
        mutated["audit_job_conclusion"] = "failure"
        for row in (None, mutated):
            with self.subTest(receipt=row):
                trace = delivery.shadow_decision_lineage_panel(
                    row, prior_sixteen_verified=True, production_disabled=True
                )
                self.assertIn("原始 ZIP 稽核：UNKNOWN", trace)
                self.assertNotIn("2026-10-25T04:43:38.396000Z", trace)
                self.assertNotIn("40183609493", trace)
                self.assertNotIn("已驗證的獨立 ZIP", trace)
        untrusted_history = delivery.shadow_decision_lineage_panel(
            original, prior_sixteen_verified=False, production_disabled=False
        )
        self.assertIn("歷史暖機：UNKNOWN", untrusted_history)
        self.assertIn("策略准入：UNKNOWN", untrusted_history)
        self.assertIn("正式 PAPER：UNKNOWN", untrusted_history)
        self.assertNotIn("正式 PAPER：NOT_RUN", untrusted_history)

    def test_false_authority_or_invalid_metadata_falls_back_to_unknown(self):
        fixture = observed_fixture()
        mutants = [
            lambda obj: obj["assurance"].update(original_zip_content_authenticated=True),
            lambda obj: obj["assurance"].update(additional_verified_shadow_batch=True),
            lambda obj: obj["run"].update(event="workflow_dispatch"),
            lambda obj: obj["run"].update(created_at_utc="2026-10-25"),
            lambda obj: obj["run"].update(head_sha="not-sha"),
            lambda obj: obj["artifact"].update(digest="sha256:not-a-hash"),
            lambda obj: obj["artifact"].update(expired=True),
            lambda obj: obj["artifact"].update(id=0),
            lambda obj: obj["artifact"].update(size_bytes=0),
        ]
        for mutate in mutants:
            changed = copy.deepcopy(fixture)
            mutate(changed)
            with self.subTest(mutate=mutate):
                text = delivery.observed_shadow_metadata_panel(changed)
                self.assertIn("UNKNOWN", text)
                self.assertNotIn("40162915838", text)
                self.assertNotIn("來源 K 線可用時間：PASS", text)
        self.assertIn("UNKNOWN", delivery.observed_shadow_metadata_panel(None))

    def test_production_not_run_cannot_be_presented_as_executed_no_trade(self):
        current = delivery.read_json(delivery.CURRENT_OPERATIONS)
        panel = delivery.market_decision_panel(current)
        self.assertIn("僅設計時原因：NO_ELIGIBLE_STRATEGY", panel)
        self.assertIn("NOT_RUN（非 NO_TRADE）", panel)
        self.assertIn("不是 runtime reason 或已發生的 NO_TRADE", panel)

    def test_wrong_or_missing_registry_does_not_promote_hypothetical_reason(self):
        current = delivery.read_json(delivery.CURRENT_OPERATIONS)
        original = delivery.read_json
        for kind in ("missing", "changed", "nonempty"):
            def fake_reader(path, root=delivery.ROOT):
                if path == "config/cloud_paper_strategy_registry_v0_1.json":
                    if kind == "missing":
                        raise FileNotFoundError("unavailable")
                    if kind == "changed":
                        data = original(path, root)
                        data["model_quality"] = "PASS"
                        return data
                    data = original(path, root)
                    data["strategies"] = [{"id": "unverified"}]
                    return data
                return original(path, root)
            with patch.object(delivery, "read_json", fake_reader):
                panel = delivery.market_decision_panel(current)
                self.assertNotIn("僅設計時原因：NO_ELIGIBLE_STRATEGY", panel)
                self.assertIn("正式原因碼：UNKNOWN", panel)


if __name__ == "__main__":
    unittest.main()
