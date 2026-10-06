from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from typing import Protocol

from crypto_autopilot.features.structure import (
    build_market_structure_series,
    latest_market_structure_as_of,
)
from crypto_autopilot.models import BookTicker, Candle, MarketTicker
from crypto_autopilot.paper.cloud_market_v0_1 import validated_candles
from crypto_autopilot.providers.context_forward_capture import (
    ETH_TICKER_URL,
    GLOBAL_URL,
    build_context_forward_snapshot,
)
from crypto_autopilot.research.market_event_radar_v0_1 import (
    build_market_event_radar_snapshot,
)
from crypto_autopilot.research.pionex_universe_v0_1 import build_universe
from crypto_autopilot.research.technical_pattern_detectors_v0_1 import (
    build_technical_pattern_series,
    latest_technical_pattern_as_of,
)
from crypto_autopilot.technical import (
    build_technical_series,
    latest_closed_snapshot,
)


class PublicCollectionClient(Protocol):
    def list_perpetual_symbols(self) -> list[str]: ...
    def list_perpetual_tickers(self) -> list[MarketTicker]: ...
    def list_perpetual_book_tickers(self) -> list[BookTicker]: ...
    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ) -> list[Candle]: ...


def _record_id(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _validate_execution_config(config: Mapping[str, object]) -> None:
    if config.get("schema") != "qookey-prospective-shadow-collection-execution-v0.1":
        raise ValueError("unexpected prospective shadow execution schema")
    if config.get("version") != "0.1.0":
        raise ValueError("unexpected prospective shadow execution version")
    if config.get("status") != "AUTHORIZED_NOT_ACTIVE_UNTIL_IMPLEMENTATION_MERGED":
        raise ValueError("prospective shadow authority status changed")

    execution = config.get("execution")
    providers = config.get("providers")
    artifact = config.get("artifact_backend")
    research = config.get("research_contract")
    zero_cost = config.get("zero_cost_policy")
    authority = config.get("authority")
    if not all(
        isinstance(value, Mapping)
        for value in (execution, providers, artifact, research, zero_cost, authority)
    ):
        raise ValueError("prospective shadow execution config is incomplete")

    if execution.get("cron_utc") != "17 */4 * * *":
        raise ValueError("prospective shadow cron changed")
    if execution.get("maximum_natural_runs_per_day") != 6:
        raise ValueError("prospective shadow run budget changed")
    if zero_cost.get("monthly_budget_usd") != 0:
        raise ValueError("prospective shadow monthly budget must remain zero")

    pionex = providers.get("pionex")
    coinpaprika = providers.get("coinpaprika")
    if not isinstance(pionex, Mapping) or not isinstance(coinpaprika, Mapping):
        raise ValueError("prospective shadow provider config is incomplete")
    if pionex.get("maximum_requests_per_run") != 8:
        raise ValueError("Pionex request budget changed")
    if coinpaprika.get("maximum_requests_per_run") != 2:
        raise ValueError("CoinPaprika request budget changed")
    if artifact.get("retention_days") != 90:
        raise ValueError("artifact retention changed")
    if artifact.get("r2_access_authorized") is not False:
        raise ValueError("R2 must remain closed")
    if artifact.get("d1_access_authorized") is not False:
        raise ValueError("D1 must remain closed")

    required_true = (
        "research_only",
        "provider_public_fetch_authorized",
        "github_actions_artifact_read_authorized",
        "github_actions_artifact_write_authorized",
        "workflow_dispatch_authorized",
        "workflow_schedule_authorized",
    )
    if any(authority.get(key) is not True for key in required_true):
        raise ValueError("required research authority is missing")
    for key, value in authority.items():
        if key not in required_true and value is not False:
            raise ValueError(f"authority.{key} unexpectedly opened")


def _ticker_by_symbol(tickers: Sequence[MarketTicker]) -> dict[str, MarketTicker]:
    output: dict[str, MarketTicker] = {}
    for ticker in tickers:
        symbol = ticker.symbol.upper()
        if symbol in output:
            raise ValueError(f"duplicate ticker: {symbol}")
        output[symbol] = ticker
    return output


def _latest_market_evidence(
    *,
    symbol: str,
    candles: Sequence[Candle],
    as_of_ms: int,
) -> tuple[dict[str, object], bool, bool]:
    validated = validated_candles(candles, as_of_ms=as_of_ms)
    technical_series = build_technical_series(validated, "60M")
    technical = latest_closed_snapshot(
        technical_series,
        as_of_ms,
        require_ready=True,
    )
    if technical is None or not technical.ready_v0_2:
        raise ValueError(f"technical evidence not ready for {symbol}")

    structure = latest_market_structure_as_of(
        build_market_structure_series(
            validated,
            "60M",
            technical_series=technical_series,
        ),
        as_of_ms,
        require_ready=True,
    )
    if structure is None:
        raise ValueError(f"market structure not ready for {symbol}")

    patterns = latest_technical_pattern_as_of(
        build_technical_pattern_series(
            validated,
            "60M",
            technical_series=technical_series,
        ),
        as_of_ms,
    )
    if patterns is None:
        raise ValueError(f"technical pattern evidence not ready for {symbol}")

    radar = build_market_event_radar_snapshot(
        symbol=symbol,
        as_of_ms=as_of_ms,
        observed_at_ms=technical.bar_time_ms,
        available_at_ms=technical.available_at_ms,
        features={"relative_volume": technical.volume_ratio},
    )
    positive_momentum = validated[-1].close > validated[-6].close
    above_ema20 = technical.ema20 is not None and technical.close > technical.ema20
    payload = {
        "symbol": symbol,
        "candles_60m": [asdict(candle) for candle in validated],
        "technical": asdict(technical),
        "structure": asdict(structure),
        "patterns": asdict(patterns),
        "market_event_radar": radar,
        "candles_sha256": hashlib.sha256(
            json.dumps(
                [asdict(candle) for candle in validated],
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode()
        ).hexdigest(),
    }
    return payload, bool(above_ema20), bool(positive_momentum)


def build_collection_record(
    *,
    execution_config: Mapping[str, object],
    universe_config: Mapping[str, object],
    alternative_registry_bytes: bytes,
    context_config: Mapping[str, object],
    source_lineage_bytes: bytes,
    client: PublicCollectionClient,
    fetch_public_bytes: Callable[[str], bytes],
    capture_timestamp_ms: int,
) -> dict[str, object]:
    """Capture bounded normalized evidence for later prospective causal replay."""

    _validate_execution_config(execution_config)
    if (
        not isinstance(capture_timestamp_ms, int)
        or isinstance(capture_timestamp_ms, bool)
        or capture_timestamp_ms <= 0
    ):
        raise ValueError("capture_timestamp_ms must be a positive integer")

    symbols = client.list_perpetual_symbols()
    tickers = client.list_perpetual_tickers()
    books = client.list_perpetual_book_tickers()
    universe = build_universe(
        universe_config,
        alternative_registry_bytes=alternative_registry_bytes,
        live_symbols=symbols,
        tickers=tickers,
        book_tickers=books,
    )
    markets = universe.get("markets")
    if not isinstance(markets, list) or len(markets) < 5:
        raise ValueError("governed research universe has fewer than five markets")
    selected_markets = markets[:5]

    market_evidence: list[dict[str, object]] = []
    above_ema20: list[bool] = []
    positive_momentum: list[bool] = []
    for market in selected_markets:
        if not isinstance(market, Mapping):
            raise ValueError("invalid governed market row")
        symbol = market.get("symbol")
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("governed market symbol is required")
        rows = client.get_klines(
            symbol,
            "60M",
            limit=240,
            end_time_ms=(capture_timestamp_ms // 3_600_000) * 3_600_000 - 1,
        )
        evidence, above, momentum = _latest_market_evidence(
            symbol=symbol,
            candles=rows,
            as_of_ms=capture_timestamp_ms,
        )
        evidence["universe_market"] = dict(market)
        market_evidence.append(evidence)
        above_ema20.append(above)
        positive_momentum.append(momentum)

    global_payload = fetch_public_bytes(GLOBAL_URL)
    eth_payload = fetch_public_bytes(ETH_TICKER_URL)
    context = build_context_forward_snapshot(
        config=context_config,
        source_lineage_bytes=source_lineage_bytes,
        global_payload=global_payload,
        eth_payload=eth_payload,
        capture_timestamp_ms=capture_timestamp_ms,
    )

    ticker_map = _ticker_by_symbol(tickers)
    btc = ticker_map.get("BTC_USDT_PERP")
    eth = ticker_map.get("ETH_USDT_PERP")
    if btc is None or eth is None or btc.close <= 0.0 or eth.close <= 0.0:
        raise ValueError("BTC/ETH Pionex reference tickers are required")

    breadth_above = sum(above_ema20) / len(above_ema20)
    breadth_momentum = sum(positive_momentum) / len(positive_momentum)
    if not all(math.isfinite(value) for value in (breadth_above, breadth_momentum)):
        raise ValueError("breadth proxy must be finite")

    body: dict[str, object] = {
        "schema": "qookey-prospective-shadow-collection-run-v0.1",
        "capture_timestamp_ms": capture_timestamp_ms,
        "context_snapshot": context.as_dict(),
        "regime_observation_input": {
            "time_ms": capture_timestamp_ms,
            "available_at_ms": capture_timestamp_ms,
            "btc_close": btc.close,
            "eth_close": eth.close,
            "total3_value": context.total3_value,
            "btc_dominance_pct": context.btc_dominance_pct,
            "alt_breadth_above_ema20": breadth_above,
            "alt_breadth_positive_momentum": breadth_momentum,
            "breadth_scope": "TOP5_GOVERNED_SCAN_RESEARCH_PROXY",
            "production_regime_equivalence_claimed": False,
        },
        "universe_summary": {
            "status": universe.get("status"),
            "selected_market_count": universe.get("selected_market_count"),
            "crypto_core_count": universe.get("crypto_core_count"),
            "meme_candidate_selected_count": universe.get(
                "meme_candidate_selected_count"
            ),
            "alternative_asset_selected_count": universe.get(
                "alternative_asset_selected_count"
            ),
            "top5_symbols": [
                str(market["symbol"])
                for market in selected_markets
                if isinstance(market, Mapping)
            ],
        },
        "market_evidence": market_evidence,
        "replay_state": {
            "daily_opportunity_engine_v0_1_changed": False,
            "strategy_router_v0_1_changed": False,
            "signal_selection_performed_in_collector": False,
            "outcome_evaluation_performed_in_collector": False,
            "context_warmup_observations_required": 21,
            "future_replay_must_use_only_artifacts_available_at_signal_time": True,
        },
        "comparison_source": {
            "status": "UNAVAILABLE",
            "reason": "NO_GOVERNED_EXTERNAL_COMPARISON_SOURCE",
        },
        "authority": {
            "research_collection_only": True,
            "raw_provider_payload_persisted": False,
            "r2_accessed": False,
            "d1_accessed": False,
            "holdout_accessed": False,
            "training_performed": False,
            "model_promotion_performed": False,
            "candidate_reranking_changed": False,
            "strategy_router_threshold_changed": False,
            "paper_submission_performed": False,
            "real_money_order_performed": False,
            "live_trading_performed": False,
        },
    }
    return {**body, "record_id": _record_id(body)}
