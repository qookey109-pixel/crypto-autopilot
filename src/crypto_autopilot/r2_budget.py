from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class R2Pricing:
    free_storage_gb_month: float
    storage_usd_per_gb_month: float
    free_class_a_requests_per_month: int
    class_a_usd_per_million: float
    free_class_b_requests_per_month: int
    class_b_usd_per_million: float


@dataclass(frozen=True, slots=True)
class R2Guardrails:
    storage_warn_gb_month: float
    storage_block_gb_month: float
    class_a_warn_requests_per_month: int
    class_a_block_requests_per_month: int
    class_b_warn_requests_per_month: int
    class_b_block_requests_per_month: int


@dataclass(frozen=True, slots=True)
class R2ProjectedUsage:
    storage_gb_month: float
    class_a_requests_per_month: int
    class_b_requests_per_month: int


def _severity(value: float, warn: float, block: float) -> str:
    if value > block:
        return "BLOCK"
    if value > warn:
        return "WARN"
    return "PASS"


def _rounded_billable_units(value: float, free: float, unit: float) -> int:
    overage = max(0.0, value - free)
    if overage <= 0:
        return 0
    return math.ceil(overage / unit)


def evaluate_r2_budget(
    usage: R2ProjectedUsage,
    pricing: R2Pricing,
    guardrails: R2Guardrails,
) -> dict[str, Any]:
    if usage.storage_gb_month < 0:
        raise ValueError("storage_gb_month cannot be negative")
    if usage.class_a_requests_per_month < 0 or usage.class_b_requests_per_month < 0:
        raise ValueError("request counts cannot be negative")

    component_status = {
        "storage": _severity(
            usage.storage_gb_month,
            guardrails.storage_warn_gb_month,
            guardrails.storage_block_gb_month,
        ),
        "class_a": _severity(
            usage.class_a_requests_per_month,
            guardrails.class_a_warn_requests_per_month,
            guardrails.class_a_block_requests_per_month,
        ),
        "class_b": _severity(
            usage.class_b_requests_per_month,
            guardrails.class_b_warn_requests_per_month,
            guardrails.class_b_block_requests_per_month,
        ),
    }
    status = (
        "BLOCK"
        if "BLOCK" in component_status.values()
        else "WARN"
        if "WARN" in component_status.values()
        else "PASS"
    )

    billable_storage_gb = _rounded_billable_units(
        usage.storage_gb_month,
        pricing.free_storage_gb_month,
        1.0,
    )
    billable_class_a_millions = _rounded_billable_units(
        float(usage.class_a_requests_per_month),
        float(pricing.free_class_a_requests_per_month),
        1_000_000.0,
    )
    billable_class_b_millions = _rounded_billable_units(
        float(usage.class_b_requests_per_month),
        float(pricing.free_class_b_requests_per_month),
        1_000_000.0,
    )

    storage_cost = billable_storage_gb * pricing.storage_usd_per_gb_month
    class_a_cost = billable_class_a_millions * pricing.class_a_usd_per_million
    class_b_cost = billable_class_b_millions * pricing.class_b_usd_per_million

    return {
        "schema_version": 1,
        "status": status,
        "component_status": component_status,
        "projected_usage": asdict(usage),
        "billable_after_free_tier_rounding": {
            "storage_gb_month": billable_storage_gb,
            "class_a_million_request_units": billable_class_a_millions,
            "class_b_million_request_units": billable_class_b_millions,
        },
        "estimated_monthly_cost_usd": {
            "storage": round(storage_cost, 6),
            "class_a": round(class_a_cost, 6),
            "class_b": round(class_b_cost, 6),
            "total": round(storage_cost + class_a_cost + class_b_cost, 6),
        },
    }
