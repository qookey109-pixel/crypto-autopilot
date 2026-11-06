"""Prepared read-only Core100 comparison under V0.5 shared admission.

No production workflow or identity authority is created by this module.
"""
from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import D1UsageGuard, D1UsageSnapshot
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, CloudBudgetGuard, R2UsageSnapshot
from crypto_autopilot.paper.cloud_loop_v0_1 import SLOT_MS, SLOT_OFFSET_MS
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.prepaid_d1_client_v0_1 import DatabaseSizeEvidence
from crypto_autopilot.paper.prepaid_query_controller_v0_1 import PrepaidQueryMeter
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import SharedWriterReservation
from crypto_autopilot.paper.shared_writer_r2_budget_v0_2 import SharedWriterR2BudgetV05
from crypto_autopilot.training.prepaid_core100_d1_v0_1 import Core100PrepaidD1Client, WRITER
from scripts import train_binance_detailed_history_models_v0_4 as frozen

_MAX_OBJECT_BYTES = 8 * 1024 * 1024
_MAX_TOTAL_BYTES = 64 * 1024 * 1024
_ALLOWED_EXACT = frozenset({
    "catalogs/binance_usdm/crypto-core-v0.1/latest.json",
    "training/binance_usdm/crypto-core-v0.1/backfill-state.json",
    "training/binance_usdm/crypto-core-v0.1/fingerprint-v0.2/latest.json",
})
_ALLOWED_PREFIXES = (
    "catalogs/binance_usdm/crypto-core-v0.1/runs/",
    "receipts/historical/binance_usdm/crypto-core-v0.1/",
    "training/binance_usdm/crypto-core-v0.1/fingerprint-v0.2/runs/",
)


class _Core100ReadOnlyStore:
    """No object writes, model reads, historical partition reads or holdout reads."""

    def __init__(self, store: BudgetedR2Store) -> None:
        self._store = store
        self._bytes = 0

    @staticmethod
    def _check_key(key: str) -> None:
        if (
            not isinstance(key, str) or not key or len(key) > 1024
            or key.startswith("/") or any(part in {"", ".", ".."} for part in key.split("/"))
            or "holdout" in key.lower() or not key.endswith(".json")
        ):
            raise ValueError("CORE100_READ_KEY_REJECTED")
        if key in _ALLOWED_EXACT:
            return
        if not key.startswith(_ALLOWED_PREFIXES):
            raise ValueError("CORE100_READ_KEY_REJECTED")
        if key.startswith(_ALLOWED_PREFIXES[2]) and not re.fullmatch(
            r"training/binance_usdm/crypto-core-v0[.]1/fingerprint-v0[.]2/runs/run=github-[0-9]+-1/manifest[.]json",
            key,
        ):
            raise ValueError("CORE100_READ_KEY_REJECTED")

    def get_bytes_if_exists(self, key: str) -> bytes | None:
        self._check_key(key)
        try:
            response = self._store.client.get_object(Bucket=self._store.bucket, Key=key)
        except Exception as exc:
            detail = getattr(exc, "response", {}) or {}
            if str(detail.get("Error", {}).get("Code", "")) in {"NoSuchKey", "NotFound", "404"} or (
                detail.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404
            ):
                return None
            raise
        stream = response["Body"]
        try:
            body = stream.read(_MAX_OBJECT_BYTES + 1)
        finally:
            stream.close()
        if not isinstance(body, bytes) or len(body) > _MAX_OBJECT_BYTES:
            raise ValueError("CORE100_READ_SIZE_INVALID")
        self._bytes += len(body)
        if self._bytes > _MAX_TOTAL_BYTES:
            raise ValueError("CORE100_TOTAL_READ_SIZE_EXCEEDED")
        digest = response.get("Metadata", {}).get("sha256")
        if digest and hashlib.sha256(body).hexdigest() != digest:
            raise ValueError("CORE100_METADATA_DIGEST_MISMATCH")
        return body

    def get_bytes_verified(self, key: str, *, expected_sha256: str) -> bytes:
        if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            raise ValueError("CORE100_EXPECTED_DIGEST_INVALID")
        body = self.get_bytes_if_exists(key)
        if body is None or hashlib.sha256(body).hexdigest() != expected_sha256:
            raise ValueError("CORE100_DIGEST_MISMATCH")
        return body

    def bucket_bytes(self) -> int:
        total = 0
        token = None
        seen_tokens: set[str] = set()
        seen_keys: set[str] = set()
        for _ in range(32):
            kwargs = {"Bucket": self._store.bucket, "MaxKeys": 1000}
            if token is not None:
                kwargs["ContinuationToken"] = token
            page = self._store.client.list_objects_v2(**kwargs)
            if not isinstance(page, dict) or type(page.get("IsTruncated")) is not bool:
                raise ValueError("CORE100_BUCKET_PAGE_INVALID")
            rows = page.get("Contents", [])
            if not isinstance(rows, list) or len(rows) > 1000:
                raise ValueError("CORE100_BUCKET_PAGE_INVALID")
            if "KeyCount" in page and (type(page["KeyCount"]) is not int or page["KeyCount"] != len(rows)):
                raise ValueError("CORE100_BUCKET_PAGE_INVALID")
            if "Contents" not in page and page.get("KeyCount") != 0:
                raise ValueError("CORE100_BUCKET_PAGE_INVALID")
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError("CORE100_BUCKET_ROW_INVALID")
                key, size = row.get("Key"), row.get("Size")
                if not isinstance(key, str) or not key or key in seen_keys or type(size) is not int or size < 0:
                    raise ValueError("CORE100_BUCKET_ROW_INVALID")
                seen_keys.add(key)
                total += size
            if not page["IsTruncated"]:
                if "NextContinuationToken" in page:
                    raise ValueError("CORE100_BUCKET_PAGE_INVALID")
                return total
            token = page.get("NextContinuationToken")
            if not isinstance(token, str) or not token or token in seen_tokens:
                raise ValueError("CORE100_BUCKET_PAGE_INVALID")
            seen_tokens.add(token)
        raise ValueError("CORE100_BUCKET_PAGE_LIMIT")


def compare_prepaid_core100(
    *, r2_snapshot: R2UsageSnapshot, d1_snapshot: D1UsageSnapshot,
    query_meter: PrepaidQueryMeter, clock_ms: Callable[[], int], slot_at_ms: int,
    database_evidence: DatabaseSizeEvidence, credentials: Mapping[str, str],
    verify_source: Callable[[], str], execution_enabled: bool = False,
) -> dict[str, object]:
    """Compare only; caller supplies independent source and exclusive-ownership checks."""
    if type(execution_enabled) is not bool:
        raise BudgetBlocked("BLOCKED_CORE100_EXECUTION_FLAG")
    if not execution_enabled:
        return {"status": "SKIPPED_DISABLED", "external_access_performed": False}
    if type(slot_at_ms) is not int or slot_at_ms <= 0 or (slot_at_ms - SLOT_OFFSET_MS) % SLOT_MS:
        raise BudgetBlocked("BLOCKED_CORE100_SLOT_INVALID")
    if not isinstance(r2_snapshot, R2UsageSnapshot) or not isinstance(d1_snapshot, D1UsageSnapshot):
        raise BudgetBlocked("BLOCKED_CORE100_USAGE_EVIDENCE")
    if not isinstance(database_evidence, DatabaseSizeEvidence) or not callable(verify_source):
        raise BudgetBlocked("BLOCKED_CORE100_BINDING")
    if not isinstance(credentials, Mapping) or set(credentials) != {
        "account_id", "bucket", "access_key_id", "secret_access_key",
    } or any(not isinstance(v, str) or not v.strip() for v in credentials.values()):
        raise BudgetBlocked("BLOCKED_CORE100_CREDENTIAL_BINDING")
    credentials = dict(credentials)
    r2_guard = CloudBudgetGuard(snapshot=r2_snapshot, clock_ms=clock_ms)
    d1_guard = D1UsageGuard(snapshot=d1_snapshot, clock_ms=clock_ms)
    slot_id = f"slot:{slot_at_ms}"
    database_id = os.environ.get("CLOUDFLARE_D1_DATABASE_ID", "")
    source_sha = verify_source()
    if not isinstance(source_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise BudgetBlocked("BLOCKED_CORE100_SOURCE")

    def validate_binding() -> None:
        if (credentials["account_id"] != os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
                or credentials["bucket"] != os.environ.get("R2_BUCKET_NAME", "")
                or database_id != os.environ.get("CLOUDFLARE_D1_DATABASE_ID", "")):
            raise BudgetBlocked("BLOCKED_CORE100_TARGET_CHANGED")
        if verify_source() != source_sha:
            raise BudgetBlocked("BLOCKED_CORE100_SOURCE_CHANGED")
        Core100PrepaidD1Client.validate_inputs(
            usage_guard=d1_guard, query_meter=query_meter, writer_id=WRITER, slot_id=slot_id,
        )
        database_evidence.validate(database_id=database_id, guard=d1_guard)

    validate_binding()
    # Read and validate frozen checkout documents before any D1 or R2 request.
    root = frozen.ROOT
    implementation = frozen._load_json(root / frozen.IMPLEMENTATION_RECEIPT_PATH)
    expected = implementation["successor_contract_sha256"]
    contract = frozen.validate_successor_contract(
        contract_bytes=(root / frozen.SUCCESSOR_CONTRACT_PATH).read_bytes(),
        expected_sha256=expected, parent_contract_bytes=(root / frozen.PARENT_CONTRACT_PATH).read_bytes(),
    )
    _, implementation_sha = frozen._validate_authority_and_implementation(
        contract=contract, contract_sha256=expected, root=root,
    )
    data_config, _, _ = frozen.runner.load_authority_pair(
        root / frozen.DATA_CONFIG_PATH, root / frozen.DATA_AUTHORITY_PATH,
    )
    now = clock_ms()
    if type(now) is not int:
        raise BudgetBlocked("BLOCKED_CORE100_CLOCK")
    frozen.runner.require_execution_window(
        data_config, observed_at=datetime.fromtimestamp(now / 1000, UTC), operation="training",
    )
    validate_binding()
    client = Core100PrepaidD1Client(
        api_token=os.environ.get("CLOUDFLARE_D1_API_TOKEN", ""),
        account_id=credentials["account_id"], database_id=database_id, usage_guard=d1_guard,
        query_meter=query_meter, writer_id=WRITER, slot_id=slot_id,
        database_evidence=database_evidence, execution_enabled=True,
    )
    ticket = query_meter.report()["ticket_envelope_charged_in_full"]
    reservation = SharedWriterReservation(
        writer_id=WRITER, slot_id=slot_id, idempotency_key=slot_id,
        slot_at_ms=slot_at_ms, reserved_at_ms=clock_ms(), provider_requests=0,
        r2_class_a=32, r2_class_b=32, r2_new_bytes=0,
        d1_queries=ticket["queries"], d1_rows_read=ticket["rows_read"],
        d1_rows_written=ticket["rows_written"], d1_storage_growth_bytes=ticket["storage_bytes"],
    )
    budget = SharedWriterR2BudgetV05.admit(
        reservation=reservation, guard=r2_guard, execute=client.query,
        query_meter=query_meter, validate_binding=validate_binding, execution_enabled=True,
    )
    stage = "CONSTRUCT_STORE"
    try:
        store = _Core100ReadOnlyStore(BudgetedR2Store.from_credentials(
            account_id=credentials["account_id"], bucket=credentials["bucket"],
            access_key_id=credentials["access_key_id"], secret_access_key=credentials["secret_access_key"],
            before_external=budget.reserve,
        ))
        stage = "HEADROOM"
        if store.bucket_bytes() >= frozen.HEADROOM_LIMIT:
            raise BudgetBlocked("BLOCKED_CORE100_BUCKET_HEADROOM")
        stage = "READ_AND_COMPARE"
        _, latest, manifest = frozen._load_v02_latest(store)
        if latest is None or manifest is None:
            raise ValueError("CORE100_BASELINE_MISSING")
        catalog, state, _, dataset_fingerprint = frozen.runner.load_dataset_index(store, data_config)
        if not frozen._dataset_is_exact(catalog, state):
            raise ValueError("CORE100_DATASET_INVALID")
        if manifest.get("implementation_receipt_git_blob_sha") != implementation_sha:
            raise ValueError("CORE100_IMPLEMENTATION_CHANGED")
        current = frozen._current_fingerprint(
            contract=contract, dataset_fingerprint=dataset_fingerprint, root=root, checkout_sha=source_sha,
        )
        decision = frozen.compare_fingerprints(
            contract=contract, current=current, previous=manifest["training_fingerprint_v0_2"],
        )
        if decision.get("status") not in {"NO_CHANGE", "REVIEW_REQUIRED"}:
            raise ValueError("CORE100_DECISION_INVALID")
        validate_binding()
        if r2_guard.storage_capacity_state() == "HARD_STOP":
            raise BudgetBlocked("BLOCKED_CORE100_HEADROOM")
        return {
            "status": decision["status"], "reason": decision["reason"],
            "training_performed": False, "r2_writes_performed": False, "holdout_accessed": False,
            "provider_requests_performed": 0, "central_reservation_retained": True,
            "attempted_usage": budget.attempted_usage(), "source_main_sha": source_sha,
            "automatic_retry_allowed": False, "paper_activation_allowed": False,
            "independent_job_identity_verified": False, "production_authority_verified": False,
        }
    except Exception:
        return {
            "status": "REVIEW_REQUIRED", "reason": "CORE100_COMPARISON_UNVERIFIED", "stage": stage,
            "training_performed": False, "r2_writes_performed": False, "holdout_accessed": False,
            "provider_requests_performed": 0, "central_reservation_retained": True,
            "attempted_usage": budget.attempted_usage(), "automatic_retry_allowed": False,
            "paper_activation_allowed": False,
        }
