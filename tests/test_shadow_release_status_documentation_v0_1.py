"""GitHub CI-only consistency checks for the dated Shadow release handoff.

This is a repository fixture test, not a live polling mechanism or an
execution-authority grant. Never accesses the user's local machine.
"""
from __future__ import annotations

import copy
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = (
    "CURRENT_STATUS.md",
    "docs/PROJECT_CONTINUATION_RUNBOOK.md",
)
RELEASE_MAIN = "a7ee3e951d1d1f1e02e58a62c7951ea1ca5763db"
RELEASE_PAGES_RUN = 38120258816
RELEASE_AUDIT_RUN = 38117712031


def release_header(text: str) -> str:
    """Validate only the current top release section, not dated old snapshots."""
    section = text.split("\n---\n", 1)[0]
    if not section.startswith("## Current merged release checkpoint — 2026-10-11"):
        raise ValueError("MISSING_DATED_RELEASE_CHECKPOINT")
    return section


def require_release_projection(
    documents: dict[str, str],
    operations: dict[str, object],
    receipt: dict[str, object],
) -> None:
    """Raise on inconsistent release docs or upgraded research authority."""
    if set(documents) != set(DOCUMENTS):
        raise ValueError("INCOMPLETE_HANDOFF_SURFACES")
    shadow = operations["vnext_delivery_checkpoint"]["prospective_shadow"][
        "sixteen_batch_audit"
    ]
    totals = receipt["cumulative"]
    if (
        shadow["status"] != "REVIEW_REQUIRED_MULTIPLE_SOURCE_GAPS"
        or shadow["continuity"] != totals["continuity_state"]
        or shadow["continuity"] != "REVIEW_REQUIRED"
        or shadow["maturity"] != totals["warmup_state"]
        or shadow["maturity"] != "INSUFFICIENT"
        or shadow["cumulative_distinct_observations"] != totals["verified_distinct_observations"]
        or shadow["required_observations"] != totals["warmup_target_observations"]
        or shadow["consistent_overlap_candles"] != totals[
            "overlap_consistent_candles_across_15_adjacent_pairs"
        ]
        or shadow["observed_gaps_over_six_hours_count"] != totals[
            "gaps_over_six_hours_count"
        ]
        or shadow["maximum_source_lag_minutes"] != totals["max_source_lag_minutes"]
        or shadow["audit_run_id"] != RELEASE_AUDIT_RUN
        or any(shadow[key] is not False for key in (
            "continuous_collection_proven", "model_promotion_authorized",
            "paper_activated", "real_money_trading_authorized",
        ))
        or operations["core100"]["model_quality_gate"]["status"] != "REJECT"
        or operations["cloudflare_prepaid_d1_runtime_gateway_v0_1"][
            "production_cycle_status"
        ] != "NOT_RUN"
    ):
        raise ValueError("MACHINE_EVIDENCE_OR_AUTHORITY_DRIFT")

    expected = (
        f"{totals['verified_distinct_observations']}/"
        f"{totals['warmup_target_observations']}"
    )
    overlaps = f"{totals['overlap_consistent_candles_across_15_adjacent_pairs']:,}"
    for path, text in documents.items():
        top = release_header(text)
        # Every observation count in this top section must agree, not just
        # one correct occurrence alongside a later corrupted duplicate.
        observed_counts = set(re.findall(
            rf"\b\d+/{totals['warmup_target_observations']}\b", top,
        ))
        if observed_counts != {expected}:
            raise ValueError("DOCUMENT_RELEASE_MISMATCH:" + path)
        required = (
            operations["updated_date"],
            f"main={RELEASE_MAIN}",
            expected,
            overlaps,
            "nine actual capture intervals over six hours",
            "REVIEW_REQUIRED",
            "INSUFFICIENT",
            "Core100 model quality **\u0060REJECT\u0060**",
            "\u0060NOT_WIRED / NOT_RUN / NOT_CONFIGURED\u0060",
            str(RELEASE_AUDIT_RUN),
            str(RELEASE_PAGES_RUN),
            "60/60",
            "CLOUD_ONLY",
        )
        # CLOUD_ONLY is represented by the explicit paragraph below the
        # top marker, not by credentials or a local-run indicator.
        required = tuple(x for x in required if x != "CLOUD_ONLY") + ("Cloud-only evidence",)
        for value in required:
            if value not in top:
                raise ValueError("DOCUMENT_RELEASE_MISMATCH:" + path)
        if "continuous warmup proven" in top or "model quality PASS" in top:
            raise ValueError("UNAUTHORIZED_RESEARCH_CLAIM")


class ShadowReleaseDocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.documents = {
            path: (ROOT / path).read_text(encoding="utf-8")
            for path in DOCUMENTS
        }
        cls.operations = json.loads(
            (ROOT / "research/status/current-operations-v0-3.json").read_text(
                encoding="utf-8"
            )
        )
        cls.receipt = json.loads(
            (ROOT / "research/receipts/2026-10-11-shadow-sixteen-incremental-audit-v0-1.json").read_text(
                encoding="utf-8"
            )
        )

    def test_both_current_handoffs_match_immutable_sixteen_evidence(self):
        require_release_projection(self.documents, self.operations, self.receipt)

    def test_missing_or_altered_handoff_cannot_look_current(self):
        for path in DOCUMENTS:
            changed = copy.deepcopy(self.documents)
            for original, wrong in (
                ("16/21", "21/21"),
                ("15,604", "15,603"),
                ("60/60", "FAILED"),
                ("Core100 model quality", "Core100 model approved"),
            ):
                with self.subTest(path=path, altered=original):
                    changed[path] = self.documents[path].replace(original, wrong, 1)
                    with self.assertRaisesRegex(ValueError, "DOCUMENT_RELEASE_MISMATCH"):
                        require_release_projection(changed, self.operations, self.receipt)
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_HANDOFF_SURFACES"):
            require_release_projection(
                {"CURRENT_STATUS.md": self.documents["CURRENT_STATUS.md"]},
                self.operations, self.receipt,
            )

    def test_machine_tampering_cannot_promote_context_or_paper(self):
        for key, wrong in (
            ("cumulative_distinct_observations", 21),
            ("observed_gaps_over_six_hours_count", 0),
            ("maximum_source_lag_minutes", 0),
            ("continuous_collection_proven", True),
            ("model_promotion_authorized", True),
            ("paper_activated", True),
            ("real_money_trading_authorized", True),
        ):
            with self.subTest(field=key):
                bad = copy.deepcopy(self.operations)
                bad["vnext_delivery_checkpoint"]["prospective_shadow"][
                    "sixteen_batch_audit"
                ][key] = wrong
                with self.assertRaisesRegex(ValueError, "MACHINE_EVIDENCE_OR_AUTHORITY_DRIFT"):
                    require_release_projection(self.documents, bad, self.receipt)

    def test_receipt_revision_must_fail(self):
        changed = copy.deepcopy(self.receipt)
        changed["cumulative"]["overlap_consistent_candles_across_15_adjacent_pairs"] += 1
        with self.assertRaisesRegex(ValueError, "MACHINE_EVIDENCE_OR_AUTHORITY_DRIFT"):
            require_release_projection(self.documents, self.operations, changed)


if __name__ == "__main__":
    unittest.main()
