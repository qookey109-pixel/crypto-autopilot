"""Cloud Paper Loop R2 wrapper with a reservation hook for every S3 request.

Use from_credentials in the production composition so SDK retries are disabled.
Supplying an externally configured client cannot prove its retry policy.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from crypto_autopilot.paper.cloud_budget_v0_1 import CloudBudgetGuard
from crypto_autopilot.storage.r2 import R2ObjectReceipt


class BudgetedR2Client:
    """Narrow proxy that reserves before each S3 operation."""

    def __init__(
        self, *, client: Any, before_external: Callable[[str, int], None],
    ) -> None:
        self._client = client
        self._before_external = before_external

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        body = kwargs.get("Body")
        if not isinstance(body, bytes):
            raise ValueError("budgeted R2 writes require a bounded bytes body")
        self._before_external("R2_CLASS_A", len(body))
        return self._client.put_object(**kwargs)

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        self._before_external("R2_CLASS_B", 0)
        return self._client.get_object(**kwargs)

    def list_objects_v2(self, **kwargs: Any) -> dict[str, Any]:
        self._before_external("R2_CLASS_A", 0)
        return self._client.list_objects_v2(**kwargs)


@dataclass(frozen=True, slots=True)
class BudgetedR2Policy:
    maximum_list_pages: int = 100
    maximum_list_keys_per_page: int = 1000


class BudgetedR2Store:
    """R2Store-compatible methods used by R2PaperRunStore, without editing it."""

    def __init__(
        self,
        *,
        client: Any,
        bucket: str,
        before_external: Callable[[str, int], None] | None = None,
        budget_guard: CloudBudgetGuard | None = None,
        freshness_check: Callable[[], None] | None = None,
        policy: BudgetedR2Policy = BudgetedR2Policy(),
    ) -> None:
        if not isinstance(bucket, str) or not bucket:
            raise ValueError("R2 bucket is required")
        if (before_external is None) == (budget_guard is None):
            raise ValueError("provide exactly one R2 budget reservation mechanism")
        if freshness_check is not None and budget_guard is None:
            raise ValueError("freshness_check requires a shared cloud budget guard")
        if freshness_check is not None and not callable(freshness_check):
            raise ValueError("freshness_check must be callable")
        self.bucket = bucket
        self.policy = policy
        self.budget_guard = budget_guard
        if budget_guard is None:
            reserve = before_external
        else:
            def reserve(operation: str, size: int) -> None:
                if freshness_check is not None:
                    freshness_check()
                budget_guard.reserve(operation, size)
        if not callable(reserve):
            raise ValueError("R2 budget reservation callback is required")
        self.client = BudgetedR2Client(
            client=client, before_external=reserve,
        )

    @classmethod
    def from_credentials(
        cls,
        *,
        account_id: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        before_external: Callable[[str, int], None] | None = None,
        budget_guard: CloudBudgetGuard | None = None,
        freshness_check: Callable[[], None] | None = None,
        policy: BudgetedR2Policy = BudgetedR2Policy(),
    ) -> BudgetedR2Store:
        if not all((account_id, bucket, access_key_id, secret_access_key)):
            raise ValueError("R2 account, bucket and S3 credentials are required")
        import boto3
        from botocore.config import Config

        client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
            config=Config(retries={"max_attempts": 0, "mode": "standard"}),
        )
        return cls(
            client=client, bucket=bucket, before_external=before_external,
            budget_guard=budget_guard, freshness_check=freshness_check,
            policy=policy,
        )

    def put_bytes(
        self,
        key: str,
        payload: bytes,
        *,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> R2ObjectReceipt:
        sha256 = hashlib.sha256(payload).hexdigest()
        response = self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=payload,
            ContentType=content_type,
            Metadata={"sha256": sha256, **(metadata or {})},
        )
        return R2ObjectReceipt(
            bucket=self.bucket, key=key, bytes=len(payload), sha256=sha256,
            etag=str(response.get("ETag")).strip('"') if response.get("ETag") else None,
        )

    def get_bytes_verified(self, key: str, *, expected_sha256: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        payload = response["Body"].read()
        actual_sha256 = hashlib.sha256(payload).hexdigest()
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"R2 round-trip SHA-256 mismatch for {key}: "
                f"expected {expected_sha256}, got {actual_sha256}"
            )
        return payload

    def get_bytes_if_exists(self, key: str) -> bytes | None:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            response_payload = getattr(exc, "response", {}) or {}
            code = str(response_payload.get("Error", {}).get("Code", ""))
            status = response_payload.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if code in {"NoSuchKey", "NotFound", "404"} or status == 404:
                return None
            raise

        payload = response["Body"].read()
        expected_sha256 = str(response.get("Metadata", {}).get("sha256") or "")
        if expected_sha256 and hashlib.sha256(payload).hexdigest() != expected_sha256:
            raise ValueError(f"R2 metadata SHA-256 mismatch for {key}")
        return payload

    def list_keys(self, prefix: str) -> tuple[str, ...]:
        if not prefix:
            raise ValueError("R2 list prefix is required")
        token: str | None = None
        seen_tokens: set[str] = set()
        keys: list[str] = []
        for _ in range(self.policy.maximum_list_pages):
            request: dict[str, object] = {
                "Bucket": self.bucket,
                "Prefix": prefix,
                "MaxKeys": self.policy.maximum_list_keys_per_page,
            }
            if token is not None:
                request["ContinuationToken"] = token
            page = self.client.list_objects_v2(**request)
            contents = page.get("Contents", [])
            if not isinstance(contents, list):
                raise ValueError("R2 list response Contents must be an array")
            for row in contents:
                key = row.get("Key") if isinstance(row, dict) else None
                if not isinstance(key, str) or not key:
                    raise ValueError("R2 list response object key is invalid")
                keys.append(key)
            if not page.get("IsTruncated", False):
                return tuple(sorted(set(keys)))
            next_token = page.get("NextContinuationToken")
            if not isinstance(next_token, str) or not next_token or next_token in seen_tokens:
                raise ValueError("R2 list continuation token is missing or repeated")
            seen_tokens.add(next_token)
            token = next_token
        raise ValueError("R2 list page limit exceeded")
