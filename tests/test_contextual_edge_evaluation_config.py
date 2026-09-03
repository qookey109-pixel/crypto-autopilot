from __future__ import annotations

import json
from pathlib import Path


def test_contextual_edge_evaluation_authority_remains_research_only() -> None:
    config = json.loads(Path("config/contextual_edge_evaluation_v0_1.json").read_text())

    assert config["version"] == "0.1.0"
    assert config["status"] == "PREPARED_RESEARCH_ONLY"
    assert config["inputs"]["join_rule"] == (
        "latest regime with available_at_ms <= breakout_available_at_ms"
    )
    assert config["inputs"]["future_resolution_masking_required"] is True
    assert config["metrics"]["minimum_decisive_events_for_uplift"] == 30
    assert config["metrics"]["interpretation"] == "DESCRIPTIVE_ONLY"
    assert config["statistical_boundary"]["parameter_selection"] is False
    assert config["statistical_boundary"]["significance_claim"] is False
    assert config["statistical_boundary"]["promotion_gate"] is False
    assert config["statistical_boundary"]["formal_statistical_validation_layer"] == (
        "Strategy Edge Validation V0.1"
    )

    authority = config["authority"]
    assert authority
    assert all(value is False for value in authority.values())
