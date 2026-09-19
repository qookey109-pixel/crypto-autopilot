from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

SOURCE_IDS: Final[tuple[str, ...]] = (
    "crypto_orderbook_mcp",
    "crypto_liquidations_mcp",
    "pulse_verity",
    "crypto_rss_mcp",
    "crypto_sentiment_mcp",
    "crypto_trending_mcp",
)

_SYMBOL_SPECIFIC: Final[frozenset[str]] = frozenset(
    {
        "crypto_orderbook_mcp",
        "crypto_liquidations_mcp",
        "pulse_verity",
        "crypto_sentiment_mcp",
    }
)


@dataclass(frozen=True, slots=True)
class ExternalMarketContextPolicy:
    prefetched_evidence_ingestion_authorized: bool = True
    network_capture_authorized: bool = False
    mcp_runtime_embedding_authorized: bool = False
    provider_api_key_storage_authorized: bool = False
    external_text_instruction_authority: bool = False
    strategy_router_threshold_change_authorized: bool = False
    daily_opportunity_score_change_authorized: bool = False
    automatic_candidate_generation_authorized: bool = False
    automatic_strategy_selection_authorized: bool = False
    r2_write_authorized: bool = False
    holdout_access_authorized: bool = False
    training_authorized: bool = False
    model_promotion_authorized: bool = False
    real_money_order_authorized: bool = False
    live_real_trading_authorized: bool = False

    def __post_init__(self) -> None:
        values = (
            self.prefetched_evidence_ingestion_authorized,
            self.network_capture_authorized,
            self.mcp_runtime_embedding_authorized,
            self.provider_api_key_storage_authorized,
            self.external_text_instruction_authority,
            self.strategy_router_threshold_change_authorized,
            self.daily_opportunity_score_change_authorized,
            self.automatic_candidate_generation_authorized,
            self.automatic_strategy_selection_authorized,
            self.r2_write_authorized,
            self.holdout_access_authorized,
            self.training_authorized,
            self.model_promotion_authorized,
            self.real_money_order_authorized,
            self.live_real_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in values):
            raise ValueError("external market context policy flags must be booleans")
        if not self.prefetched_evidence_ingestion_authorized:
            raise ValueError("V0.1 requires prefetched evidence ingestion")
        if any(values[1:]):
            raise ValueError(
                "External Market Context V0.1 cannot grant network, routing, "
                "training, storage or trading authority"
            )


def _clean_symbol(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("symbol is required")
    symbol = value.strip().upper()
    if any(character.isspace() for character in symbol):
        raise ValueError("symbol cannot contain whitespace")
    return symbol


def _non_negative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _finite_number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{label} must be finite")
    return number


def _positive_number(value: object, label: str) -> float:
    number = _finite_number(value, label)
    if number <= 0:
        raise ValueError(f"{label} must be positive")
    return number


def _clean_external_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty string")
    text = value.strip()
    if len(text) > 240:
        raise ValueError(f"{label} is too long")
    if any(ord(character) < 32 and character not in "\t" for character in text):
        raise ValueError(f"{label} contains control characters")
    return text


def _normalize_orderbook(payload: Mapping[str, object]) -> dict[str, object]:
    exchange = payload.get("exchange")
    if not isinstance(exchange, str) or not exchange.strip():
        raise ValueError("orderbook exchange is required")
    bid_depth = _finite_number(payload.get("bid_depth"), "bid_depth")
    ask_depth = _finite_number(payload.get("ask_depth"), "ask_depth")
    if bid_depth < 0 or ask_depth < 0:
        raise ValueError("orderbook depths cannot be negative")
    imbalance = _finite_number(payload.get("imbalance"), "imbalance")
    if not -1.0 <= imbalance <= 1.0:
        raise ValueError("orderbook imbalance must be within [-1, 1]")
    return {
        "exchange": exchange.strip().lower(),
        "bid_depth": bid_depth,
        "ask_depth": ask_depth,
        "imbalance": imbalance,
        "mid_price": _positive_number(payload.get("mid_price"), "mid_price"),
    }


def _normalize_liquidations(payload: Mapping[str, object]) -> dict[str, object]:
    events = payload.get("events")
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        raise ValueError("liquidation events must be an array")
    buy_notional = 0.0
    sell_notional = 0.0
    count = 0
    for row in events:
        if not isinstance(row, Mapping):
            raise ValueError("liquidation event must be an object")
        side = row.get("side")
        if not isinstance(side, str) or side.upper() not in {"BUY", "SELL"}:
            raise ValueError("liquidation side must be BUY or SELL")
        notional = _positive_number(row.get("price"), "liquidation price") * _positive_number(
            row.get("quantity"),
            "liquidation quantity",
        )
        if side.upper() == "BUY":
            buy_notional += notional
        else:
            sell_notional += notional
        count += 1
    gross = buy_notional + sell_notional
    imbalance = 0.0 if gross == 0.0 else (buy_notional - sell_notional) / gross
    return {
        "event_count": count,
        "buy_notional": buy_notional,
        "sell_notional": sell_notional,
        "gross_notional": gross,
        "side_imbalance": imbalance,
    }


def _normalize_pulse(
    payload: Mapping[str, object],
    as_of_ms: int,
) -> dict[str, object]:
    verified = payload.get("signature_verified")
    if not isinstance(verified, bool):
        raise ValueError("pulse signature_verified must be boolean")
    grade = payload.get("grade")
    if not isinstance(grade, str) or not grade.strip():
        raise ValueError("pulse grade is required")
    print_timestamp_ms = _non_negative_int(
        payload.get("print_timestamp_ms"),
        "print_timestamp_ms",
    )
    if print_timestamp_ms > as_of_ms:
        raise ValueError("future Pulse print is not causally available")
    return {
        "price": _positive_number(payload.get("price"), "pulse price"),
        "grade": grade.strip().lower(),
        "signature_verified": verified,
        "print_timestamp_ms": print_timestamp_ms,
    }


def _normalize_rss(payload: Mapping[str, object], as_of_ms: int) -> dict[str, object]:
    entries = payload.get("entries")
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
        raise ValueError("rss entries must be an array")
    titles: list[str] = []
    latest_published_ms: int | None = None
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("rss entry must be an object")
        title = _clean_external_text(entry.get("title"), "rss entry title")
        published_ms = _non_negative_int(entry.get("published_ms"), "rss published_ms")
        if published_ms > as_of_ms:
            raise ValueError("future rss entry is not causally available")
        titles.append(title)
        latest_published_ms = (
            published_ms
            if latest_published_ms is None
            else max(latest_published_ms, published_ms)
        )
    return {
        "article_count": len(entries),
        "latest_published_ms": latest_published_ms,
        "titles": titles[:20],
    }


def _normalize_sentiment(payload: Mapping[str, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    for field in ("sentiment_balance", "social_volume", "social_dominance"):
        if field in payload and payload[field] is not None:
            result[field] = _finite_number(payload[field], field)
    words = payload.get("trending_words")
    if words is not None:
        if not isinstance(words, Sequence) or isinstance(words, (str, bytes)):
            raise ValueError("trending_words must be an array")
        cleaned: list[str] = []
        for word in words:
            cleaned.append(_clean_external_text(word, "trending word"))
        result["trending_words"] = cleaned[:20]
    if not result:
        raise ValueError("sentiment payload contains no supported metrics")
    return result


def _normalize_trending(payload: Mapping[str, object]) -> dict[str, object]:
    rank = payload.get("rank")
    if not isinstance(rank, int) or isinstance(rank, bool) or rank < 1:
        raise ValueError("trending rank must be a positive integer")
    result: dict[str, object] = {"rank": rank}
    for field in (
        "price",
        "change_1h_pct",
        "change_24h_pct",
        "change_7d_pct",
        "volume_24h",
        "market_cap",
    ):
        if field in payload and payload[field] is not None:
            result[field] = _finite_number(payload[field], field)
    return result


def _normalize_payload(
    source_id: str,
    payload: Mapping[str, object],
    as_of_ms: int,
) -> dict[str, object]:
    if source_id == "crypto_orderbook_mcp":
        return _normalize_orderbook(payload)
    if source_id == "crypto_liquidations_mcp":
        return _normalize_liquidations(payload)
    if source_id == "pulse_verity":
        return _normalize_pulse(payload, as_of_ms)
    if source_id == "crypto_rss_mcp":
        return _normalize_rss(payload, as_of_ms)
    if source_id == "crypto_sentiment_mcp":
        return _normalize_sentiment(payload)
    if source_id == "crypto_trending_mcp":
        return _normalize_trending(payload)
    raise ValueError(f"unsupported external market context source: {source_id}")


def build_external_market_context_snapshot(
    *,
    symbol: str,
    as_of_ms: int,
    evidence: Sequence[Mapping[str, object]],
    policy: ExternalMarketContextPolicy = ExternalMarketContextPolicy(),
) -> dict[str, object]:
    """Normalize already-fetched external evidence without performing I/O."""

    if not policy.prefetched_evidence_ingestion_authorized:
        raise ValueError("prefetched evidence ingestion is not authorized")
    clean_symbol = _clean_symbol(symbol)
    decision_time = _non_negative_int(as_of_ms, "as_of_ms")
    seen: set[str] = set()
    normalized: dict[str, object] = {}

    for row in evidence:
        if not isinstance(row, Mapping):
            raise ValueError("external evidence row must be an object")
        source_id = row.get("source_id")
        if not isinstance(source_id, str) or source_id not in SOURCE_IDS:
            raise ValueError("unsupported external evidence source_id")
        if source_id in seen:
            raise ValueError(f"duplicate external evidence source: {source_id}")
        seen.add(source_id)

        observed_at_ms = _non_negative_int(
            row.get("observed_at_ms"),
            "observed_at_ms",
        )
        available_at_ms = _non_negative_int(
            row.get("available_at_ms"),
            "available_at_ms",
        )
        if observed_at_ms > available_at_ms:
            raise ValueError("external evidence cannot be available before observation")
        if available_at_ms > decision_time:
            raise ValueError("future external evidence is not causally available")

        evidence_symbol = row.get("symbol")
        if source_id in _SYMBOL_SPECIFIC:
            if _clean_symbol(evidence_symbol) != clean_symbol:
                raise ValueError(f"{source_id} evidence belongs to another symbol")
        elif evidence_symbol is not None and _clean_symbol(evidence_symbol) != clean_symbol:
            raise ValueError(f"{source_id} evidence belongs to another symbol")

        payload = row.get("payload")
        if not isinstance(payload, Mapping):
            raise ValueError("external evidence payload must be an object")
        normalized[source_id] = {
            "observed_at_ms": observed_at_ms,
            "available_at_ms": available_at_ms,
            "data": _normalize_payload(source_id, payload, decision_time),
        }

    return {
        "schema": "qookey-external-market-context-snapshot-v0.1",
        "symbol": clean_symbol,
        "as_of_ms": decision_time,
        "sources_present": sorted(normalized),
        "sources": normalized,
        "authority": {
            "prefetched_evidence_ingestion_only": True,
            "network_capture_authorized": False,
            "mcp_runtime_embedding_authorized": False,
            "provider_api_key_storage_authorized": False,
            "external_text_instruction_authority": False,
            "strategy_router_threshold_change_authorized": False,
            "daily_opportunity_score_change_authorized": False,
            "automatic_candidate_generation_authorized": False,
            "automatic_strategy_selection_authorized": False,
            "r2_write_authorized": False,
            "holdout_access_authorized": False,
            "training_authorized": False,
            "model_promotion_authorized": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
    }


def external_market_context_policy_from_config(
    payload: Mapping[str, object],
) -> ExternalMarketContextPolicy:
    if payload.get("schema") != "qookey-external-market-context-sources-v0.1":
        raise ValueError("unsupported external market context config")
    source_rows = payload.get("sources")
    policy = payload.get("policy")
    if not isinstance(source_rows, list) or not isinstance(policy, Mapping):
        raise ValueError("external market context sources/policy are required")
    source_ids: list[str] = []
    for row in source_rows:
        if not isinstance(row, Mapping):
            raise ValueError("external source registry row must be an object")
        source_id = row.get("source_id")
        if not isinstance(source_id, str):
            raise ValueError("external source registry source_id must be string")
        source_ids.append(source_id)
    if sorted(source_ids) != sorted(SOURCE_IDS):
        raise ValueError("external market context source registry mismatch")
    for row in source_rows:
        sha = row.get("upstream_commit_sha")
        if not isinstance(sha, str) or len(sha) != 40:
            raise ValueError("external source commit pin must be a 40-character SHA")
        if row.get("network_capture_authorized") is not False:
            raise ValueError("external source network capture must remain closed in V0.1")

    keys = (
        "prefetched_evidence_ingestion_authorized",
        "network_capture_authorized",
        "mcp_runtime_embedding_authorized",
        "provider_api_key_storage_authorized",
        "external_text_instruction_authority",
        "strategy_router_threshold_change_authorized",
        "daily_opportunity_score_change_authorized",
        "automatic_candidate_generation_authorized",
        "automatic_strategy_selection_authorized",
        "r2_write_authorized",
        "holdout_access_authorized",
        "training_authorized",
        "model_promotion_authorized",
        "real_money_order_authorized",
        "live_real_trading_authorized",
    )
    values: dict[str, bool] = {}
    for key in keys:
        value = policy.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")
        values[key] = value
    return ExternalMarketContextPolicy(**values)
