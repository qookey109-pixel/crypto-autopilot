"""Per-invocation R2 limits for the sequential Research Signal collector."""
from __future__ import annotations

from typing import Any

from crypto_autopilot.research.signal_ingest_v0_2 import ResearchSignalIngestError


# Two complete inventories of up to 32 pages, two immutable object reads,
# and one PUT for each of the payload, manifest, and latest pointer.
_ATTEMPT_LIMITS = {"ListObjectsV2": 64, "GetObject": 2, "PutObject": 3}


class SignalR2Attempts:
    def __init__(self, max_write_bytes: int) -> None:
        if type(max_write_bytes) is not int or max_write_bytes <= 0:
            raise ResearchSignalIngestError("invalid research R2 write reservation")
        self.max_write_bytes = max_write_bytes
        self.attempts = dict.fromkeys(_ATTEMPT_LIMITS, 0)
        self.put_payload_bytes = 0
        self.block_reason: str | None = None

    def _block(self, reason: str) -> None:
        self.block_reason = reason
        raise ResearchSignalIngestError(reason)

    def before_send(self, *, event_name: str, request: Any, **kwargs: Any) -> None:
        """Debit before transport, including repeat attempts and failed responses."""
        if self.block_reason:
            raise ResearchSignalIngestError(self.block_reason)
        operation = event_name.removeprefix("before-send.s3.")
        if operation not in _ATTEMPT_LIMITS:
            self._block("R2_OPERATION_OUTSIDE_SIGNAL_SCOPE")
        if self.attempts[operation] >= _ATTEMPT_LIMITS[operation]:
            self._block("R2_SIGNAL_ATTEMPT_LIMIT")

        if operation == "PutObject":
            # AWS chunk framing can make Content-Length larger than object size.
            length = request.headers.get("x-amz-decoded-content-length")
            if length is None:
                length = request.headers.get("Content-Length")
            if isinstance(length, bytes):
                try:
                    length = length.decode("ascii")
                except UnicodeDecodeError:
                    self._block("R2_SIGNAL_PUT_LENGTH_UNKNOWN")
            if not (isinstance(length, str) and 0 < len(length) <= 16
                    and length.isascii() and length.isdigit()):
                self._block("R2_SIGNAL_PUT_LENGTH_UNKNOWN")
            size = int(length)
            if self.put_payload_bytes + size > self.max_write_bytes:
                self._block("R2_SIGNAL_PUT_BYTES_LIMIT")
            self.put_payload_bytes += size
        self.attempts[operation] += 1

    def report(self) -> dict[str, object]:
        return {
            "schema": "research-signal-r2-attempts-v0.1",
            "scope": "THIS_COLLECTOR_INVOCATION",
            "admitted_send_attempts": dict(self.attempts),
            "attempted_put_payload_bytes": self.put_payload_bytes,
            "block_reason": self.block_reason,
        }
