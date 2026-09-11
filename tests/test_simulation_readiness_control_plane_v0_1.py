from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class SimulationReadinessControlPlaneV01Tests(unittest.TestCase):
    def _workflow(self, name: str) -> str:
        return (WORKFLOWS / name).read_text(encoding="utf-8")

    def test_public_readiness_workflows_are_manual_only_and_secret_free(self) -> None:
        for name in (
            "pionex-historical-reach-v0-3.yml",
            "pionex-research-universe-v0-1.yml",
            "pionex-funding-history-v0-1.yml",
        ):
            text = self._workflow(name)
            self.assertIn("workflow_dispatch:", text, name)
            self.assertNotIn("schedule:", text, name)
            self.assertNotIn("secrets.", text, name)
            self.assertIn("permissions:\n  contents: read", text, name)
            self.assertIn("persist-credentials: false", text, name)
            self.assertIn("requirements/ci-constraints.txt", text, name)
            self.assertNotIn("R2_", text, name)
            self.assertNotIn("PIONEX-KEY", text, name)

    def test_universe_snapshot_workflow_keeps_selection_and_trading_boundaries(self) -> None:
        text = self._workflow("pionex-research-universe-v0-1.yml")
        self.assertIn("run_pionex_research_universe_v0_1.py", text)
        self.assertIn('report["provider_request_count"] == 3', text)
        self.assertIn('report["selected_market_count"] >= 150', text)
        self.assertIn('report["crypto_core_count"] == 100', text)
        self.assertIn('report["historical_materialization_authorized"] is False', text)
        self.assertIn('report["real_money_orders_authorized"] is False', text)
        self.assertIn('report["live_trading_authorized"] is False', text)

    def test_funding_workflow_keeps_exact_window_and_no_admission(self) -> None:
        text = self._workflow("pionex-funding-history-v0-1.yml")
        self.assertIn("run_pionex_funding_history_v0_1.py", text)
        self.assertIn('report["symbol"] == "BTC_USDT_PERP"', text)
        self.assertIn('report["window_start_utc"] == "2026-08-01T00:00:00Z"', text)
        self.assertIn('report["window_end_exclusive_utc"] == "2026-08-28T00:00:00Z"', text)
        self.assertIn('1 <= report["requests"] <= 3', text)
        self.assertIn('report["left_boundary_reached"] is True', text)
        self.assertIn('report["simulation_data_admission_authorized"] is False', text)
        self.assertIn('report["formal_backtest_admission_authorized"] is False', text)
        self.assertIn('report["live_trading_authorized"] is False', text)


if __name__ == "__main__":
    unittest.main()
