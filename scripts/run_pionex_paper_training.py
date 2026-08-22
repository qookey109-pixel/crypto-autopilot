#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.market_features import (
    build_derivative_features,
    build_microstructure_features,
)
from crypto_autopilot.paper_training import REQUIRED_INTERVALS, run_paper_training_replay


def _closed_end_ms(now_ms: int, interval: str, maximum_end_ms: int) -> int:
    step = INTERVAL_MS[interval]
    return min((now_ms // step) * step - 1, maximum_end_ms)


def _skip_payload(run_id: str, observed_at: str, reason: str) -> dict[str, object]:
    return {
        "schema": "pionex-public-paper-training-run-v0.1",
        "status": "SKIPPED",
        "mode": "PAPER_TRAINING_ONLY",
        "runId": run_id,
        "observedAtUtc": observed_at,
        "reason": reason,
        "authority": {
            "providerRequestsPerformed": 0,
            "holdoutAccessed": False,
            "pionexDemoAutomationAuthorized": False,
            "privateApiUsed": False,
            "realMoneyOrderAuthorized": False,
            "liveTradingAuthorized": False,
        },
        "metrics": {
            "trade_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate": 0.0,
            "net_pnl_usd": 0.0,
            "return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "profit_factor": None,
            "trade_sharpe": None,
            "total_fees_usd": 0.0,
            "total_funding_usd": 0.0,
            "total_slippage_cost_usd": 0.0,
        },
        "latestCandidates": [],
        "paperTrades": [],
        "trainingRecords": [],
        "manualPionexDemoSamples": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run bounded Pionex-public candidate generation and Paper Broker replay."
    )
    parser.add_argument("--config", type=Path, default=Path("config/paper_training_v0_1.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--run-id", default="local")
    parser.add_argument("--now-ms", type=int)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    now_ms = args.now_ms if args.now_ms is not None else int(now.timestamp() * 1000)
    observed_at = datetime.fromtimestamp(now_ms / 1000.0, timezone.utc).isoformat()
    holdout_start_ms = int(config["holdout_guard"]["blocked_from_ms"])
    maximum_end_ms = min(now_ms, holdout_start_ms - 1)

    if now_ms >= holdout_start_ms:
        payload = _skip_payload(
            args.run_id,
            observed_at,
            "FROZEN_HOLDOUT_BOUNDARY_REACHED_NO_PROVIDER_ACCESS",
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(payload, sort_keys=True))
        return 0

    previous_state: dict[str, object] = {}
    if args.state and args.state.exists():
        previous_state = json.loads(args.state.read_text(encoding="utf-8"))
    previous_oi = {
        str(key): float(value)
        for key, value in dict(previous_state.get("openInterest", {})).items()
    }

    client = PionexPublicClient(
        timeout_seconds=float(config["provider"]["timeout_seconds"]),
        requests_per_second=float(config["provider"]["requests_per_second"]),
    )
    indexes = {item.symbol: item for item in client.list_derivative_indexes()}
    open_interests = client.list_open_interests()
    candles_by_symbol_interval = {}
    funding_by_symbol = {}
    live_microstructure = {}
    live_derivatives = {}
    errors = []

    for symbol in config["symbols"]:
        try:
            candles_by_symbol_interval[symbol] = {
                interval: client.get_klines(
                    symbol,
                    interval,
                    limit=int(config["provider"]["kline_limit"]),
                    end_time_ms=_closed_end_ms(now_ms, interval, maximum_end_ms),
                )
                for interval in REQUIRED_INTERVALS
            }
            funding = client.get_funding_rates(
                symbol,
                limit=int(config["provider"]["funding_limit"]),
                end_time_ms=maximum_end_ms,
            )
            funding_by_symbol[symbol] = funding
            trades = client.get_recent_trades(
                symbol, limit=int(config["provider"]["recent_trade_limit"])
            )
            book = client.get_order_book(
                symbol, limit=int(config["provider"]["depth_limit"])
            )
            live_microstructure[symbol] = build_microstructure_features(
                trades,
                book,
                depth_levels=int(config["features"]["order_book_depth_levels"]),
                reference_notional_usd=float(config["features"]["slippage_reference_usd"]),
            )
            mark = client.get_price_klines(
                symbol,
                "15M",
                price_type="mark",
                limit=int(config["provider"]["basis_history_limit"]),
            )
            index = client.get_price_klines(
                symbol,
                "15M",
                price_type="index",
                limit=int(config["provider"]["basis_history_limit"]),
            )
            index_by_time = {item.time_ms: item for item in index}
            basis_history = [
                item.close / index_by_time[item.time_ms].close - 1.0
                for item in mark
                if item.time_ms in index_by_time and index_by_time[item.time_ms].close > 0
            ]
            live_derivatives[symbol] = build_derivative_features(
                current=indexes.get(symbol),
                funding_history=funding,
                basis_history=basis_history,
                open_interest=open_interests.get(symbol),
                previous_open_interest=previous_oi.get(symbol),
            )
        except Exception as exc:  # fail one symbol closed without provider substitution
            errors.append({"symbol": symbol, "errorType": type(exc).__name__, "message": str(exc)})
            candles_by_symbol_interval.pop(symbol, None)
            funding_by_symbol.pop(symbol, None)
            live_microstructure.pop(symbol, None)
            live_derivatives.pop(symbol, None)

    if len(candles_by_symbol_interval) < int(config["provider"]["minimum_symbols"]):
        raise RuntimeError(
            f"only {len(candles_by_symbol_interval)} symbols succeeded; "
            f"requires {config['provider']['minimum_symbols']}; errors={errors}"
        )

    payload = run_paper_training_replay(
        run_id=args.run_id,
        observed_at_utc=observed_at,
        candles_by_symbol_interval=candles_by_symbol_interval,
        funding_by_symbol=funding_by_symbol,
        live_microstructure=live_microstructure,
        live_derivatives=live_derivatives,
        config=config,
    )
    payload["providerErrors"] = errors
    payload["requestedSymbolCount"] = len(config["symbols"])
    payload["successfulSymbolCount"] = len(candles_by_symbol_interval)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.state:
        history = list(previous_state.get("runHistory", []))
        history.append(
            {
                "runId": args.run_id,
                "observedAtUtc": observed_at,
                "inputFingerprint": payload["inputFingerprint"],
                "metrics": payload["metrics"],
            }
        )
        state_payload = {
            "schema": "paper-training-forward-state-v0.1",
            "openInterest": open_interests,
            "runHistory": history[-100:],
            "containsSecrets": False,
            "holdoutAccessed": False,
        }
        args.state.parent.mkdir(parents=True, exist_ok=True)
        args.state.write_text(
            json.dumps(state_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        payload["runHistory"] = state_payload["runHistory"]
        args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"status={payload['status']} symbols={payload['symbolCount']} "
        f"eligibleCandidates={payload['eligibleCandidateCount']} "
        f"trades={payload['metrics']['trade_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
