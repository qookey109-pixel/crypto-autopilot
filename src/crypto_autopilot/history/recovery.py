"""Bounded history attempt journal; never grants dataset completion."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

BASE_SHA = "fc4e42b855229ecb62e12e681778080c2aa749112036a6e8b3af9e9da98b716a"
PREFIX = "training/binance_usdm/history-recovery-v0.1"
MAX_ATTEMPTS = 128


class RecoveryError(ValueError):
    pass


def payload(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def require_window(now):
    if not datetime(2026, 9, 4, 2, tzinfo=timezone.utc) <= now < datetime(2026, 10, 1, tzinfo=timezone.utc):
        raise RecoveryError("recovery execution window closed")


def load_contract(config_path, receipt_path, base_bytes, now):
    require_window(now)
    raw = Path(config_path).read_bytes()
    config = json.loads(raw)
    receipt = json.loads(Path(receipt_path).read_bytes())
    expected = {
        "version": "0.1",
        "status": "AUTHORIZED_ON_MAIN_MERGE",
        "base_config_sha256": BASE_SHA,
        "namespace": PREFIX,
        "max_attempts": MAX_ATTEMPTS,
        "shard_count": 10,
        "algorithm": "unattempted_then_oldest_sequence",
        "expires_at_utc": "2026-10-01T00:00:00Z",
        "quality_failure_exit_code": 1,
        "dataset_completion_changed": False,
        "source_switch_authorized": False,
        "holdout_access_authorized": False,
        "trading_authorized": False,
    }
    if config != expected or digest(base_bytes) != BASE_SHA:
        raise RecoveryError("recovery config or base binding mismatch")
    if receipt != {
        "schema": "history-recovery-authority-v0.1",
        "status": "AUTHORIZED_ON_MAIN_MERGE",
        "config": "config/binance_usdm_history_recovery_v0_1.json",
        "config_sha256": digest(raw),
        "base_config_sha256": BASE_SHA,
        "execution_gate": "protected-main merge before execution",
        "attempt_metadata_r2_read_write_authorized": True,
        "shard_rotation_authorized": True,
        "data_repair_authorized": False,
        "scope_change_authorized": False,
    }:
        raise RecoveryError("recovery receipt binding mismatch")
    return digest(raw)


def quality_diagnostic(message):
    prefix = "Binance Vision kline audit failed: "
    if not message.startswith(prefix) or len(message) > 2048:
        raise RecoveryError("unclassified archive error")
    try:
        value = json.loads(message[len(prefix):])
    except (ValueError, TypeError) as exc:
        raise RecoveryError("invalid diagnostic") from exc
    counts = ("row_count", "gap_count", "missing_bars", "misaligned_count", "invalid_candle_count")
    fields = set(counts) | {"provider", "dataset", "frequency", "symbol", "interval", "period", "archive_sha256"}
    if not isinstance(value, dict) or set(value) != fields:
        raise RecoveryError("diagnostic fields mismatch")
    if any(type(value[k]) is not int or not 0 <= value[k] <= 10000000 for k in counts):
        raise RecoveryError("invalid diagnostic counts")
    if (value["provider"], value["dataset"], value["frequency"]) != ("binance_usdm", "klines", "monthly"):
        raise RecoveryError("diagnostic provider mismatch")
    if value["interval"] not in ("15m", "1h", "4h"):
        raise RecoveryError("diagnostic interval mismatch")
    for field, pattern in (("symbol", r"[A-Z0-9_]{1,40}USDT"), ("period", r"20[0-9]{2}-(0[1-9]|1[0-2])"), ("archive_sha256", r"[0-9a-f]{64}")):
        if not isinstance(value[field], str) or not re.fullmatch(pattern, value[field]):
            raise RecoveryError("invalid diagnostic identity")
    if not "2022-08" <= value["period"] <= "2026-07":
        raise RecoveryError("diagnostic escaped history window")
    if not any(value[k] for k in ("gap_count", "misaligned_count", "invalid_candle_count")):
        raise RecoveryError("diagnostic does not report failure")
    return value


def choose_shard(shard_count, completed, attempts):
    if type(shard_count) is not int or not 1 <= shard_count <= 10:
        raise RecoveryError("invalid shard count")
    if any(type(i) is not int or not 0 <= i < shard_count for i in completed) or len(set(completed)) != len(completed):
        raise RecoveryError("invalid completed shards")
    last = {}
    runs = set()
    for seq, item in enumerate(attempts):
        i = item["shard_index"]
        if (type(i) is not int or not 0 <= i < shard_count or
                item["sequence"] != seq or item["run_id"] in runs or
                item["outcome"] not in ("PASS", "QUALITY_REJECT")):
            raise RecoveryError("invalid attempt history")
        if item["outcome"] == "PASS" and i not in completed:
            raise RecoveryError("attempt PASS without completed shard evidence")
        runs.add(item["run_id"])
        last[i] = seq
    remaining = [i for i in range(shard_count) if i not in completed]
    return min(remaining, key=lambda i: (last.get(i, -1), i)) if remaining else None


class Journal:
    """Serialized receipt chain. Uncommitted next record blocks all new work."""
    def __init__(self, store, catalog_sha, contract_sha, gate):
        if any(not re.fullmatch(r"[0-9a-f]{64}", s) for s in (catalog_sha, contract_sha)):
            raise RecoveryError("invalid journal binding")
        self.store, self.gate = store, gate
        self.binding = {"catalog_sha256": catalog_sha, "contract_sha256": contract_sha, "base_config_sha256": BASE_SHA}
        self.root = f"{PREFIX}/catalog={catalog_sha}/contract={contract_sha}"
        self.pointer_key = f"{self.root}/latest.json"
        self.records = []
        self.head = None
        self.original_pointer = None

    def key(self, seq):
        return f"{self.root}/attempt={seq:03d}.json"

    def load(self):
        self.gate()
        self.records = []
        self.head = None
        raw = self.store.get_bytes_if_exists(self.pointer_key)
        self.original_pointer = raw
        count, expected = 0, None
        if raw is not None:
            pointer = json.loads(raw)
            if set(pointer) != {"count", "sha256", "binding"} or pointer["binding"] != self.binding:
                raise RecoveryError("journal pointer mismatch")
            count, expected = pointer["count"], pointer["sha256"]
            if type(count) is not int or not 1 <= count <= MAX_ATTEMPTS:
                raise RecoveryError("journal count invalid")
        previous = None
        for seq in range(count):
            raw_record = self.store.get_bytes_if_exists(self.key(seq))
            if raw_record is None:
                raise RecoveryError("journal record missing")
            item = json.loads(raw_record)
            fields = {"binding", "sequence", "previous_sha256", "run_id", "shard_index", "outcome", "diagnostic"}
            if set(item) != fields or item["binding"] != self.binding or item["sequence"] != seq or item["previous_sha256"] != previous:
                raise RecoveryError("journal chain mismatch")
            if not isinstance(item["run_id"], str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,96}", item["run_id"]):
                raise RecoveryError("journal run identity invalid")
            if item["outcome"] == "QUALITY_REJECT":
                quality_diagnostic("Binance Vision kline audit failed: " + json.dumps(item["diagnostic"]))
            elif item["outcome"] != "PASS" or item["diagnostic"] is not None:
                raise RecoveryError("journal outcome invalid")
            previous = digest(raw_record)
            self.records.append(item)
        if previous != expected:
            raise RecoveryError("journal head SHA mismatch")
        if self.store.get_bytes_if_exists(self.key(count)) is not None:
            raise RecoveryError("uncommitted journal record requires review")
        self.head = previous
        return self.records

    def append(self, run_id, shard_index, outcome, diagnostic=None):
        count = len(self.records)
        if count >= MAX_ATTEMPTS:
            raise RecoveryError("attempt budget exhausted")
        if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,96}", run_id):
            raise RecoveryError("invalid run id")
        if any(r["run_id"] == run_id for r in self.records):
            raise RecoveryError("duplicate run requires review")
        if type(shard_index) is not int or not 0 <= shard_index < 10:
            raise RecoveryError("invalid shard index")
        if outcome == "QUALITY_REJECT":
            quality_diagnostic("Binance Vision kline audit failed: " + json.dumps(diagnostic))
        elif outcome != "PASS" or diagnostic is not None:
            raise RecoveryError("invalid attempt result")
        record = dict(binding=self.binding, sequence=count, previous_sha256=self.head,
                      run_id=run_id, shard_index=shard_index, outcome=outcome, diagnostic=diagnostic)
        data = payload(record)
        self.gate()
        if self.store.get_bytes_if_exists(self.pointer_key) != self.original_pointer:
            raise RecoveryError("journal pointer changed")
        if self.store.get_bytes_if_exists(self.key(count)) is not None:
            raise RecoveryError("immutable attempt already exists")
        self.store.put_bytes(self.key(count), data, content_type="application/json", metadata={"role": "history-attempt"})
        if self.store.get_bytes_verified(self.key(count), expected_sha256=digest(data)) != data:
            raise RecoveryError("attempt readback mismatch")
        pointer_data = payload({"count": count + 1, "sha256": digest(data), "binding": self.binding})
        self.gate()
        if self.store.get_bytes_if_exists(self.pointer_key) != self.original_pointer:
            raise RecoveryError("journal pointer changed before commit")
        self.store.put_bytes(self.pointer_key, pointer_data, content_type="application/json", metadata={"role": "history-attempt-pointer"})
        if self.store.get_bytes_verified(self.pointer_key, expected_sha256=digest(pointer_data)) != pointer_data:
            raise RecoveryError("pointer readback mismatch")
        self.records.append(record)
        self.original_pointer, self.head = pointer_data, digest(data)

