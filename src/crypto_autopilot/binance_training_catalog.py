from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


DEFAULT_QUOTES = ("USDT", "USDC")
STABLECOINS = {
    "DAI",
    "EURI",
    "FDUSD",
    "PYUSD",
    "TUSD",
    "USDC",
    "USDE",
    "USDP",
    "USDS",
    "USDT",
    "USD1",
    "XUSD",
}

# Binance uses a trailing B for a number of equity-like token candidates. Keep
# the label explicitly heuristic: exchangeInfo alone does not prove legal or
# economic equivalence to the underlying US stock.
TOKENIZED_STOCK_ROOTS = {
    "AAPL B".replace(" ", ""),
    "AMDB",
    "AMZNB",
    "COINB",
    "CRCLB",
    "EWYB",
    "GOOGLB",
    "HOODB",
    "IBMB",
    "INTCB",
    "LITEB",
    "METAB",
    "MSTRB",
    "MSFTB",
    "NVDAB",
    "ORCLB",
    "PLTRB",
    "QQQB",
    "QCOMB",
    "SNDKB",
    "SOXLB",
    "SPCXB",
    "SPYB",
    "TSLAB",
}

# Common crypto assets whose symbols happen to end in B. These must not be
# presented as equity-like candidates merely because of a suffix heuristic.
NON_STOCK_SUFFIX_B_ASSETS = {
    "BCH",
    "BNB",
    "BSV",
    "CKB",
    "DGB",
    "FTM",
    "KSM",
    "LQTY",
    "NEAR",
    "QUBIC",
    "SHIB",
    "TRB",
    "WLD",
    "XMR",
}


@dataclass(frozen=True, slots=True)
class TrainingMarket:
    symbol: str
    base_asset: str
    quote_asset: str
    status: str
    market_type: str
    asset_class: str
    classification_method: str
    classification_confidence: str
    is_spot_trading_allowed: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_asset(base_asset: str) -> tuple[str, str, str]:
    asset = base_asset.upper()
    if asset in STABLECOINS:
        return "stablecoin", "known_stablecoin_set", "high"
    if asset in TOKENIZED_STOCK_ROOTS or (
        asset.endswith("B") and asset not in NON_STOCK_SUFFIX_B_ASSETS and len(asset) >= 4
    ):
        return "tokenized_stock_candidate", "trailing_B_heuristic", "heuristic"
    if asset in {"PAXG", "XAUT", "DCR", "LUNA", "USTC"}:
        return "other", "known_nonstandard_asset_set", "medium"
    return "crypto", "default_spot_asset_class", "medium"


def parse_exchange_info(
    payload: dict[str, Any],
    *,
    quotes: tuple[str, ...] | list[str] = DEFAULT_QUOTES,
    all_quotes: bool = False,
) -> list[TrainingMarket]:
    if not isinstance(payload, dict) or not isinstance(payload.get("symbols"), list):
        raise ValueError("Binance exchangeInfo must contain a symbols list")
    allowed_quotes = {str(item).upper() for item in quotes}
    markets: list[TrainingMarket] = []
    for raw in payload["symbols"]:
        if not isinstance(raw, dict):
            continue
        symbol = str(raw.get("symbol", "")).upper()
        base = str(raw.get("baseAsset", "")).upper()
        quote = str(raw.get("quoteAsset", "")).upper()
        if not symbol or not base or not quote or not symbol.isascii() or not symbol.isalnum():
            continue
        if raw.get("status") != "TRADING":
            continue
        if raw.get("isSpotTradingAllowed") is not True:
            continue
        if not all_quotes and quote not in allowed_quotes:
            continue
        asset_class, method, confidence = classify_asset(base)
        markets.append(
            TrainingMarket(
                symbol=symbol,
                base_asset=base,
                quote_asset=quote,
                status="TRADING",
                market_type="spot",
                asset_class=asset_class,
                classification_method=method,
                classification_confidence=confidence,
                is_spot_trading_allowed=True,
            )
        )
    return sorted(markets, key=lambda item: (item.quote_asset, item.asset_class, item.symbol))


def catalog_payload(
    markets: list[TrainingMarket], *, retrieved_at_utc: str, quotes: list[str], all_quotes: bool
) -> dict[str, Any]:
    return {
        "schema": "binance-internal-training-market-catalog-v0.2",
        "status": "LOCAL_INTERNAL_TRAINING_AUTHORIZED",
        "provider": "binance_spot",
        "market_type": "spot",
        "source_endpoint": "https://data-api.binance.vision/api/v3/exchangeInfo",
        "retrieved_at_utc": retrieved_at_utc,
        "quote_filter": {"all_quotes": all_quotes, "quotes": quotes},
        "classification_note": "Tokenized stock labels are heuristic candidates only; exchangeInfo does not establish equity equivalence.",
        "markets": [market.as_dict() for market in markets],
        "authority": {
            "local_public_market_reads_authorized": True,
            "local_artifact_write_authorized": True,
            "website_projection_authorized": False,
            "production_r2_access_authorized": False,
            "provider_splicing_authorized": False,
            "pionex_native_relabel_authorized": False,
            "source_switch_authorized": False,
            "holdout_access_authorized": False,
            "trade_kline_w1_materialization_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
