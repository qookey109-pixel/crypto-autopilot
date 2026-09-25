from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "config/core100_training_fingerprint_v0_2_bootstrap_authority_proposal_v0_1.json"


def test_bootstrap_proposal_is_non_authorizing_and_preserves_legacy_pointer() -> None:
    proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    assert proposal["status"] == "PROPOSED_NOT_AUTHORIZED"
    assert proposal["user_decision_required"] == "AUTHORIZE_ONE_TIME_V0_2_BASELINE_TRAINING_AND_BOUNDED_R2_ACCESS"
    assert proposal["boundaries"]["active_cutover_authorized"] is False
    assert proposal["boundaries"]["training_authorized"] is False
    assert proposal["boundaries"]["r2_reads_authorized"] is False
    assert proposal["boundaries"]["r2_writes_authorized"] is False
    assert proposal["proposed_r2_access"]["writes_authorized_by_this_proposal"] is False
    assert proposal["after_bootstrap"]["legacy_v0_1_pointer"] == (
        "Never read, migrate, overwrite, or treat as V0.2 predecessor."
    )
    writes = proposal["proposed_r2_access"]["writes"]
    assert writes[-1]["key"].endswith("/fingerprint-v0.2/latest.json")
    assert proposal["proposed_r2_access"]["headroom_gate_bytes"] == 8_000_000_000
    assert proposal["boundaries"]["monthly_budget_usd"] == 0
