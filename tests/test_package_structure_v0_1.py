from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "src" / "crypto_autopilot"

ALLOWED_ROOT_MODULES = {
    "__init__.py",
    "backtest.py",
    "binance_expansion_plan.py",
    "binance_funding.py",
    "binance_funding_budget.py",
    "binance_funding_materialization_plan.py",
    "binance_funding_materialization_plan_v0_2.py",
    "binance_historical.py",
    "historical.py",
    "lineage.py",
    "models.py",
    "provider_metadata_capture_v0_10.py",
    "provider_metadata_capture_v0_12.py",
    "provider_metadata_capture_v0_2.py",
    "provider_metadata_capture_v0_8.py",
    "provider_metadata_capture_v0_8_successor.py",
    "provider_metadata_stability_v0_11.py",
    "risk.py",
    "sstate_adapter.py",
    "sstate_evidence.py",
    "strategy.py",
    "strategy_edge_validation.py",
    "strategy_research_loop.py",
    "technical.py",
    "universe.py",
}

DOMAIN_PACKAGES = {
    "binance",
    "exchanges",
    "features",
    "history",
    "paper",
    "providers",
    "research",
    "storage",
    "training",
}

NEW_DESCRIPTION_ONLY_PACKAGES = DOMAIN_PACKAGES - {"exchanges", "storage"}

LEGACY_MODULES = {
    "advanced_technical",
    "binance_2025_pilot",
    "binance_capacity",
    "binance_coverage",
    "binance_funding_coverage",
    "binance_funding_materializer_v0_2",
    "binance_spot_history",
    "binance_training_catalog",
    "binance_vision",
    "detailed_history",
    "detailed_training",
    "ephemeral_storage",
    "equivalence_forensics",
    "evaluation_integrity",
    "experiment_registry",
    "historical_admission",
    "historical_liquidity",
    "historical_sstate",
    "historical_universe",
    "historical_universe_review",
    "market_features",
    "market_structure",
    "monthly_universe_review",
    "multi_timeframe_technical",
    "online_r2_training",
    "online_training",
    "orderflow",
    "paper_exploration",
    "paper_simulation_demo",
    "paper_training",
    "parameter_sweep",
    "pilot_evidence",
    "provider_equivalence",
    "provider_metadata_capture_suspension_v0_2",
    "r2_budget",
    "replay_readiness",
    "research_automation_health",
    "research_context",
    "research_signal_ingest_v0_2",
    "research_signal_layer",
    "research_signal_quality",
    "resource_planning",
    "shadow_ablation",
    "training_quality",
    "weekly_model_review",
}


class PackageStructureV01Tests(unittest.TestCase):
    def test_package_root_is_allowlisted(self) -> None:
        actual = {path.name for path in PACKAGE_ROOT.glob("*.py")}
        self.assertEqual(actual, ALLOWED_ROOT_MODULES)

    def test_domain_packages_exist(self) -> None:
        for package in DOMAIN_PACKAGES:
            with self.subTest(package=package):
                init_file = PACKAGE_ROOT / package / "__init__.py"
                self.assertTrue(init_file.is_file())

    def test_new_package_initializers_do_not_hide_reexports(self) -> None:
        for package in NEW_DESCRIPTION_ONLY_PACKAGES:
            with self.subTest(package=package):
                tree = ast.parse(
                    (PACKAGE_ROOT / package / "__init__.py").read_text(encoding="utf-8")
                )
                self.assertEqual(len(tree.body), 1)
                self.assertIsInstance(tree.body[0], ast.Expr)
                self.assertIsInstance(tree.body[0].value, ast.Constant)
                self.assertIsInstance(tree.body[0].value.value, str)

    def test_python_imports_do_not_use_removed_flat_modules(self) -> None:
        search_roots = (ROOT / "src", ROOT / "scripts", ROOT / "tests")
        violations: list[str] = []
        for search_root in search_roots:
            for source in search_root.rglob("*.py"):
                tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        module = node.module
                        if module.startswith("crypto_autopilot."):
                            relative_module = module.removeprefix("crypto_autopilot.")
                            head = relative_module.split(".", 1)[0]
                            if head in LEGACY_MODULES:
                                violations.append(f"{source}:{node.lineno}:{module}")
                        elif node.level and module.split(".", 1)[0] in LEGACY_MODULES:
                            violations.append(f"{source}:{node.lineno}:{module}")
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name.startswith("crypto_autopilot."):
                                relative_module = alias.name.removeprefix("crypto_autopilot.")
                                if relative_module.split(".", 1)[0] in LEGACY_MODULES:
                                    violations.append(f"{source}:{node.lineno}:{alias.name}")
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
