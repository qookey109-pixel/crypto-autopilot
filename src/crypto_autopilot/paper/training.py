from __future__ import annotations

from bisect import bisect_right
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from crypto_autopilot.features.advanced import AdvancedTechnicalSnapshot, build_advanced_technical_series
from crypto_autopilot.backtest import BacktestConfig, FundingPoint, LongTradePlan, run_long_backtest
from crypto_autopilot.lineage import build_lineage_manifest, sha256_json
from crypto_autopilot.features.market import DerivativeFeatures, FundingRateObservation, MicrostructureFeatures
from crypto_autopilot.models import Candle
from crypto_autopilot.risk import RiskConfig
from crypto_autopilot.technical import TechnicalSnapshot, build_technical_series


REQUIRED_INTERVALS = ("15M", "60M", "4H", "8H", "1D")


@dataclass(frozen=True, slots=True)
class CandidateSignal:
    plan_id: str
    symbol: str
    signal_time_ms: int
    score: float
    eligible: bool
    reasons: tuple[str, ...]
    reference_price: float
    stop_price: float
    target_price: float
    trend_agreement: float
    features: tuple[tuple[str, float], ...]


def _latest_as_of(series: Sequence[Any], available_times: Sequence[int], as_of_ms: int) -> Any | None:
    index = bisect_right(available_times, as_of_ms) - 1
    return series[index] if index >= 0 else None


def _trend_vote(snapshot: TechnicalSnapshot) -> bool:
    return bool(
        snapshot.ready_v0_2
        and snapshot.ema20 is not None
        and snapshot.ema50 is not None
        and snapshot.ema200 is not None
        and snapshot.ema20_slope is not None
        and snapshot.ema20 > snapshot.ema50
        and snapshot.close > snapshot.ema200
        and snapshot.ema20_slope > 0
    )


def _candidate(
    *,
    symbol: str,
    technical: TechnicalSnapshot,
    advanced: AdvancedTechnicalSnapshot,
    higher: Sequence[TechnicalSnapshot],
    config: Mapping[str, Any],
) -> CandidateSignal:
    thresholds = config["candidate_thresholds"]
    risk = config["paper_risk"]
    trend_agreement = sum(_trend_vote(snapshot) for snapshot in higher) / len(higher)

    reasons: list[str] = []
    if not technical.ready_v0_2 or not advanced.ready:
        reasons.append("feature_warmup_incomplete")
    if trend_agreement < float(thresholds["minimum_trend_agreement"]):
        reasons.append("higher_timeframe_trend_not_aligned")
    if (advanced.adx14 or 0.0) < float(thresholds["minimum_adx14"]):
        reasons.append("trend_strength_below_gate")
    if (advanced.plus_di14 or 0.0) <= (advanced.minus_di14 or 0.0):
        reasons.append("directional_index_not_long")
    if (advanced.vwap_distance_fraction or -1.0) <= 0:
        reasons.append("below_rolling_vwap")
    if not float(thresholds["minimum_rsi14"]) <= (technical.rsi14 or -1.0) <= float(
        thresholds["maximum_rsi14"]
    ):
        reasons.append("rsi_outside_gate")
    if (technical.macd_histogram or 0.0) <= 0:
        reasons.append("macd_histogram_not_positive")
    if (advanced.donchian_position20 or -1.0) < float(
        thresholds["minimum_donchian_position"]
    ):
        reasons.append("donchian_position_below_gate")
    if (advanced.volume_zscore20 or -99.0) < float(thresholds["minimum_volume_zscore"]):
        reasons.append("relative_volume_below_gate")
    if (advanced.kaufman_efficiency_ratio10 or 0.0) < float(
        thresholds["minimum_efficiency_ratio"]
    ):
        reasons.append("efficiency_ratio_below_gate")

    score = 0.0
    score += 25.0 * trend_agreement
    score += 15.0 * min(1.0, max(0.0, (advanced.adx14 or 0.0) / 40.0))
    score += 10.0 if (advanced.plus_di14 or 0.0) > (advanced.minus_di14 or 0.0) else 0.0
    score += 10.0 if (advanced.vwap_distance_fraction or -1.0) > 0 else 0.0
    score += 10.0 if (technical.macd_histogram or 0.0) > 0 else 0.0
    score += 10.0 * min(1.0, max(0.0, (advanced.donchian_position20 or 0.0)))
    score += 10.0 * min(1.0, max(0.0, ((advanced.volume_zscore20 or 0.0) + 1.0) / 3.0))
    score += 10.0 * min(1.0, max(0.0, advanced.kaufman_efficiency_ratio10 or 0.0))
    score = round(min(100.0, score), 8)

    if score < float(thresholds["minimum_candidate_score"]):
        reasons.append("candidate_score_below_gate")
    atr = float(technical.atr14 or 0.0)
    stop = technical.close - atr * float(risk["stop_atr_multiple"])
    target = technical.close + atr * float(risk["target_atr_multiple"])
    if atr <= 0 or stop <= 0:
        reasons.append("invalid_atr_risk_geometry")

    features = {
        "adx14": advanced.adx14 or 0.0,
        "plus_di14": advanced.plus_di14 or 0.0,
        "minus_di14": advanced.minus_di14 or 0.0,
        "vwap_distance_fraction": advanced.vwap_distance_fraction or 0.0,
        "volume_zscore20": advanced.volume_zscore20 or 0.0,
        "donchian_position20": advanced.donchian_position20 or 0.0,
        "atr_percentile100": advanced.atr_percentile100 or 0.0,
        "bollinger_bandwidth_percentile100": (
            advanced.bollinger_bandwidth_percentile100 or 0.0
        ),
        "realized_volatility20": advanced.realized_volatility20 or 0.0,
        "parkinson_volatility20": advanced.parkinson_volatility20 or 0.0,
        "volatility_of_volatility20": advanced.volatility_of_volatility20 or 0.0,
        "kaufman_efficiency_ratio10": advanced.kaufman_efficiency_ratio10 or 0.0,
        "choppiness_index14": advanced.choppiness_index14 or 0.0,
        "volatility_adjusted_momentum20": advanced.volatility_adjusted_momentum20 or 0.0,
        "trend_agreement": trend_agreement,
    }
    return CandidateSignal(
        plan_id=f"paper-{symbol}-{technical.bar_time_ms}",
        symbol=symbol,
        signal_time_ms=technical.bar_time_ms,
        score=score,
        eligible=not reasons,
        reasons=tuple(reasons) if reasons else ("eligible_paper_candidate",),
        reference_price=technical.close,
        stop_price=stop,
        target_price=target,
        trend_agreement=trend_agreement,
        features=tuple(sorted((key, round(value, 12)) for key, value in features.items())),
    )


def run_paper_training_replay(
    *,
    run_id: str,
    observed_at_utc: str,
    candles_by_symbol_interval: Mapping[str, Mapping[str, Sequence[Candle]]],
    funding_by_symbol: Mapping[str, Sequence[FundingRateObservation]],
    live_microstructure: Mapping[str, MicrostructureFeatures],
    live_derivatives: Mapping[str, DerivativeFeatures],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    symbols = tuple(sorted(candles_by_symbol_interval))
    candidates: list[CandidateSignal] = []
    candles_for_backtest: dict[str, tuple[Candle, ...]] = {}
    replay_bars = int(config["replay"]["fifteen_minute_bars"])

    dataset_evidence: dict[str, Any] = {}
    for symbol in symbols:
        by_interval = candles_by_symbol_interval[symbol]
        if any(interval not in by_interval for interval in REQUIRED_INTERVALS):
            continue
        technical_by_interval = {
            interval: build_technical_series(by_interval[interval], interval)
            for interval in REQUIRED_INTERVALS
        }
        advanced_15m = build_advanced_technical_series(
            by_interval["15M"], "15M", technical_series=technical_by_interval["15M"]
        )
        available_by_interval = {
            interval: tuple(item.available_at_ms for item in series)
            for interval, series in technical_by_interval.items()
        }
        candles_for_backtest[symbol] = tuple(by_interval["15M"])
        dataset_evidence[symbol] = {
            interval: [asdict(candle) for candle in by_interval[interval]]
            for interval in REQUIRED_INTERVALS
        }

        start = max(0, len(advanced_15m) - replay_bars)
        for index in range(start, len(advanced_15m)):
            technical = technical_by_interval["15M"][index]
            advanced = advanced_15m[index]
            higher: list[TechnicalSnapshot] = []
            for interval in ("60M", "4H", "8H", "1D"):
                snapshot = _latest_as_of(
                    technical_by_interval[interval],
                    available_by_interval[interval],
                    technical.available_at_ms,
                )
                if snapshot is None:
                    higher = []
                    break
                higher.append(snapshot)
            if not higher:
                continue
            candidates.append(
                _candidate(
                    symbol=symbol,
                    technical=technical,
                    advanced=advanced,
                    higher=higher,
                    config=config,
                )
            )

    eligible = tuple(candidate for candidate in candidates if candidate.eligible)
    plans = tuple(
        LongTradePlan(
            plan_id=candidate.plan_id,
            symbol=candidate.symbol,
            signal_time_ms=candidate.signal_time_ms,
            stop_price=candidate.stop_price,
            target_price=candidate.target_price,
        )
        for candidate in eligible
    )
    funding_points = tuple(
        FundingPoint(item.symbol, item.funding_time_ms, item.funding_rate)
        for symbol in symbols
        for item in funding_by_symbol.get(symbol, ())
    )
    risk_cfg = config["paper_risk"]
    result = run_long_backtest(
        candles_by_symbol=candles_for_backtest,
        plans=plans,
        funding_points=funding_points,
        config=BacktestConfig(
            initial_equity_usd=float(risk_cfg["initial_equity_usd"]),
            taker_fee_bps=float(risk_cfg["taker_fee_bps"]),
            slippage_bps=float(risk_cfg["slippage_bps"]),
            risk=RiskConfig(
                risk_fraction_per_trade=float(risk_cfg["risk_fraction_per_trade"]),
                max_leverage=float(risk_cfg["maximum_leverage"]),
                daily_loss_limit_r=float(risk_cfg["daily_loss_limit_r"]),
                max_new_trades_per_day=int(risk_cfg["maximum_new_trades_per_day"]),
            ),
        ),
    )
    candidate_by_id = {candidate.plan_id: candidate for candidate in eligible}
    training_records = []
    for trade in result.trades:
        candidate = candidate_by_id[trade.plan_id]
        training_records.append(
            {
                "planId": trade.plan_id,
                "symbol": trade.symbol,
                "signalTimeMs": trade.signal_time_ms,
                "features": dict(candidate.features),
                "candidateScore": candidate.score,
                "outcome": {
                    "exitReason": trade.exit_reason,
                    "netPnlUsd": trade.net_pnl_usd,
                    "rMultiple": trade.r_multiple,
                },
            }
        )

    lineage = build_lineage_manifest(
        run_id=run_id,
        provider="pionex_public_futures",
        symbol_universe=symbols,
        intervals=REQUIRED_INTERVALS,
        datasets={"public_candles": dataset_evidence},
        feature_config=config["features"],
        strategy_config={
            "candidate_thresholds": config["candidate_thresholds"],
            "paper_risk": config["paper_risk"],
        },
        environment={"runner": "github-actions-or-local", "mode": "paper-training"},
        seed=0,
    )

    latest_candidates: dict[str, CandidateSignal] = {}
    latest_eligible_candidates: dict[str, CandidateSignal] = {}
    for candidate in candidates:
        previous = latest_candidates.get(candidate.symbol)
        if previous is None or candidate.signal_time_ms > previous.signal_time_ms:
            latest_candidates[candidate.symbol] = candidate
        if candidate.eligible:
            previous_eligible = latest_eligible_candidates.get(candidate.symbol)
            if (
                previous_eligible is None
                or candidate.signal_time_ms > previous_eligible.signal_time_ms
            ):
                latest_eligible_candidates[candidate.symbol] = candidate

    return {
        "schema": "pionex-public-paper-training-run-v0.1",
        "status": "PASS",
        "mode": "PAPER_TRAINING_ONLY",
        "runId": run_id,
        "observedAtUtc": observed_at_utc,
        "provider": "pionex_public_futures",
        "authority": {
            "publicMarketDataReadAuthorized": True,
            "paperCandidateGenerationAuthorized": True,
            "repositoryPaperBrokerAuthorized": True,
            "formalTradePlanAuthorized": False,
            "pionexDemoAutomationAuthorized": False,
            "privateApiUsed": False,
            "r2ReadsPerformed": False,
            "r2WritesPerformed": False,
            "holdoutAccessed": False,
            "sourceSwitchAuthorized": False,
            "realMoneyOrderAuthorized": False,
            "liveTradingAuthorized": False,
        },
        "lineage": lineage.evidence(),
        "lineageFingerprint": lineage.fingerprint,
        "inputFingerprint": sha256_json(dataset_evidence),
        "symbolCount": len(symbols),
        "candidateCount": len(candidates),
        "eligibleCandidateCount": len(eligible),
        "latestCandidates": [asdict(latest_candidates[symbol]) for symbol in sorted(latest_candidates)],
        "paperTrades": [asdict(trade) for trade in result.trades],
        "rejectedPlans": [list(item) for item in result.rejected_plans],
        "metrics": asdict(result.metrics),
        "initialEquityUsd": result.initial_equity_usd,
        "finalEquityUsd": result.final_equity_usd,
        "equityCurve": list(result.equity_curve),
        "trainingRecords": training_records,
        "liveMarketState": {
            symbol: {
                "microstructure": asdict(live_microstructure[symbol])
                if symbol in live_microstructure
                else None,
                "derivatives": asdict(live_derivatives[symbol])
                if symbol in live_derivatives
                else None,
            }
            for symbol in symbols
        },
        "manualPionexDemoSamples": [
            {
                "symbol": candidate.symbol,
                "signalTimeMs": candidate.signal_time_ms,
                "candidateScore": candidate.score,
                "referencePrice": candidate.reference_price,
                "stopPrice": candidate.stop_price,
                "targetPrice": candidate.target_price,
                "action": "MANUAL_REVIEW_ONLY",
            }
            for candidate in sorted(
                latest_eligible_candidates.values(),
                key=lambda item: (-item.signal_time_ms, -item.score, item.symbol),
            )[:3]
        ],
        "interpretation": (
            "Bounded public-data rolling replay and forward-training evidence only; "
            "not a profitability claim or live-trading authority."
        ),
    }
