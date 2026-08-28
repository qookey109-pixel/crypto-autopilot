from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


INTERVALS = ("15m", "1h", "4h")
PROJECT_INTERVALS = {"15m": "15M", "1h": "60M", "4h": "4H"}
VISION_MONTHLY_ROOT = "data/futures/um/monthly/klines/"
_MONTH_RE = re.compile(r"^(20\d{2})-(0[1-9]|1[0-2])$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class DetailedHistoryAuthorityError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BucketListing:
    common_prefixes: tuple[str, ...]
    keys: tuple[str, ...]
    is_truncated: bool
    next_marker: str | None


@dataclass(frozen=True, slots=True)
class DetailedMarketCoverage:
    symbol: str
    base_asset: str
    quote_asset: str
    asset_class: str
    classification_method: str
    months_15m: tuple[str, ...]
    months_1h: tuple[str, ...]
    months_4h: tuple[str, ...]
    common_months: tuple[str, ...]
    first_common_month: str
    last_common_month: str
    common_month_count: int
    missing_common_months_inside_span: tuple[str, ...]
    reaches_window_end: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DetailedPartition:
    symbol: str
    asset_class: str
    interval: str
    project_interval: str
    period: str
    year: int
    month: int
    source_key: str
    checksum_key: str
    r2_key: str


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_month(value: str) -> tuple[int, int]:
    match = _MONTH_RE.fullmatch(value)
    if match is None:
        raise ValueError("month must be YYYY-MM")
    return int(match.group(1)), int(match.group(2))


def month_range(start: str, end: str) -> tuple[str, ...]:
    start_year, start_month = parse_month(start)
    end_year, end_month = parse_month(end)
    if (end_year, end_month) < (start_year, start_month):
        raise ValueError("end month must not be before start month")
    output: list[str] = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        output.append(f"{year:04d}-{month:02d}")
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return tuple(output)


def parse_bucket_listing(payload: bytes, *, expected_prefix: str) -> BucketListing:
    """Parse the anonymous Binance Vision S3 ListBucket XML response."""

    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise DetailedHistoryAuthorityError("invalid Binance Vision bucket listing XML") from exc

    namespace = "{http://s3.amazonaws.com/doc/2006-03-01/}"
    prefix = root.findtext(f"{namespace}Prefix")
    if prefix != expected_prefix:
        raise DetailedHistoryAuthorityError(
            f"Binance Vision listing prefix mismatch: {prefix!r} != {expected_prefix!r}"
        )
    common_prefixes = tuple(
        sorted(
            value
            for value in (
                item.findtext(f"{namespace}Prefix")
                for item in root.findall(f"{namespace}CommonPrefixes")
            )
            if value
        )
    )
    keys = tuple(
        sorted(
            value
            for value in (
                item.findtext(f"{namespace}Key")
                for item in root.findall(f"{namespace}Contents")
            )
            if value
        )
    )
    truncated = root.findtext(f"{namespace}IsTruncated") == "true"
    next_marker = root.findtext(f"{namespace}NextMarker")
    if truncated and not next_marker:
        candidates = [*keys, *common_prefixes]
        next_marker = max(candidates) if candidates else None
    if truncated and not next_marker:
        raise DetailedHistoryAuthorityError("truncated Binance Vision listing has no marker")
    return BucketListing(common_prefixes, keys, truncated, next_marker)


def symbols_from_root_prefixes(prefixes: Iterable[str]) -> tuple[str, ...]:
    symbols: list[str] = []
    for prefix in prefixes:
        if not prefix.startswith(VISION_MONTHLY_ROOT) or not prefix.endswith("/"):
            raise DetailedHistoryAuthorityError(f"unsafe Binance Vision symbol prefix: {prefix}")
        symbol = prefix[len(VISION_MONTHLY_ROOT) : -1]
        if (
            not symbol
            or not symbol.isascii()
            or not symbol.isalnum()
            or not symbol.endswith("USDT")
            or symbol.endswith("USDTSETTLED")
            or "SETTLED" in symbol
        ):
            continue
        symbols.append(symbol)
    return tuple(sorted(set(symbols)))


def months_from_interval_keys(
    keys: Iterable[str], *, symbol: str, interval: str
) -> tuple[str, ...]:
    if interval not in INTERVALS:
        raise ValueError("unsupported detailed-history interval")
    prefix = f"{VISION_MONTHLY_ROOT}{symbol}/{interval}/"
    archive_pattern = re.compile(
        rf"^{re.escape(prefix + symbol + '-' + interval + '-')}(20\d{{2}}-(?:0[1-9]|1[0-2]))\.zip$"
    )
    key_set = set(keys)
    periods = []
    for key in key_set:
        match = archive_pattern.fullmatch(key)
        if match is None:
            continue
        if f"{key}.CHECKSUM" not in key_set:
            continue
        periods.append(match.group(1))
    return tuple(sorted(set(periods)))


def classify_usdm_asset(
    base_asset: str,
    *,
    tokenized_stock_roots: Iterable[str],
    other_roots: Iterable[str],
) -> tuple[str, str]:
    base = base_asset.upper()
    stocks = {str(value).upper() for value in tokenized_stock_roots}
    others = {str(value).upper() for value in other_roots}
    if base in stocks:
        return "tokenized_stock_candidate", "explicit_futures_root_heuristic"
    if base in others:
        return "other", "explicit_non_crypto_root_heuristic"
    return "crypto", "default_usdm_symbol_heuristic"


def build_market_coverage(
    *,
    symbol: str,
    months_by_interval: Mapping[str, Sequence[str]],
    requested_months: Sequence[str],
    tokenized_stock_roots: Iterable[str],
    other_roots: Iterable[str],
) -> DetailedMarketCoverage | None:
    if not symbol.endswith("USDT"):
        raise ValueError("detailed-history symbols must be USDT quoted")
    base = symbol[: -len("USDT")]
    if not base:
        raise ValueError("symbol has no base asset")
    requested = tuple(requested_months)
    if not requested:
        raise ValueError("requested_months cannot be empty")
    requested_set = set(requested)
    normalized: dict[str, tuple[str, ...]] = {}
    for interval in INTERVALS:
        values = tuple(sorted({str(value) for value in months_by_interval.get(interval, ())}))
        for value in values:
            parse_month(value)
        normalized[interval] = tuple(value for value in values if value in requested_set)
    common = tuple(
        value
        for value in requested
        if all(value in set(normalized[interval]) for interval in INTERVALS)
    )
    if not common:
        return None
    first_index = requested.index(common[0])
    last_index = requested.index(common[-1])
    missing = tuple(
        value for value in requested[first_index : last_index + 1] if value not in set(common)
    )
    asset_class, method = classify_usdm_asset(
        base,
        tokenized_stock_roots=tokenized_stock_roots,
        other_roots=other_roots,
    )
    return DetailedMarketCoverage(
        symbol=symbol,
        base_asset=base,
        quote_asset="USDT",
        asset_class=asset_class,
        classification_method=method,
        months_15m=normalized["15m"],
        months_1h=normalized["1h"],
        months_4h=normalized["4h"],
        common_months=common,
        first_common_month=common[0],
        last_common_month=common[-1],
        common_month_count=len(common),
        missing_common_months_inside_span=missing,
        reaches_window_end=common[-1] == requested[-1],
    )


def _coverage_rank(item: DetailedMarketCoverage) -> tuple[int, int, int, str]:
    last_year, last_month = parse_month(item.last_common_month)
    return (-item.common_month_count, -(last_year * 100 + last_month), len(item.missing_common_months_inside_span), item.symbol)


def select_training_universe(
    records: Sequence[DetailedMarketCoverage],
    *,
    target_size: int,
    required_symbols: Sequence[str],
    minimum_tokenized_stock_candidates: int,
    minimum_historical_absence_candidates: int,
    minimum_window_end_candidates: int,
) -> tuple[DetailedMarketCoverage, ...]:
    if target_size < 1:
        raise ValueError("target_size must be positive")
    by_symbol = {item.symbol: item for item in records}
    if len(by_symbol) < target_size:
        raise DetailedHistoryAuthorityError(
            f"only {len(by_symbol)} markets have common detailed coverage; target is {target_size}"
        )
    missing_required = sorted(set(required_symbols) - set(by_symbol))
    if missing_required:
        raise DetailedHistoryAuthorityError(
            f"required continuity symbols lack common detailed coverage: {missing_required}"
        )

    selected: list[DetailedMarketCoverage] = []
    selected_symbols: set[str] = set()

    def add(items: Iterable[DetailedMarketCoverage], limit: int | None = None) -> None:
        added = 0
        for item in sorted(items, key=_coverage_rank):
            if item.symbol in selected_symbols or len(selected) >= target_size:
                continue
            selected.append(item)
            selected_symbols.add(item.symbol)
            added += 1
            if limit is not None and added >= limit:
                break

    add(by_symbol[symbol] for symbol in required_symbols)

    stock_candidates = [
        item for item in records if item.asset_class == "tokenized_stock_candidate"
    ]
    if len(stock_candidates) < minimum_tokenized_stock_candidates:
        raise DetailedHistoryAuthorityError(
            "insufficient tokenized-stock candidates for the frozen category minimum"
        )
    current_stock_candidates = sum(
        item.asset_class == "tokenized_stock_candidate" for item in selected
    )
    add(
        stock_candidates,
        max(0, minimum_tokenized_stock_candidates - current_stock_candidates),
    )

    historical = [item for item in records if not item.reaches_window_end]
    if len(historical) < minimum_historical_absence_candidates:
        raise DetailedHistoryAuthorityError(
            "insufficient historical-absence candidates for survivorship-bias evidence"
        )
    current_historical = sum(not item.reaches_window_end for item in selected)
    add(
        historical,
        max(0, minimum_historical_absence_candidates - current_historical),
    )

    recent = [item for item in records if item.reaches_window_end]
    if len(recent) < minimum_window_end_candidates:
        raise DetailedHistoryAuthorityError(
            "insufficient window-end candidates for the frozen recent-market minimum"
        )
    current_recent = sum(item.reaches_window_end for item in selected)
    add(recent, max(0, minimum_window_end_candidates - current_recent))
    add(records)

    if len(selected) != target_size:
        raise DetailedHistoryAuthorityError(
            f"universe selection produced {len(selected)} markets; expected {target_size}"
        )
    if (
        sum(item.asset_class == "tokenized_stock_candidate" for item in selected)
        < minimum_tokenized_stock_candidates
        or sum(not item.reaches_window_end for item in selected)
        < minimum_historical_absence_candidates
        or sum(item.reaches_window_end for item in selected)
        < minimum_window_end_candidates
    ):
        raise DetailedHistoryAuthorityError(
            "selected universe does not satisfy frozen category minimums"
        )
    return tuple(selected)


def build_catalog(
    records: Sequence[DetailedMarketCoverage],
    *,
    config: Mapping[str, Any],
    retrieved_at_utc: str,
) -> dict[str, Any]:
    scope = config["scope"]
    selection = config["selection"]
    selected = select_training_universe(
        records,
        target_size=int(scope["target_market_count"]),
        required_symbols=tuple(selection["required_continuity_symbols"]),
        minimum_tokenized_stock_candidates=int(
            selection["minimum_tokenized_stock_candidates"]
        ),
        minimum_historical_absence_candidates=int(
            selection["minimum_historical_absence_candidates"]
        ),
        minimum_window_end_candidates=int(selection["minimum_window_end_candidates"]),
    )
    shard_size = int(config["execution"]["symbols_per_shard"])
    markets = []
    for index, item in enumerate(selected):
        row = item.as_dict()
        row["selection_rank"] = index + 1
        row["shard_index"] = index // shard_size
        markets.append(row)
    shard_count = (len(markets) + shard_size - 1) // shard_size
    payload = {
        "schema": "binance-usdm-detailed-history-catalog-v0.1",
        "status": "PASS",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "retrieved_at_utc": retrieved_at_utc,
        "source_month_start": scope["source_month_start"],
        "source_month_end": scope["source_month_end"],
        "target_market_count": int(scope["target_market_count"]),
        "selected_market_count": len(markets),
        "eligible_market_count": len(records),
        "shard_size": shard_size,
        "shard_count": shard_count,
        "markets": markets,
        "selection_evidence": {
            "tokenized_stock_candidate_count": sum(
                item.asset_class == "tokenized_stock_candidate" for item in selected
            ),
            "historical_absence_candidate_count": sum(
                not item.reaches_window_end for item in selected
            ),
            "window_end_candidate_count": sum(item.reaches_window_end for item in selected),
            "classification_is_heuristic": True,
            "current_catalog_is_membership_authority": False,
        },
        "authority": {
            "historical_universe_membership_authorized": False,
            "backtest_admission_authorized": False,
            "provider_splicing_authorized": False,
            "pionex_native_relabel_authorized": False,
            "holdout_accessed": False,
            "automatic_model_promotion_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
    validate_catalog(payload, config=config)
    return payload


def validate_catalog(payload: Mapping[str, Any], *, config: Mapping[str, Any]) -> None:
    if (
        payload.get("schema") != "binance-usdm-detailed-history-catalog-v0.1"
        or payload.get("status") != "PASS"
        or payload.get("provider") != "binance_usdm"
        or payload.get("delivery") != "binance_vision"
    ):
        raise DetailedHistoryAuthorityError("detailed-history catalog identity mismatch")
    markets = payload.get("markets")
    if not isinstance(markets, list):
        raise DetailedHistoryAuthorityError("detailed-history catalog markets are missing")
    target = int(config["scope"]["target_market_count"])
    if len(markets) != target or payload.get("selected_market_count") != target:
        raise DetailedHistoryAuthorityError("detailed-history catalog count mismatch")
    symbols = [str(item.get("symbol")) for item in markets if isinstance(item, dict)]
    if len(symbols) != target or len(set(symbols)) != target:
        raise DetailedHistoryAuthorityError("detailed-history catalog symbols are not unique")
    if any(not symbol.endswith("USDT") or "SETTLED" in symbol for symbol in symbols):
        raise DetailedHistoryAuthorityError("detailed-history catalog contains unsafe symbols")
    authority = payload.get("authority")
    if not isinstance(authority, dict) or any(
        authority.get(name) is not False
        for name in (
            "historical_universe_membership_authorized",
            "backtest_admission_authorized",
            "provider_splicing_authorized",
            "pionex_native_relabel_authorized",
            "holdout_accessed",
            "automatic_model_promotion_authorized",
            "real_money_order_authorized",
            "live_trading_authorized",
        )
    ):
        raise DetailedHistoryAuthorityError("detailed-history catalog authority drift")


def detailed_object_key(*, symbol: str, interval: str, period: str) -> str:
    if interval not in INTERVALS:
        raise ValueError("unsupported detailed-history interval")
    year, month = parse_month(period)
    if not symbol.isascii() or not symbol.isalnum() or not symbol.endswith("USDT"):
        raise ValueError("unsafe detailed-history symbol")
    return (
        "market-data/binance_usdm/detailed-v0.1/perp/"
        f"{symbol}/{interval}/year={year:04d}/month={month:02d}/candles.parquet"
    )


def build_shard_plan(
    catalog: Mapping[str, Any], *, shard_index: int
) -> tuple[DetailedPartition, ...]:
    markets = catalog.get("markets")
    if not isinstance(markets, list):
        raise DetailedHistoryAuthorityError("catalog markets are missing")
    shard_count = int(catalog.get("shard_count") or 0)
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("shard index is outside catalog range")
    output: list[DetailedPartition] = []
    for market in markets:
        if not isinstance(market, dict) or int(market.get("shard_index", -1)) != shard_index:
            continue
        symbol = str(market["symbol"])
        asset_class = str(market["asset_class"])
        months = tuple(str(value) for value in market["common_months"])
        for interval in INTERVALS:
            for period in months:
                year, month = parse_month(period)
                source_key = (
                    f"{VISION_MONTHLY_ROOT}{symbol}/{interval}/"
                    f"{symbol}-{interval}-{period}.zip"
                )
                output.append(
                    DetailedPartition(
                        symbol=symbol,
                        asset_class=asset_class,
                        interval=interval,
                        project_interval=PROJECT_INTERVALS[interval],
                        period=period,
                        year=year,
                        month=month,
                        source_key=source_key,
                        checksum_key=f"{source_key}.CHECKSUM",
                        r2_key=detailed_object_key(
                            symbol=symbol, interval=interval, period=period
                        ),
                    )
                )
    output.sort(key=lambda item: (item.symbol, item.interval, item.period))
    if not output:
        raise DetailedHistoryAuthorityError("selected detailed-history shard is empty")
    if len({item.r2_key for item in output}) != len(output):
        raise DetailedHistoryAuthorityError("detailed-history shard contains duplicate keys")
    return tuple(output)


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise DetailedHistoryAuthorityError("authority timestamps must be timezone-aware")
    return parsed.astimezone(UTC)


def validate_authority_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("version") != "0.1.1"
        or config.get("status") != "EXECUTION_AUTHORIZED_AFTER_V0_10_WINDOW"
        or config.get("provider") != "binance_usdm"
        or config.get("delivery") != "binance_vision"
    ):
        raise DetailedHistoryAuthorityError("detailed-history config identity mismatch")
    scope = config.get("scope")
    execution = config.get("execution")
    storage = config.get("storage")
    authority = config.get("authority")
    if not all(isinstance(value, dict) for value in (scope, execution, storage, authority)):
        raise DetailedHistoryAuthorityError("detailed-history config sections are missing")
    assert isinstance(scope, dict)
    assert isinstance(execution, dict)
    assert isinstance(storage, dict)
    assert isinstance(authority, dict)
    requested = month_range(str(scope["source_month_start"]), str(scope["source_month_end"]))
    if len(requested) != 48 or int(scope.get("target_market_count", 0)) != 250:
        raise DetailedHistoryAuthorityError("detailed-history scope must remain 250 markets x 48 months")
    if tuple(scope.get("intervals") or ()) != INTERVALS:
        raise DetailedHistoryAuthorityError("detailed-history interval contract mismatch")
    holdout_start = _parse_utc(str(scope["replacement_holdout_start_utc"]))
    source_end_exclusive = _parse_utc(str(scope["source_end_exclusive_utc"]))
    if source_end_exclusive > holdout_start:
        raise DetailedHistoryAuthorityError("detailed-history source scope overlaps the holdout")
    not_before = _parse_utc(str(execution["not_before_utc"]))
    if not_before < _parse_utc("2026-09-04T02:00:00Z"):
        raise DetailedHistoryAuthorityError("detailed-history execution may not overlap V0.10")
    backfill_stop = _parse_utc(str(execution["backfill_stop_exclusive_utc"]))
    if backfill_stop != _parse_utc("2026-10-01T00:00:00Z") or not_before >= backfill_stop:
        raise DetailedHistoryAuthorityError("detailed-history backfill stop is invalid")
    if int(storage.get("free_only_hard_stop_bytes", 0)) != 8_000_000_000:
        raise DetailedHistoryAuthorityError("detailed-history R2 hard stop must remain 8 GB")
    if int(storage.get("maximum_projected_dataset_bytes", 0)) <= 0:
        raise DetailedHistoryAuthorityError("detailed-history capacity reservation is missing")
    if authority.get("public_binance_vision_reads_authorized") is not True:
        raise DetailedHistoryAuthorityError("public Binance Vision reads are not authorized")
    if authority.get("production_r2_detailed_history_writes_authorized") is not True:
        raise DetailedHistoryAuthorityError("detailed-history R2 writes are not authorized")
    for name in (
        "replacement_holdout_access_authorized",
        "historical_universe_membership_authorized",
        "backtest_admission_authorized",
        "pionex_native_relabel_authorized",
        "source_switch_authorized",
        "automatic_model_promotion_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if authority.get(name) is not False:
            raise DetailedHistoryAuthorityError(f"detailed-history authority drift: {name}")


def require_execution_window(
    config: Mapping[str, Any],
    *,
    observed_at: datetime,
    operation: str = "backfill",
) -> None:
    validate_authority_config(config)
    if observed_at.tzinfo is None:
        raise ValueError("execution clock must be timezone-aware")
    if operation not in {"backfill", "training"}:
        raise ValueError("unsupported detailed-history operation")
    observed_utc = observed_at.astimezone(UTC)
    if observed_utc < _parse_utc(str(config["execution"]["not_before_utc"])):
        raise DetailedHistoryAuthorityError(
            "detailed-history execution is blocked until the V0.10 window has ended"
        )
    if operation == "backfill" and observed_utc >= _parse_utc(
        str(config["execution"]["backfill_stop_exclusive_utc"])
    ):
        raise DetailedHistoryAuthorityError(
            "detailed-history backfill authority expired before provider or R2 access"
        )


def load_authority_pair(
    config_path: str | Path,
    receipt_path: str | Path,
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    config_bytes = Path(config_path).read_bytes()
    config = json.loads(config_bytes)
    receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    validate_authority_config(config)
    digest = sha256_bytes(config_bytes)
    supersession = receipt.get("supersession")
    execution_boundary = receipt.get("execution_boundary")
    if (
        receipt.get("schema")
        != "binance-usdm-detailed-history-execution-authority-v0.1.1"
        or receipt.get("status") != "AUTHORIZED"
        or receipt.get("stage") != "BINANCE_USDM_DETAILED_HISTORY_V0_1_1_AUTHORIZED"
        or receipt.get("config")
        != "config/binance_usdm_detailed_history_v0_1_1.json"
        or receipt.get("config_sha256") != digest
        or not _SHA256_RE.fullmatch(str(receipt.get("config_sha256") or ""))
        or not isinstance(supersession, dict)
        or supersession.get("superseded_authority_mutated") is not False
        or supersession.get("v0_1_provider_requests_performed") != 0
        or supersession.get("v0_1_r2_access_performed") is not False
        or not isinstance(execution_boundary, dict)
        or execution_boundary.get("backfill_stop_exclusive_utc")
        != config["execution"]["backfill_stop_exclusive_utc"]
    ):
        raise DetailedHistoryAuthorityError("detailed-history config/receipt binding mismatch")
    return config, receipt, config_bytes
