import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_market_request_budget_is_inactive_and_does_not_expand_v01():
    proposal = json.loads(
        (ROOT / "config/cloud_paper_market_request_budget_v0_2.json").read_text()
    )
    current = json.loads((ROOT / "config/cloud_paper_loop_v0_1.json").read_text())

    assert proposal["status"] == (
        "PREPARED_REQUIREMENT_ENVELOPE_NOT_EXECUTION_AUTHORITY"
    )
    assert proposal["requests"]["total_calls_per_slot"] == (
        proposal["requests"]["shared_market_calls_per_slot"]
        + proposal["requests"]["four_hour_breadth_calls_per_slot"]
        + proposal["requests"]["sixty_minute_candidate_calls_per_slot"]
        + proposal["requests"]["fifteen_minute_candidate_calls_per_slot"]
    )
    slots = proposal["assumptions"]["schedule_slots_per_day"]
    assert proposal["requests"]["maximum_calls_per_utc_day"] == (
        proposal["requests"]["total_calls_per_slot"] * slots
    )
    assert proposal["requests"]["maximum_calls_per_rolling_30_days"] == (
        proposal["requests"]["maximum_calls_per_utc_day"] * 30
    )
    kline_calls = (
        proposal["requests"]["four_hour_breadth_calls_per_slot"]
        + proposal["requests"]["sixty_minute_candidate_calls_per_slot"]
        + proposal["requests"]["fifteen_minute_candidate_calls_per_slot"]
    )
    assert proposal["requests"]["pionex_kline_weight_per_request"] == 1
    assert kline_calls == 33
    assert proposal["warmup"]["closed_bars_per_timeframe"] == {
        "4H_breadth_per_market": 21,
        "60M_candidate_technical": 200,
        "15M_candidate_technical": 200,
    }
    assert proposal["warmup"]["maximum_closed_bars_requested_per_slot"] == (
        23 * 21 + 5 * 200 + 5 * 200
    )
    assert proposal["requests"]["minimum_calls_with_shared_and_fixed_breadth_per_slot"] == (
        proposal["requests"]["shared_market_calls_per_slot"]
        + proposal["requests"]["four_hour_breadth_calls_per_slot"]
    )
    assert proposal["requests"]["minimum_exceeds_v0_1_run_ceiling"] is True
    assert (
        proposal["requests"]["minimum_calls_with_shared_and_fixed_breadth_per_slot"]
        > current["budget"]["provider_requests_per_run"]
    )
    assert proposal["requests"]["total_calls_per_slot"] > (
        current["budget"]["provider_requests_per_run"]
    )
    assert proposal["requests"]["maximum_calls_per_utc_day"] > (
        current["budget"]["provider_requests_per_utc_day"]
    )
    assert proposal["comparison_with_v0_1"]["fits_existing_contract"] is False
    assert proposal["assumptions"]["automatic_retries"] == 0
    assert proposal["assumptions"]["missed_slots_backfilled"] is False
    assert proposal["requests"]["shared_market_endpoint_weights"] is None
    assert proposal["requests"]["provider_rate_limit"] is None
    assert proposal["freshness"]["15m_age_limit_status"] == (
        "PROPOSAL_NOT_CURRENT_AUTHORITY"
    )
    assert proposal["freshness"][
        "schedule_delay_can_exceed_proposed_15m_bar_age_limit"
    ] is True
    assert proposal["cache_and_storage"]["durable_cache_authorized"] is False

    for key in (
        "provider_fetch_authorized",
        "r2_access_authorized",
        "d1_access_authorized",
        "runtime_activation_authorized",
        "schedule_activation_authorized",
        "strategy_qualification_or_change_authorized",
        "source_switch_authorized",
        "holdout_access_authorized",
        "model_promotion_authorized",
        "real_money_orders_authorized",
        "live_trading_authorized",
    ):
        assert proposal["authority"][key] is False
