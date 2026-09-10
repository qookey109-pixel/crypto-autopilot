"""Fixed pre-holdout capacity sample; no provider requests at import time."""
from datetime import datetime, timezone
import hashlib
import json

from ..historical import INTERVAL_MS, audit_candles


class PilotRejected(RuntimeError):
    pass


def stamp(text):
    return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() * 1000)


def now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def require_window(config, clock):
    now = clock()
    if not stamp(config["not_before_utc"]) <= now < stamp(config["stop_exclusive_utc"]):
        raise PilotRejected("execution window closed")
    start, end = stamp(config["start_utc"]), stamp(config["end_exclusive_utc"])
    if not start < end <= stamp("2026-08-28T00:00:00Z"):
        raise PilotRejected("requested range overlaps protected period")
    for interval in config["intervals"]:
        step = INTERVAL_MS[interval]
        if start % step or end % step or end > now:
            raise PilotRejected("invalid or unfinished range")
        # A conservative margin below the documented 10,000-record horizon.
        if now - start >= config["maximum_provider_lookback_bars"] * step:
            raise PilotRejected("fixed sample outside conservative provider horizon")


def collect(config, client, clock, progress):
    """Require exact endpoints and every bar; never turn errors into EOF."""
    start, end = stamp(config["start_utc"]), stamp(config["end_exclusive_utc"])
    collected = {}
    for interval in config["intervals"]:
        step = INTERVAL_MS[interval]
        cursor, bars = end - step, {}
        while cursor >= start:
            require_window(config, clock)
            if progress["requests"] >= config["maximum_requests"]:
                raise PilotRejected("request budget exhausted")
            limit = min(config["page_limit"], (cursor - start) // step + 1)
            progress["requests"] += 1
            try:
                page = client.get_klines(config["symbol"], interval, limit=limit, end_time_ms=cursor)
            except Exception:
                raise PilotRejected("provider request rejected; no retry or partial publication") from None
            # Check timestamps before any OHLCV evaluation, and do not publish
            # raw responses. Unexpected provider data cannot prove non-access.
            if any(not start <= c.time_ms <= cursor for c in page):
                progress["holdout_accessed"] = "UNVERIFIED_PROVIDER_RANGE_VIOLATION"
                raise PilotRejected("provider returned timestamps outside requested range")
            if not page or len(page) != limit or not audit_candles(page, interval).ok:
                raise PilotRejected("missing, duplicate, unordered or invalid page")
            if page[-1].time_ms != cursor or page[0].time_ms != cursor - (limit - 1) * step:
                raise PilotRejected("page endpoints incomplete")
            if any(c.time_ms in bars for c in page):
                raise PilotRejected("repeated page")
            bars.update((c.time_ms, c) for c in page)
            cursor = page[0].time_ms - step
        candles = tuple(bars[t] for t in sorted(bars))
        if len(candles) != (end - start) // step or not audit_candles(candles, interval).ok:
            raise PilotRejected("fixed range incomplete")
        collected[interval] = candles
    return collected
