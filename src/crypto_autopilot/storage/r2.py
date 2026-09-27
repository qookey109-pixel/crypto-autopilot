from __future__ import annotations

import hashlib
from dataclasses import dataclass


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
    never persists secrets and never contains trading-execution logic.
    """

    def __init__(
        self,
        *,
        account_id: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        endpoint_url: str | None = None,
    ) -> None:
        if not all([account_id, bucket, access_key_id, secret_access_key]):
            raise ValueError("R2 account, bucket and S3 credentials are required")
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("boto3 is required for R2 storage") from exc

        self.bucket = bucket
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
            bucket=self.bucket,
            key=key,
            bytes=len(payload),
            sha256=sha256,
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
        """Read an object if it exists and verify the SHA-256 metadata when present."""

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
