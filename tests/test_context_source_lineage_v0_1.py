from __future__ import annotations

import json
from pathlib import Path


def test_context_source_lineage_is_zero_cost_and_research_only() -> None:
    config = json.loads(Path("config/context_source_lineage_v0_1.json").read_text())

    assert config["version"] == "0.1.0"
    assert config["status"] == "PREPARED_RESEARCH_ONLY_SOURCE_DECISION"
    assert config["zero_cost_policy"]["monthly_budget_usd"] == 0
    assert config["zero_cost_policy"]["paid_fallback_allowed"] is False
    assert config["zero_cost_policy"]["scraping_unofficial_chart_endpoints_allowed"] is False

    candidate = config["forward_candidate"]
    assert candidate["provider"] == "coinpaprika"
    assert candidate["plan"] == "Free"
    assert candidate["monthly_cost_usd"] == 0
    assert candidate["authentication_required"] is False
    assert candidate["documented_monthly_request_limit"] == 20000
    assert candidate["endpoints"] == {
        "global": "/global",
        "eth_ticker": "/tickers/eth-ethereum",
    }
    assert candidate["current_snapshot_semantics_supported"] is True
    assert candidate["historical_global_semantics_supported"] is False
    assert candidate["candidate_use"] == (
        "FORWARD_COLLECTION_ONLY_AFTER_SEPARATE_EXECUTION_AUTHORITY"
    )

    semantics = config["semantic_contract"]
    assert semantics["same_provider_components_required"] is True
    assert semantics["negative_total3_fails_closed"] is True
    assert semantics["total3_value"] == (
        "total_market_cap_usd - btc_market_cap_usd - eth_market_cap_usd"
    )

    historical = config["historical_decision"]
    assert historical["status"] == "BLOCKED_NO_ZERO_COST_CANONICAL_GLOBAL_HISTORY"
    assert historical["coingecko_global_market_cap_chart"]["status"] == "REJECTED_PAID"
    assert historical["coinmarketcap_global_metrics_historical"]["status"] == "REJECTED_PAID"
    assert historical["unofficial_tradingview_or_web_scrape"]["status"] == "REJECTED"

    integration = config["integration_boundary"]
    assert integration["market_regime_breadth_v0_1_real_global_context_ready"] is False
    assert integration["contextual_edge_evaluation_v0_1_real_global_history_ready"] is False
    assert integration["missing_global_history_must_not_be_imputed_from_current_snapshot"] is True

    authority = config["authority"]
    assert authority["research_only"] is True
    mutable_authority = {key: value for key, value in authority.items() if key != "research_only"}
    assert mutable_authority
    assert all(value is False for value in mutable_authority.values())
