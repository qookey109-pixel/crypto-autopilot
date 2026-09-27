from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass


class R2ObjectAlreadyExistsError(ValueError):
    """Raised when an immutable conditional write loses an existing-key race."""


@dataclass(frozen=True, slots=True)
class R2ObjectReceipt:
    bucket: str
    key: str
    bytes: int
    sha256: str
    etag: str | None


class R2Store:
    """Small Cloudflare R2 adapter over its S3-compatible API.

    Credentials must be supplied by the environment/secret manager. This class
    never persists secrets and never contains trading-execution logic. An
    optional pre-access callback lets a caller reserve budget before each
    individual provider-facing R2 request.
    """

    def __init__(
        self,
        *,
        account_id: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        endpoint_url: str | None = None,
        before_external: Callable[[str, int], None] | None = None,
    ) -> None:
        if not all([account_id, bucket, access_key_id, secret_access_key]):
            raise ValueError("R2 account, bucket and S3 credentials are required")
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("boto3 is required for R2 storage") from exc

        self.bucket = bucket
        self.before_external = before_external
        self.endpoint_url = endpoint_url or (
            f"https://{account_id}.r2.cloudflarestorage.com"
        )
        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
        )

    def _before(self, operation: str, new_bytes: int = 0) -> None:
        callback = getattr(self, "before_external", None)
        if callback is not None:
            callback(operation, new_bytes)

    @staticmethod
    def _receipt(bucket: str, key: str, payload: bytes, response: dict) -> R2ObjectReceipt:
        return R2ObjectReceipt(
            bucket=bucket,
            key=key,
            bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            etag=str(response.get("ETag")).strip('"') if response.get("ETag") else None,
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
        self._before("R2_CLASS_A", len(payload))
        response = self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=payload,
            ContentType=content_type,
            Metadata={"sha256": sha256, **(metadata or {})},
        )
        return self._receipt(self.bucket, key, payload, response)

    def put_bytes_if_absent(
        self,
        key: str,
        payload: bytes,
        *,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> R2ObjectReceipt:
        sha256 = hashlib.sha256(payload).hexdigest()
        self._before("R2_CLASS_A", len(payload))
        try:
            response = self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=payload,
                ContentType=content_type,
                Metadata={"sha256": sha256, **(metadata or {})},
                IfNoneMatch="*",
            )
        except Exception as exc:
            error = getattr(exc, "response", {}) or {}
            code = str(error.get("Error", {}).get("Code", ""))
            status = error.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if code in {"PreconditionFailed", "412"} or status == 412:
                raise R2ObjectAlreadyExistsError(key) from exc
            raise
        return self._receipt(self.bucket, key, payload, response)

    def get_bytes_verified(self, key: str, *, expected_sha256: str) -> bytes:
        self._before("R2_CLASS_B")
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
        """Read an object if it exists and verify SHA-256 metadata when present."""
        self._before("R2_CLASS_B")
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except Exception as exc:  # boto3's ClientError is optional until runtime
            response_payload = getattr(exc, "response", {}) or {}
            code = str(response_payload.get("Error", {}).get("Code", ""))
            status = response_payload.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if code in {"NoSuchKey", "NotFound", "404"} or status == 404:
                return None
            raise

        payload = response["Body"].read()
        expected_sha256 = str(response.get("Metadata", {}).get("sha256") or "")
        if expected_sha256:
            actual_sha256 = hashlib.sha256(payload).hexdigest()
            if actual_sha256 != expected_sha256:
                raise ValueError(
                    f"R2 metadata SHA-256 mismatch for {key}: "
                    f"expected {expected_sha256}, got {actual_sha256}"
                )
        return payload

    def list_keys(self, prefix: str, *, max_pages: int = 100) -> tuple[str, ...]:
        """List bounded keys, reserving one Class A operation before each page."""
        if not prefix or type(max_pages) is not int or max_pages < 1:
            raise ValueError("R2 list prefix and positive page limit are required")
        token: str | None = None
        seen_tokens: set[str] = set()
        keys: list[str] = []
        for _ in range(max_pages):
            self._before("R2_CLASS_A")
            request: dict[str, object] = {
                "Bucket": self.bucket, "Prefix": prefix, "MaxKeys": 1000,
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
