#!/usr/bin/env python3
"""Run Pionex Validation Dataset V0.2 with secret-safe boundary adapters."""
from __future__ import annotations

from crypto_autopilot.exchanges import pionex_public
from crypto_autopilot.history import pionex_validation_materialization_v0_2 as v02_materialization
from crypto_autopilot.history.pionex_gap_boundary_v0_1 import GapBoundaryKlineClient
from crypto_autopilot.history.pionex_page_audit_diagnostics_v0_1 import (
    install_page_audit_diagnostics,
)
from crypto_autopilot.history.pionex_provider_error_diagnostics_v0_1 import (
    ProviderErrorDiagnosticKlineClient,
    install_provider_error_diagnostics,
)
from crypto_autopilot.history.pionex_trailing_coverage_v0_2 import (
    collect_partition_v0_2_with_trailing_coverage,
)


_BasePionexPublicClient = pionex_public.PionexPublicClient


class _GapAwarePionexPublicClient:
    def __init__(self, *args, **kwargs) -> None:
        self._client = ProviderErrorDiagnosticKlineClient(
            GapBoundaryKlineClient(_BasePionexPublicClient(*args, **kwargs))
        )

    @property
    def provider_error_diagnostics(self) -> dict[str, object]:
        return self._client.provider_error_diagnostics

    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ):
        return self._client.get_klines(
            symbol,
            interval,
            limit=limit,
            end_time_ms=end_time_ms,
        )


pionex_public.PionexPublicClient = _GapAwarePionexPublicClient
# The reviewed V0.2 runtime imports collect_partition_v0_2 by value. Patch the
# V0.2 module before importing the runner so only this successor execution path
# gains explicit trailing-history coverage; frozen V0.1 remains untouched.
v02_materialization.collect_partition_v0_2 = collect_partition_v0_2_with_trailing_coverage
install_page_audit_diagnostics()
install_provider_error_diagnostics()

from run_pionex_validation_materialization_v0_2 import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
