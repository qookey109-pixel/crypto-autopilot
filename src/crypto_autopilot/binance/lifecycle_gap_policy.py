from __future__ import annotations

from typing import Any


POLICY_ID = "binance-usdm-lifecycle-gap-v0.1"

# Operational classification only. These entries do not assert that an exchange
# lifecycle event is the historically proven cause of each gap. They authorize
# accepting only the exact checksum-pinned Binance Vision monthly archives below
# while preserving their missing timestamps unchanged.
_ALLOWANCES: tuple[dict[str, Any], ...] = (
    {
        "symbol": "CTKUSDT",
        "interval": "15m",
        "period": "2025-04",
        "monthly_sha256": "bd77c44d0061511b2e8f5c140a06ad2dd30007c640586fad5b035d71b0c3c61c",
        "row_count": 2839,
        "gap_count": 1,
        "missing_bars": 41,
        "gap_previous_time_ms": 1745970300000,
        "gap_next_time_ms": 1746008100000,
        "evidence": "research/receipts/2026-09-12-ctk-official-lifecycle-evidence-v0-4.json",
    },
    {
        "symbol": "CTKUSDT",
        "interval": "1h",
        "period": "2025-04",
        "monthly_sha256": "1fe1c295babc4481dd5c5e9145b68e2bacafe3c6e262528854f8de903ac14b25",
        "row_count": 710,
        "gap_count": 1,
        "missing_bars": 10,
        "gap_previous_time_ms": 1745967600000,
        "gap_next_time_ms": 1746007200000,
        "evidence": "research/receipts/2026-09-12-ctk-official-lifecycle-evidence-v0-4.json",
    },
    {
        "symbol": "CTKUSDT",
        "interval": "4h",
        "period": "2025-04",
        "monthly_sha256": "08ce76f52b01e9151d64e5df72dca9c5af36ebb41afa9b397edd43fec799862f",
        "row_count": 178,
        "gap_count": 1,
        "missing_bars": 2,
        "gap_previous_time_ms": 1745956800000,
        "gap_next_time_ms": 1746000000000,
        "evidence": "research/receipts/2026-09-12-ctk-official-lifecycle-evidence-v0-4.json",
    },
    {
        "symbol": "LITUSDT",
        "interval": "15m",
        "period": "2025-12",
        "monthly_sha256": "246dca9c1bcc046af274cc4d5b61fdd1fb818f243a2ae3c82a20471bdecdd160",
        "row_count": 2906,
        "gap_count": 1,
        "missing_bars": 70,
        "evidence": "config/lit_archive_diagnosis_v0_1.json",
    },
)


def reviewed_allowances() -> tuple[dict[str, Any], ...]:
    """Return defensive copies for CI/config drift checks."""
    return tuple(dict(entry) for entry in _ALLOWANCES)


def match_lifecycle_gap(key: Any, *, archive_sha256: str, audit: Any) -> str | None:
    """Return POLICY_ID only when an observed gap exactly matches the reviewed allowlist.

    Archive SHA pinning is part of the match. No rows are synthesized or removed.
    Any duplicate, ordering, alignment or candle-validity defect remains rejected.
    """
    if key.dataset != "klines" or key.frequency != "monthly":
        return None
    if (
        audit.duplicate_timestamps
        or audit.out_of_order_pairs
        or audit.misaligned_timestamps
        or audit.invalid_candle_timestamps
    ):
        return None

    for entry in _ALLOWANCES:
        if (
            key.symbol != entry["symbol"]
            or key.interval != entry["interval"]
            or key.period != entry["period"]
            or archive_sha256 != entry["monthly_sha256"]
            or audit.count != entry["row_count"]
            or len(audit.gaps) != entry["gap_count"]
            or sum(gap.missing_bars for gap in audit.gaps) != entry["missing_bars"]
        ):
            continue
        previous = entry.get("gap_previous_time_ms")
        next_time = entry.get("gap_next_time_ms")
        if previous is not None or next_time is not None:
            if len(audit.gaps) != 1:
                continue
            gap = audit.gaps[0]
            if gap.previous_time_ms != previous or gap.next_time_ms != next_time:
                continue
        return POLICY_ID
    return None
