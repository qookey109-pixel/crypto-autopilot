from __future__ import annotations

import math
from dataclasses import dataclass

from .historical import audit_candles
from .models import Candle
from .technical import build_technical_series


class ProviderEquivalenceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProviderEquivalencePolicy:
    """Pre-evidence V0.1 overlap gate for Pionex vs Binance market data."""

    median_ohlc_bps_pass: float = 10.0
    median_ohlc_bps_review: float = 25.0
    p95_open_close_bps_pass: float = 25.0
    p95_open_close_bps_review: float = 75.0
    p95_high_low_bps_pass: float = 75.0
    p95_high_low_bps_review: float = 200.0
    return_direction_agreement_pass: float = 0.98
    return_direction_agreement_review: float = 0.95
    setup_60m_agreement_pass: float = 0.98
    setup_60m_agreement_review: float = 0.95
    min_ready_setup_bars_60m: int = 100
    min_rows_15m: int = 600
    min_rows_60m: int = 150
    min_rows_4h: int = 40
    max_review_fraction_for_aggregate_review: float = 0.20

    def __post_init__(self) -> None:
        upper_pairs = (
            (self.median_ohlc_bps_pass, self.median_ohlc_bps_review, "median_ohlc_bps"),
            (self.p95_open_close_bps_pass, self.p95_open_close_bps_review, "p95_open_close_bps"),
            (self.p95_high_low_bps_pass, self.p95_high_low_bps_review, "p95_high_low_bps"),
        )
        for passed, review, name in upper_pairs:
            if not (math.isfinite(passed) and math.isfinite(review) and 0 <= passed < review):
                raise ValueError(f"invalid {name} thresholds")
        lower_pairs = (
            (
                self.return_direction_agreement_pass,
                self.return_direction_agreement_review,
                "return_direction_agreement",
            ),
            (self.setup_60m_agreement_pass, self.setup_60m_agreement_review, "setup_60m_agreement"),
        )
        for passed, review, name in lower_pairs:
            if not (0 <= review < passed <= 1):
                raise ValueError(f"invalid {name} thresholds")
        for name, value in (
            ("min_ready_setup_bars_60m", self.min_ready_setup_bars_60m),
            ("min_rows_15m", self.min_rows_15m),
            ("min_rows_60m", self.min_rows_60m),
            ("min_rows_4h", self.min_rows_4h),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if not 0 <= self.max_review_fraction_for_aggregate_review <= 1:
            raise ValueError("max_review_fraction_for_aggregate_review must be between 0 and 1")

    def min_rows(self, interval: str) -> int:
        values = {"15M": self.min_rows_15m, "60M": self.min_rows_60m, "4H": self.min_rows_4h}
        try:
            return values[interval]
        except KeyError as exc:
            raise ValueError(f"unsupported equivalence interval: {interval}") from exc


@dataclass(frozen=True, slots=True)
class ProviderPairEquivalence:
    pionex_symbol: str
    binance_symbol: str
    interval: str
    pionex_rows: int
    binance_rows: int
    timestamp_exact: bool
    missing_in_pionex: int
    missing_in_binance: int
    median_ohlc_bps: float | None
    p95_open_close_bps: float | None
    p95_high_low_bps: float | None
    return_direction_agreement: float | None
    setup_60m_ready_bars: int | None
    setup_60m_agreement: float | None
    status: str
    reasons: tuple[str, ...]
    volume_compared: bool = False
    full_strategy_semantics_evaluated: bool = False


@dataclass(frozen=True, slots=True)
class ProviderEquivalenceAggregate:
    expected_pair_count: int
    evaluated_pair_count: int
    pass_count: int
    review_count: int
    fail_count: int
    status: str
    source_switch_authorized: bool
    full_strategy_signal_equivalence_status: str
    pair_results: tuple[ProviderPairEquivalence, ...]


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("percentile requires values")
    if not 0 <= fraction <= 1:
        raise ValueError("fraction must be between 0 and 1")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _symmetric_bps(left: float, right: float) -> float:
    denominator = (abs(left) + abs(right)) / 2.0
    if denominator <= 0:
        raise ProviderEquivalenceError("price comparison denominator must be positive")
    return abs(left - right) / denominator * 10_000.0


def _direction(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _grade_upper(value: float, *, passed: float, review: float) -> str:
    if value <= passed:
        return "PASS"
    if value <= review:
        return "REVIEW"
    return "FAIL"


def _grade_lower(value: float, *, passed: float, review: float) -> str:
    if value >= passed:
        return "PASS"
    if value >= review:
        return "REVIEW"
    return "FAIL"


def _overall_status(grades: list[str]) -> str:
    if "FAIL" in grades:
        return "FAIL"
    if "REVIEW" in grades:
        return "REVIEW"
    return "PASS"


def _setup_state(snapshot) -> tuple[bool, bool, bool] | None:
    if snapshot.ema20 is None or snapshot.ema50 is None or snapshot.ema20_slope is None:
        return None
    return (
        snapshot.ema20 > snapshot.ema50,
        snapshot.ema20_slope > 0,
        snapshot.close > snapshot.ema20,
    )


def compare_provider_pair(
    *,
    pionex_symbol: str,
    binance_symbol: str,
    interval: str,
    pionex_candles: list[Candle] | tuple[Candle, ...],
    binance_candles: list[Candle] | tuple[Candle, ...],
    policy: ProviderEquivalencePolicy = ProviderEquivalencePolicy(),
) -> ProviderPairEquivalence:
    """Compare one exact overlap pair without volume equivalence assumptions.

    Volume is deliberately excluded because it is venue-specific. V0.1 evaluates
    exact timestamp coverage, OHLC proximity, close-to-close direction and, for
    60M, the already-frozen EMA20/EMA50/slope/close setup state.
    """

    if not pionex_symbol.strip() or not binance_symbol.strip():
        raise ValueError("provider symbols are required")
    if interval not in {"15M", "60M", "4H"}:
        raise ValueError("interval must be 15M, 60M or 4H")

    left = tuple(pionex_candles)
    right = tuple(binance_candles)
    left_audit = audit_candles(left, interval)
    right_audit = audit_candles(right, interval)
    if not left_audit.ok:
        raise ProviderEquivalenceError(f"Pionex candle audit failed: {left_audit}")
    if not right_audit.ok:
        raise ProviderEquivalenceError(f"Binance candle audit failed: {right_audit}")

    left_by_time = {candle.time_ms: candle for candle in left}
    right_by_time = {candle.time_ms: candle for candle in right}
    left_times = set(left_by_time)
    right_times = set(right_by_time)
    missing_in_pionex = len(right_times - left_times)
    missing_in_binance = len(left_times - right_times)
    timestamp_exact = left_times == right_times and len(left) == len(right)

    reasons: list[str] = []
    grades: list[str] = []
    min_rows = policy.min_rows(interval)
    if len(left) < min_rows or len(right) < min_rows:
        reasons.append(f"insufficient_rows_min_{min_rows}")
        grades.append("FAIL")
    if not timestamp_exact:
        reasons.append("timestamp_sets_not_exact")
        grades.append("FAIL")
        return ProviderPairEquivalence(
            pionex_symbol=pionex_symbol,
            binance_symbol=binance_symbol,
            interval=interval,
            pionex_rows=len(left),
            binance_rows=len(right),
            timestamp_exact=False,
            missing_in_pionex=missing_in_pionex,
            missing_in_binance=missing_in_binance,
            median_ohlc_bps=None,
            p95_open_close_bps=None,
            p95_high_low_bps=None,
            return_direction_agreement=None,
            setup_60m_ready_bars=None,
            setup_60m_agreement=None,
            status="FAIL",
            reasons=tuple(reasons),
        )
    if not left:
        reasons.append("empty_overlap")
        return ProviderPairEquivalence(
            pionex_symbol=pionex_symbol,
            binance_symbol=binance_symbol,
            interval=interval,
            pionex_rows=0,
            binance_rows=0,
            timestamp_exact=True,
            missing_in_pionex=0,
            missing_in_binance=0,
            median_ohlc_bps=None,
            p95_open_close_bps=None,
            p95_high_low_bps=None,
            return_direction_agreement=None,
            setup_60m_ready_bars=None,
            setup_60m_agreement=None,
            status="FAIL",
            reasons=tuple(reasons),
        )

    ordered_times = sorted(left_times)
    ohlc_diffs: list[float] = []
    open_close_diffs: list[float] = []
    high_low_diffs: list[float] = []
    left_closes: list[float] = []
    right_closes: list[float] = []
    for time_ms in ordered_times:
        l = left_by_time[time_ms]
        r = right_by_time[time_ms]
        open_diff = _symmetric_bps(l.open, r.open)
        high_diff = _symmetric_bps(l.high, r.high)
        low_diff = _symmetric_bps(l.low, r.low)
        close_diff = _symmetric_bps(l.close, r.close)
        ohlc_diffs.extend((open_diff, high_diff, low_diff, close_diff))
        open_close_diffs.extend((open_diff, close_diff))
        high_low_diffs.extend((high_diff, low_diff))
        left_closes.append(l.close)
        right_closes.append(r.close)

    median_ohlc = _percentile(ohlc_diffs, 0.50)
    p95_open_close = _percentile(open_close_diffs, 0.95)
    p95_high_low = _percentile(high_low_diffs, 0.95)
    for metric_name, grade in (
        (
            "median_ohlc_bps",
            _grade_upper(
                median_ohlc,
                passed=policy.median_ohlc_bps_pass,
                review=policy.median_ohlc_bps_review,
            ),
        ),
        (
            "p95_open_close_bps",
            _grade_upper(
                p95_open_close,
                passed=policy.p95_open_close_bps_pass,
                review=policy.p95_open_close_bps_review,
            ),
        ),
        (
            "p95_high_low_bps",
            _grade_upper(
                p95_high_low,
                passed=policy.p95_high_low_bps_pass,
                review=policy.p95_high_low_bps_review,
            ),
        ),
    ):
        grades.append(grade)
        if grade != "PASS":
            reasons.append(f"{metric_name}_{grade.lower()}")

    direction_total = max(0, len(ordered_times) - 1)
    direction_matches = 0
    for index in range(1, len(ordered_times)):
        left_return = left_closes[index] - left_closes[index - 1]
        right_return = right_closes[index] - right_closes[index - 1]
        if _direction(left_return) == _direction(right_return):
            direction_matches += 1
    direction_agreement = direction_matches / direction_total if direction_total else 1.0
    direction_grade = _grade_lower(
        direction_agreement,
        passed=policy.return_direction_agreement_pass,
        review=policy.return_direction_agreement_review,
    )
    grades.append(direction_grade)
    if direction_grade != "PASS":
        reasons.append(f"return_direction_agreement_{direction_grade.lower()}")

    setup_ready_bars: int | None = None
    setup_agreement: float | None = None
    if interval == "60M":
        left_series = build_technical_series(left, interval)
        right_series = build_technical_series(right, interval)
        setup_pairs = []
        for l_snapshot, r_snapshot in zip(left_series, right_series, strict=True):
            l_state = _setup_state(l_snapshot)
            r_state = _setup_state(r_snapshot)
            if l_state is not None and r_state is not None:
                setup_pairs.append((l_state, r_state))
        setup_ready_bars = len(setup_pairs)
        if setup_ready_bars < policy.min_ready_setup_bars_60m:
            grades.append("FAIL")
            reasons.append(f"insufficient_60m_setup_ready_bars_min_{policy.min_ready_setup_bars_60m}")
        else:
            setup_matches = sum(left_state == right_state for left_state, right_state in setup_pairs)
            setup_agreement = setup_matches / setup_ready_bars
            setup_grade = _grade_lower(
                setup_agreement,
                passed=policy.setup_60m_agreement_pass,
                review=policy.setup_60m_agreement_review,
            )
            grades.append(setup_grade)
            if setup_grade != "PASS":
                reasons.append(f"setup_60m_agreement_{setup_grade.lower()}")

    status = _overall_status(grades)
    return ProviderPairEquivalence(
        pionex_symbol=pionex_symbol,
        binance_symbol=binance_symbol,
        interval=interval,
        pionex_rows=len(left),
        binance_rows=len(right),
        timestamp_exact=True,
        missing_in_pionex=0,
        missing_in_binance=0,
        median_ohlc_bps=median_ohlc,
        p95_open_close_bps=p95_open_close,
        p95_high_low_bps=p95_high_low,
        return_direction_agreement=direction_agreement,
        setup_60m_ready_bars=setup_ready_bars,
        setup_60m_agreement=setup_agreement,
        status=status,
        reasons=tuple(reasons),
    )


def aggregate_provider_equivalence(
    results: list[ProviderPairEquivalence] | tuple[ProviderPairEquivalence, ...],
    *,
    expected_pair_count: int = 45,
    policy: ProviderEquivalencePolicy = ProviderEquivalencePolicy(),
) -> ProviderEquivalenceAggregate:
    source = tuple(results)
    if expected_pair_count <= 0:
        raise ValueError("expected_pair_count must be positive")
    identities = [(item.pionex_symbol, item.binance_symbol, item.interval) for item in source]
    if len(set(identities)) != len(identities):
        raise ProviderEquivalenceError("duplicate provider-equivalence pair identity")

    pass_count = sum(item.status == "PASS" for item in source)
    review_count = sum(item.status == "REVIEW" for item in source)
    fail_count = sum(item.status == "FAIL" for item in source)
    if len(source) != expected_pair_count:
        status = "FAIL"
    elif fail_count:
        status = "FAIL"
    elif review_count:
        review_fraction = review_count / expected_pair_count
        status = (
            "REVIEW"
            if review_fraction <= policy.max_review_fraction_for_aggregate_review
            else "FAIL"
        )
    else:
        status = "PASS"

    # V0.1 cannot authorize a full provider source switch because six mandatory
    # entry/setup semantics are still UNDEFINED in Strategy Replay Readiness.
    # A future version must explicitly add and validate those dimensions.
    return ProviderEquivalenceAggregate(
        expected_pair_count=expected_pair_count,
        evaluated_pair_count=len(source),
        pass_count=pass_count,
        review_count=review_count,
        fail_count=fail_count,
        status=status,
        source_switch_authorized=False,
        full_strategy_signal_equivalence_status="DEFERRED_UNDEFINED_STRATEGY_RULES",
        pair_results=tuple(
            sorted(source, key=lambda item: (item.pionex_symbol, item.interval, item.binance_symbol))
        ),
    )
