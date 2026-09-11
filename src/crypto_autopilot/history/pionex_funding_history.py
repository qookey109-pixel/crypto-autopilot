from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from crypto_autopilot.features.market import FundingRateObservation


class PionexFundingHistoryRejected(RuntimeError):
    pass


class FundingHistoryClient(Protocol):
    def get_funding_rates(
        self,
        symbol: str,
        *,
        limit: int = 100,
        end_time_ms: int | None = None,
    ) -> list[FundingRateObservation]: ...


@dataclass(frozen=True, slots=True)
class BoundedFundingHistory:
    symbol: str
    observations: tuple[FundingRateObservation, ...]
    requests: int
    left_boundary_reached: bool
    first_time_ms: int
    last_time_ms: int


def _stamp(text: str) -> int:
    return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() * 1000)


def collect_bounded_funding_history(
    config: dict,
    client: FundingHistoryClient,
) -> BoundedFundingHistory:
    """Collect one bounded public Pionex funding window without cadence invention."""

    source = config["source"]
    completeness = config["completeness"]
    symbol = str(source["symbol"])
    start_ms = _stamp(str(source["start_utc"]))
    end_ms = _stamp(str(source["end_exclusive_utc"]))
    limit = int(source["page_limit"])
    maximum_requests = int(source["maximum_requests"])

    if (
        source.get("provider") != "pionex_public_futures"
        or source.get("authentication") != "NONE_PUBLIC"
        or source.get("first_end_time_policy") != "END_EXCLUSIVE_MINUS_1_MS"
        or source.get("pagination") != "DESCENDING_END_TIME_FROM_OLDEST_MINUS_1_MS"
        or int(source.get("retry_count", -1)) != 0
        or not start_ms < end_ms
        or not 1 <= limit <= 500
        or maximum_requests < 1
    ):
        raise PionexFundingHistoryRejected("prepared funding source contract mismatch")
    if (
        completeness.get("require_left_boundary_reached") is not True
        or completeness.get("require_strict_unique_timestamps") is not True
        or completeness.get("require_finite_rates") is not True
        or completeness.get("fixed_cadence_assumption") is not False
        or completeness.get("silent_gap_interpolation") is not False
        or completeness.get("zero_funding_fill") is not False
    ):
        raise PionexFundingHistoryRejected("prepared completeness policy widened")

    cursor = end_ms - 1
    requests = 0
    observations_by_time: dict[int, FundingRateObservation] = {}
    left_boundary_reached = False

    while requests < maximum_requests:
        requests += 1
        try:
            page = client.get_funding_rates(
                symbol,
                limit=limit,
                end_time_ms=cursor,
            )
        except Exception as exc:
            raise PionexFundingHistoryRejected(
                f"public funding request failed on request {requests}: {type(exc).__name__}"
            ) from None

        if not page:
            raise PionexFundingHistoryRejected(
                "funding history ended before the left boundary was proven"
            )

        ordered = sorted(page, key=lambda item: item.funding_time_ms)
        page_times: set[int] = set()
        for item in ordered:
            if item.symbol != symbol:
                raise PionexFundingHistoryRejected("funding symbol mismatch")
            if item.funding_time_ms < 0 or item.funding_time_ms > cursor:
                raise PionexFundingHistoryRejected("funding timestamp outside request cursor")
            if not math.isfinite(item.funding_rate):
                raise PionexFundingHistoryRejected("non-finite funding rate")
            if item.funding_time_ms in page_times or item.funding_time_ms in observations_by_time:
                raise PionexFundingHistoryRejected("duplicate funding timestamp")
            page_times.add(item.funding_time_ms)
            observations_by_time[item.funding_time_ms] = item

        oldest = ordered[0].funding_time_ms
        if oldest <= start_ms:
            left_boundary_reached = True
            break
        cursor = oldest - 1

    if not left_boundary_reached:
        raise PionexFundingHistoryRejected(
            "request budget exhausted before the left boundary was proven"
        )

    selected = tuple(
        observations_by_time[time_ms]
        for time_ms in sorted(observations_by_time)
        if start_ms <= time_ms < end_ms
    )
    minimum = int(completeness.get("minimum_in_window_observations", 1))
    if len(selected) < minimum:
        raise PionexFundingHistoryRejected("no funding observations in fixed window")

    return BoundedFundingHistory(
        symbol=symbol,
        observations=selected,
        requests=requests,
        left_boundary_reached=True,
        first_time_ms=selected[0].funding_time_ms,
        last_time_ms=selected[-1].funding_time_ms,
    )
