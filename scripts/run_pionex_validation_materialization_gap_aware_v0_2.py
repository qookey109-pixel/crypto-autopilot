#!/usr/bin/env python3
"""Run Pionex Validation Dataset V0.2 with existing secret-safe diagnostics."""
from __future__ import annotations

from crypto_autopilot.exchanges import pionex_public
from crypto_autopilot.history.pionex_gap_boundary_v0_1 import GapBoundaryKlineClient
from crypto_autopilot.history.pionex_page_audit_diagnostics_v0_1 import (
    install_page_audit_diagnostics,
)
from crypto_autopilot.history.pionex_provider_error_diagnostics_v0_1 import (
    ProviderErrorDiagnosticKlineClient,
    install_provider_error_diagnostics,
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
install_page_audit_diagnostics()
install_provider_error_diagnostics()

from run_pionex_validation_materialization_v0_2 import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
