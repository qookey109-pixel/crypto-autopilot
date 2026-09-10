"""Tokenized-equity paper challenger using the crypto technical baseline.

The asset class is isolated and every market must carry explicit session,
corporate-action and spread evidence before a candidate can enter replay.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from .backtest import BacktestConfig, FundingPoint, LongTradePlan, run_long_backtest
from .models import Candle
from .paper_training import CandidateSignal, _candidate as _crypto_candidate
from .technical import TechnicalSnapshot
from .advanced_technical import AdvancedTechnicalSnapshot
from .risk import RiskConfig


@dataclass(frozen=True, slots=True)
class TokenizedEquityMarket:
    symbol: str
    asset_class: str
    status: str
    provider: str
    intervals: tuple[str, ...]
    session_model_verified: bool
    corporate_action_policy: bool
    spread_bps: float


@dataclass(frozen=True, slots=True)
class TokenizedEquityCandidate:
    market: TokenizedEquityMarket
    core_candidate: CandidateSignal | None
    eligible: bool
    reasons: tuple[str, ...]

    @property
    def plan(self) -> LongTradePlan | None:
        if self.core_candidate is None:
            return None
        return LongTradePlan(
            plan_id=f"tokenized-{self.core_candidate.plan_id}",
            symbol=self.core_candidate.symbol,
            signal_time_ms=self.core_candidate.signal_time_ms,
            stop_price=self.core_candidate.stop_price,
            target_price=self.core_candidate.target_price,
        )

    def evidence(self) -> dict[str, Any]:
        return {
            "symbol": self.market.symbol,
            "assetClass": self.market.asset_class,
            "provider": self.market.provider,
            "eligible": self.eligible,
            "reasons": list(self.reasons),
            "candidateScore": self.core_candidate.score if self.core_candidate else None,
            "signalTimeMs": self.core_candidate.signal_time_ms if self.core_candidate else None,
            "features": dict(self.core_candidate.features) if self.core_candidate else {},
        }


def tokenized_market_reasons(
    market: TokenizedEquityMarket,
    *,
    required_intervals: Sequence[str],
    maximum_spread_bps: float,
) -> list[str]:
    reasons: list[str] = []
    if market.asset_class != "tokenized_stock_candidate":
        reasons.append("asset_class_not_tokenized_stock_candidate")
    if market.status != "TRADING":
        reasons.append("market_not_trading")
    if market.provider != "pionex_public_futures":
        reasons.append("provider_not_pionex_public_futures")
    if not set(required_intervals).issubset(market.intervals):
        reasons.append("required_interval_coverage_missing")
    if not market.session_model_verified:
        reasons.append("session_model_not_verified")
    if not market.corporate_action_policy:
        reasons.append("corporate_action_policy_missing")
    if market.spread_bps < 0 or market.spread_bps > maximum_spread_bps:
        reasons.append("spread_gate_failed")
    return reasons


def score_tokenized_equity_candidate(
    *,
    market: TokenizedEquityMarket,
    technical: TechnicalSnapshot,
    advanced: AdvancedTechnicalSnapshot,
    higher: Sequence[TechnicalSnapshot],
    config: Mapping[str, Any],
) -> TokenizedEquityCandidate:
    """Apply the crypto candidate scorer only after tokenized-market gates pass."""
    policy = config["market_policy"]
    reasons = tokenized_market_reasons(
        market,
        required_intervals=policy["required_intervals"],
        maximum_spread_bps=float(policy["maximum_spread_bps"]),
    )
    if reasons:
        return TokenizedEquityCandidate(market, None, False, tuple(reasons))
    core = _crypto_candidate(
        symbol=market.symbol,
        technical=technical,
        advanced=advanced,
        higher=higher,
        config={
            "candidate_thresholds": config.get("candidate_thresholds", {}),
            "paper_risk": config["paper_risk"],
        },
    )
    return TokenizedEquityCandidate(
        market=market,
        core_candidate=core,
        eligible=core.eligible,
        reasons=core.reasons,
    )


def run_tokenized_equity_paper_replay(
    *,
    candidates: Sequence[TokenizedEquityCandidate],
    candles_by_symbol: Mapping[str, Sequence[Candle]],
    funding_points: Sequence[FundingPoint] = (),
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Run a bounded paper replay for already-scored tokenized candidates."""
    plans: list[LongTradePlan] = []
    rejected: list[list[str]] = []
    seen: set[str] = set()
    for candidate in candidates:
        plan = candidate.plan
        if plan is None or not candidate.eligible:
            rejected.append([candidate.market.symbol, *candidate.reasons])
            continue
        if plan.plan_id in seen:
            raise ValueError("tokenized candidate plan_id values must be unique")
        seen.add(plan.plan_id)
        plans.append(plan)

    risk = config["paper_risk"]
    result = run_long_backtest(
        candles_by_symbol={symbol: tuple(values) for symbol, values in candles_by_symbol.items()},
        plans=tuple(plans),
        funding_points=tuple(funding_points),
        config=BacktestConfig(
            initial_equity_usd=float(risk["initial_equity_usd"]),
            taker_fee_bps=float(risk["taker_fee_bps"]),
            slippage_bps=float(risk["slippage_bps"]),
            risk=RiskConfig(
                risk_fraction_per_trade=float(risk["risk_fraction_per_trade"]),
                max_leverage=float(risk["maximum_leverage"]),
                daily_loss_limit_r=float(risk["daily_loss_limit_r"]),
                max_new_trades_per_day=int(risk["maximum_new_trades_per_day"]),
            ),
        ),
    )
    return {
        "schema": "tokenized-equity-paper-replay-v0.1",
        "status": "PASS",
        "mode": "TOKENIZED_EQUITY_PAPER_CHALLENGER",
        "assetClass": "tokenized_stock_candidate",
        "candidateCount": len(candidates),
        "eligibleCandidateCount": len(plans),
        "candidateEvidence": [candidate.evidence() for candidate in candidates],
        "paperTrades": [asdict(trade) for trade in result.trades],
        "rejectedCandidates": rejected,
        "rejectedPlans": [list(item) for item in result.rejected_plans],
        "metrics": asdict(result.metrics),
        "interpretation": {
            "same_crypto_technical_logic": True,
            "asset_class_isolated": True,
            "not_a_crypto_portfolio_result": True,
            "tokenized_classification_not_tradability_proof": True,
        },
        "authority": dict(config["authority"]),
    }
