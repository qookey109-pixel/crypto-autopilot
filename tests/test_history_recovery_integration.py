"""Exercise the real CLI main with synthetic provider and R2 boundaries."""
import argparse
import ast
import io
import json
import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from crypto_autopilot.history_recovery import (
    Journal, RecoveryError, MAX_ATTEMPTS, choose_shard, load_contract,
    quality_diagnostic, require_window,
)
from test_history_recovery import Store, DIAG

ROOT = Path(__file__).resolve().parents[1]


class ArchiveError(ValueError):
    pass


class IntegrationTests(unittest.TestCase):
    def globals(self, store, state, materialize):
        tree = ast.parse((ROOT / "scripts/run_binance_detailed_history.py").read_text())
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        config_path = ROOT / "config/binance_usdm_detailed_history_v0_1_2.json"
        base_bytes = config_path.read_bytes()
        config = json.loads(base_bytes)
        env = dict(argparse=argparse, Path=Path, os=os, re=re, datetime=datetime, UTC=timezone.utc,
                   json=json, DEFAULT_CONFIG=config_path, DEFAULT_AUTHORITY=Path("unused"),
                   SAFE_RUN_ID=re.compile(r"^[A-Za-z0-9._-]{1,96}$"),
                   require_ephemeral_output=lambda p: p,
                   load_authority_pair=lambda *a: (config, {}, base_bytes),
                   require_execution_window=Mock(), DetailedHistoryAuthorityError=ValueError,
                   create_store=Mock(return_value=store),
                   load_published_catalog=lambda *a: (
                       {"catalog_key": "synthetic-catalog", "catalog_sha256": "b"*64}, {}),
                   load_state=lambda *a, **k: state,
                   _ensure_reservation_headroom=Mock(),
                   materialize_shard=materialize,
                   build_shard_plan=lambda *a, **k: [SimpleNamespace(symbol="BNXUSDT", interval="15m", period="2022-08")],
                   canonical_json_bytes=lambda d: (json.dumps(d) + "\n").encode(),
                   BinanceVisionEvidenceError=ArchiveError,
                   Journal=Journal, RecoveryError=RecoveryError, MAX_ATTEMPTS=MAX_ATTEMPTS,
                   choose_shard=choose_shard, load_contract=load_contract,
                   quality_diagnostic=quality_diagnostic, require_window=require_window)
        # Fixed real execution clock, avoiding time-dependent tests.
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 9, 8, tzinfo=timezone.utc)
        env["datetime"] = Clock
        exec(compile(ast.Module(body=[main], type_ignores=[]), "<real-cli-main>", "exec"), env)
        return env

    def invoke(self, env, output, run="r0", ref="refs/heads/main"):
        args = ["runner", "--run-id", run, "--output", str(output),
                "--recovery-config", str(ROOT / "config/binance_usdm_history_recovery_v0_1.json"),
                "--recovery-authority", str(ROOT / "research/receipts/2026-09-08-binance-usdm-history-recovery-v0-1-authority.json")]
        with patch("sys.argv", args), patch.dict(os.environ, {
            "GITHUB_REF": ref, "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
        }), redirect_stdout(io.StringIO()):
            return env["main"]()

    def test_real_cli_quality_failure_then_next_shard(self):
        store = Store()
        state = {"status": "IN_PROGRESS", "shard_count": 10, "completed_shards": []}
        attempted = []
        def fail(*a, **k):
            attempted.append(k["shard_index"])
            raise ArchiveError("Binance Vision kline audit failed: " + json.dumps(DIAG))
        env = self.globals(store, state, fail)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            self.assertEqual(self.invoke(env, path), 1)
            report = json.loads(path.read_text())
            self.assertEqual(report["status"], "FAIL")
            self.assertFalse(report["dataset_complete"])
            self.assertEqual(state["completed_shards"], [])
            self.assertEqual(self.invoke(env, path, run="r1"), 1)
        self.assertEqual(attempted, [0, 1])

    def test_checksum_error_never_writes_attempt(self):
        store = Store()
        env = self.globals(store, {"status": "IN_PROGRESS", "shard_count": 10, "completed_shards": []},
                           Mock(side_effect=ArchiveError("SHA-256 mismatch")))
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(RecoveryError):
            self.invoke(env, Path(tmp) / "report.json")
        self.assertEqual(store.writes, 0)

    def test_non_main_blocks_before_store(self):
        env = self.globals(Store(), {}, Mock())
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(RecoveryError):
            self.invoke(env, Path(tmp) / "report.json", ref="refs/heads/unreviewed")
        env["create_store"].assert_not_called()

    def test_contract_tamper_and_expiry(self):
        base = (ROOT / "config/binance_usdm_detailed_history_v0_1_2.json").read_bytes()
        config = ROOT / "config/binance_usdm_history_recovery_v0_1.json"
        receipt = ROOT / "research/receipts/2026-09-08-binance-usdm-history-recovery-v0-1-authority.json"
        now = datetime(2026, 9, 8, tzinfo=timezone.utc)
        self.assertEqual(len(load_contract(config, receipt, base, now)), 64)
        with self.assertRaises(RecoveryError):
            load_contract(config, receipt, base + b" ", now)
        with self.assertRaises(RecoveryError):
            load_contract(config, receipt, base, datetime(2026, 10, 1, tzinfo=timezone.utc))
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "receipt.json"
            data = json.loads(receipt.read_text())
            data["data_repair_authorized"] = True
            bad.write_text(json.dumps(data))
            with self.assertRaises(RecoveryError):
                load_contract(config, bad, base, now)
