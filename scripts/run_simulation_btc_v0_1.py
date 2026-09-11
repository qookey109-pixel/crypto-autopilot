"""Execute the admitted fixed BTC sample after reviewed main merge, in GitHub only."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
import zipfile

from crypto_autopilot.paper.simulation_funding_v0_1 import (
    SIMULATION_BACKTEST_CONFIG,
    load_verified_funding,
    run_readiness_with_verified_funding,
)
from crypto_autopilot.paper.simulation_readiness_v0_3 import _validate_receipt

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/simulation_btc_execution_v0_1.json"
AUTHORITY = ROOT / "research/receipts/2026-09-11-simulation-btc-execution-v0-1-authority.json"
REPOSITORY = "qookey109-pixel/crypto-autopilot"
CONFIG_SHA256 = "c0eeace59bfb350985a8f72f00233c7ffa767bebe3b14076ab858337979a1dc2"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require_context(config, env, event, now):
    expected = {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": REPOSITORY,
                "GITHUB_REF": "refs/heads/main", "GITHUB_RUN_ATTEMPT": "1",
                "GITHUB_EVENT_NAME": "workflow_run"}
    if any(env.get(key) != value for key, value in expected.items()):
        raise ValueError("cloud main context required")
    if not 1 <= int(env.get("GITHUB_RUN_NUMBER", "0")) <= config["maximum_workflow_runs"]:
        raise ValueError("execution count budget exhausted")
    if not re.fullmatch(r"[0-9]+", env.get("GITHUB_RUN_ID", "")):
        raise ValueError("run identity missing")
    upstream = event.get("workflow_run", {})
    if (upstream.get("name") != "CI" or upstream.get("event") != "push"
            or upstream.get("status") != "completed" or upstream.get("conclusion") != "success"
            or upstream.get("head_branch") != "main"
            or upstream.get("head_repository", {}).get("full_name") != REPOSITORY
            or upstream.get("head_sha") != env.get("GITHUB_SHA")
            or not re.fullmatch(r"[0-9a-f]{40}", env.get("GITHUB_SHA", ""))):
        raise ValueError("successful CI for current main SHA required")
    start = datetime.fromisoformat(config["not_before_utc"].replace("Z", "+00:00"))
    stop = datetime.fromisoformat(config["stop_exclusive_utc"].replace("Z", "+00:00"))
    if not start <= now < stop:
        raise ValueError("execution window closed")


def load_authority():
    payload = CONFIG.read_bytes()
    config = json.loads(payload)
    authority = json.loads(AUTHORITY.read_bytes())
    if (authority["config_sha256"] != digest(payload) or digest(payload) != CONFIG_SHA256
            or authority["status"] != "AUTHORIZED_AFTER_REVIEWED_MAIN_MERGE"
            or config["status"] != authority["status"]):
        raise ValueError("execution authority mismatch")
    report_bytes = (ROOT / config["kline_report"]).read_bytes()
    if digest(report_bytes) != config["kline_report_sha256"]:
        raise ValueError("frozen K-line report changed")
    report = json.loads(report_bytes)
    if report["schema"] != "pionex-bounded-pilot-run-report-v0.2":
        raise ValueError("wrong run report schema")
    # The runner report wraps the exact capacity receipt. Build an in-memory
    # adapter input; never modify the original historical run report.
    receipt = {**report, "schema": "pionex-capacity-pilot-v0.2"}
    _validate_receipt(receipt)
    if len(receipt["intervals"]) != config["maximum_r2_gets_per_run"]:
        raise ValueError("object budget mismatch")
    if sum(row["bytes"] for row in receipt["intervals"]) != config["maximum_r2_bytes_per_run"]:
        raise ValueError("byte budget mismatch")
    return config, receipt


class ArtifactRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme != "https":
            raise ValueError("non-HTTPS artifact redirect")
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            redirected.remove_header("Authorization")
        return redirected


def funding_from_zip(payload, config):
    if digest(payload) != config["funding_zip_sha256"]:
        raise ValueError("funding artifact digest mismatch")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        if archive.namelist() != [config["funding_report_path"]]:
            raise ValueError("unexpected artifact members")
        member = archive.getinfo(config["funding_report_path"])
        if member.file_size > 100_000:
            raise ValueError("oversized funding report")
        report = json.loads(archive.read(member))
    if report.get("run_id") != config["funding_run_id"]:
        raise ValueError("funding run lineage changed")
    load_verified_funding(report)
    return report


def controls_summary(backtest_result):
    """Report configured controls separately from whether a run observed a trigger."""

    observed = backtest_result is not None
    trades = () if backtest_result is None else backtest_result.trades
    rejected = () if backtest_result is None else backtest_result.rejected_plans
    kill_switch_triggered = None if not observed else (
        any(trade.exit_reason == "kill_switch" for trade in trades)
        or any(reason == "kill_switch_active" for _, reason in rejected)
    )
    max_holding_triggered = None if not observed else any(
        trade.exit_reason == "max_holding_time" for trade in trades
    )
    return {
        "kill_switch": {
            "configured": SIMULATION_BACKTEST_CONFIG.kill_switch_time_ms is not None,
            "time_ms": SIMULATION_BACKTEST_CONFIG.kill_switch_time_ms,
            "triggered": kill_switch_triggered,
        },
        "max_holding": {
            "configured": SIMULATION_BACKTEST_CONFIG.max_holding_minutes is not None,
            "minutes": SIMULATION_BACKTEST_CONFIG.max_holding_minutes,
            "triggered": max_holding_triggered,
        },
    }


def financial_summary(backtest_result):
    """Return measured PnL/cost metrics, or explicit nulls when no result exists."""

    if backtest_result is None:
        return {
            "available": False,
            "gross_pnl_usd": None,
            "net_pnl_usd": None,
            "final_equity_usd": None,
            "return_pct": None,
            "max_drawdown_pct": None,
            "total_fees_usd": None,
            "total_funding_usd": None,
            "total_slippage_cost_usd": None,
        }
    metrics = backtest_result.metrics
    return {
        "available": True,
        "gross_pnl_usd": round(sum(trade.gross_pnl_usd for trade in backtest_result.trades), 8),
        "net_pnl_usd": metrics.net_pnl_usd,
        "final_equity_usd": backtest_result.final_equity_usd,
        "return_pct": metrics.return_pct,
        "max_drawdown_pct": metrics.max_drawdown_pct,
        "total_fees_usd": metrics.total_fees_usd,
        "total_funding_usd": metrics.total_funding_usd,
        "total_slippage_cost_usd": metrics.total_slippage_cost_usd,
    }


def outcome_summary(state, *, bridge=None, reason=None):
    """Keep no-signal, no-trade and execution-failure states schema-compatible."""

    if bridge is None:
        generated = executed = rejected = None
        result_available = False
    else:
        generated = bridge.get("generated_plan_count")
        executed = bridge.get("executed_trade_count")
        rejected = bridge.get("rejected_plan_count", 0 if generated == 0 else None)
        result_available = "result" in bridge
    return {
        "state": state,
        "simulation_result_available": result_available,
        "reason": reason,
        "generated_plan_count": generated,
        "executed_trade_count": executed,
        "rejected_plan_count": rejected,
    }


def simulate(config, receipt, funding, read_object):
    payloads = {}
    for row in receipt["intervals"]:
        payload = read_object(row["key"], row["bytes"])
        if len(payload) != row["bytes"] or digest(payload) != row["sha256"]:
            raise ValueError("sample byte/hash mismatch")
        payloads[row["interval"]] = payload
    result = run_readiness_with_verified_funding(payloads, receipt, funding)
    result["blockers"] = [value for value in result["blockers"]
                          if value != "production_simulation_data_admission_not_authorized"]
    if not result["pipeline_exercised"] and "no_executed_trade" not in result["blockers"]:
        result["blockers"].append("no_executed_trade")
    result["status"] = "READY" if result["pipeline_exercised"] and not result["blockers"] else "NOT_READY"
    result["scope"] = config["scope"]
    result["full_universe_ready"] = False
    result["production_sample_admitted"] = True

    backtest_result = result.get("result")
    if result["pipeline_exercised"]:
        outcome_state = "TRADES_EXECUTED"
        outcome_reason = None
    elif result.get("generated_plan_count") == 0:
        outcome_state = "NO_SIGNAL"
        outcome_reason = "no_candle_derived_strategy_signal"
    else:
        outcome_state = "NO_TRADE"
        outcome_reason = "no_executed_trade"
    result["outcome"] = outcome_summary(outcome_state, bridge=result, reason=outcome_reason)
    result["controls"] = controls_summary(backtest_result)
    result["financial_summary"] = financial_summary(backtest_result)
    if backtest_result is not None:
        result["result"] = asdict(backtest_result)
    return result


def base_report():
    return {
        "schema": "simulation-btc-run-v0.1",
        "status": "NOT_READY",
        "scope": "BTC_FIXED_27_DAY_ENGINE_VALIDATION_ONLY",
        "full_universe_ready": False,
        "r2_writes": False,
        "holdout_accessed": False,
        "live_trading_authorized": False,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "r2_get_attempts": 0,
        "stage": "AUTHORITY_AND_CONTEXT",
        "blockers": [],
        "outcome": outcome_summary("NOT_RUN"),
        "controls": controls_summary(None),
        "financial_summary": financial_summary(None),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from crypto_autopilot.storage.ephemeral import require_ephemeral_output
    output = require_ephemeral_output(args.output)
    report = base_report()
    try:
        config, receipt = load_authority()
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        def guard():
            require_context(config, os.environ, event, datetime.now(timezone.utc))
        guard()
        report["stage"] = "FUNDING_ARTIFACT_VERIFICATION"
        url = (f"https://api.github.com/repos/{REPOSITORY}/actions/artifacts/"
               f"{config['funding_artifact_id']}/zip")
        request = Request(url, headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"})
        with build_opener(ArtifactRedirect()).open(request, timeout=15) as response:
            funding = funding_from_zip(response.read(100_001), config)
        guard()
        report["stage"] = "EXACT_SAMPLE_READ_AND_SIMULATION"
        import boto3
        from botocore.config import Config
        account = os.environ["CLOUDFLARE_ACCOUNT_ID"]
        if re.fullmatch(r"[0-9a-f]{32}", account) is None:
            raise ValueError("invalid account format")
        client = boto3.client(
            "s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto",
            config=Config(connect_timeout=10, read_timeout=15, retries={"total_max_attempts": 1}),
        )
        allowed = {row["key"]: row["bytes"] for row in receipt["intervals"]}
        def read_object(key, size):
            guard()
            if key not in allowed or size != allowed[key] or report["r2_get_attempts"] >= 3:
                raise ValueError("object access outside exact sample")
            report["r2_get_attempts"] += 1
            response = client.get_object(Bucket=os.environ["R2_BUCKET_NAME"], Key=key)
            body = response["Body"]
            try:
                if response["ContentLength"] != size:
                    raise ValueError("R2 byte count mismatch")
                return body.read(size + 1)
            finally:
                body.close()
        report.update(simulate(config, receipt, funding, read_object))
        report["stage"] = "COMPLETE"
    except Exception as exc:
        failure = "execution_failed_" + type(exc).__name__
        report["blockers"] = [failure]
        report["outcome"] = outcome_summary("EXECUTION_FAILED", reason=failure)
        report["controls"] = controls_summary(None)
        report["financial_summary"] = financial_summary(None)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "scope", "r2_get_attempts")}))
    return 0 if report["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
