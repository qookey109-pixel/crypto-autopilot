from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

CHECKOUT_V6_SHA = "d23441a48e516b6c34aea4fa41551a30e30af803"
SETUP_PYTHON_V6_SHA = "ece7cb06caefa5fff74198d8649806c4678c61a1"
UPLOAD_ARTIFACT_V7_SHA = "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
UPLOAD_PAGES_ARTIFACT_V5_SHA = "fc324d3547104276b827a68afc52ff2a11cc49c9"
CONFIGURE_PAGES_V6_SHA = "45bfe0192ca1faeb007ade9deae92b16b8254a0d"
DEPLOY_PAGES_V5_SHA = "cd2ce8fcbc39b97be8ca5fce6e763baed58fa128"
CACHE_V5_SHA = "caa296126883cff596d87d8935842f9db880ef25"

APPROVED_CRITICAL_ACTIONS = {
    "actions/checkout": CHECKOUT_V6_SHA,
    "actions/setup-python": SETUP_PYTHON_V6_SHA,
    "actions/upload-artifact": UPLOAD_ARTIFACT_V7_SHA,
    "actions/upload-pages-artifact": UPLOAD_PAGES_ARTIFACT_V5_SHA,
    "actions/configure-pages": CONFIGURE_PAGES_V6_SHA,
    "actions/deploy-pages": DEPLOY_PAGES_V5_SHA,
    "actions/cache": CACHE_V5_SHA,
}

CURRENT = (
    "ci.yml",
    "provider-equivalence-v0-10-render-metadata-capture.yml",
    "validate-v0-11-metadata-stability-evaluator.yml",
    "provider-equivalence-v0-8-render-metadata-capture.yml",
    "validate-v0-7-render-metadata-capture-protocol.yml",
    "dashboard-authority-snapshot.yml",
    "dashboard-github-pages.yml",
    "dashboard-static-smoke.yml",
    "pionex-public-paper-training-v0-1.yml",
)

PINNED_CRITICAL = (
    "ci.yml",
    "provider-equivalence-v0-10-render-metadata-capture.yml",
    "validate-v0-11-metadata-stability-evaluator.yml",
    "dashboard-authority-snapshot.yml",
    "dashboard-github-pages.yml",
    "dashboard-static-smoke.yml",
    "pionex-public-paper-training-v0-1.yml",
)


def _action_refs(text: str, action: str) -> list[str]:
    prefix = f"- uses: {action}@"
    refs: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            refs.append(stripped[len(prefix) :].split()[0])
    return refs


def _uses_entries(text: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- uses: "):
            continue
        token = stripped[len("- uses: ") :].split()[0]
        action, ref = token.rsplit("@", 1)
        entries.append((action, ref))
    return entries


class CurrentWorkflowActionsNode24Tests(unittest.TestCase):
    def test_all_workflows_use_node24_checkout_with_nonpersistent_credentials(self) -> None:
        allowed_refs = {"v6", CHECKOUT_V6_SHA}
        for path in sorted(WORKFLOWS.glob("*.yml")):
            with self.subTest(workflow=path.name):
                text = path.read_text(encoding="utf-8")
                checkout_refs = _action_refs(text, "actions/checkout")
                if not checkout_refs:
                    continue
                self.assertTrue(
                    all(ref in allowed_refs for ref in checkout_refs),
                    f"{path.name}: checkout actions must use v6 or approved v6 SHA: {checkout_refs}",
                )
                self.assertEqual(
                    text.count("persist-credentials: false"),
                    len(checkout_refs),
                    f"{path.name}: every checkout must explicitly avoid persisted git credentials",
                )

    def test_all_setup_python_users_are_on_node24_v6(self) -> None:
        allowed_refs = {"v6", SETUP_PYTHON_V6_SHA}
        for path in sorted(WORKFLOWS.glob("*.yml")):
            with self.subTest(workflow=path.name):
                setup_refs = _action_refs(path.read_text(encoding="utf-8"), "actions/setup-python")
                self.assertTrue(
                    all(ref in allowed_refs for ref in setup_refs),
                    f"{path.name}: setup-python actions must use v6 or approved v6 SHA: {setup_refs}",
                )

    def test_production_critical_workflows_pin_all_actions_to_approved_shas(self) -> None:
        for name in PINNED_CRITICAL:
            with self.subTest(workflow=name):
                entries = _uses_entries((WORKFLOWS / name).read_text(encoding="utf-8"))
                self.assertGreater(len(entries), 0)
                for action, ref in entries:
                    self.assertIn(
                        action,
                        APPROVED_CRITICAL_ACTIONS,
                        f"{name}: unapproved or third-party action {action}",
                    )
                    self.assertEqual(
                        ref,
                        APPROVED_CRITICAL_ACTIONS[action],
                        f"{name}: {action} must use its reviewed immutable SHA",
                    )
                    self.assertRegex(ref, r"^[0-9a-f]{40}$")

    def test_current_workflows_remain_in_global_node24_scope(self) -> None:
        for name in CURRENT:
            with self.subTest(workflow=name):
                text = (WORKFLOWS / name).read_text(encoding="utf-8")
                checkout_refs = _action_refs(text, "actions/checkout")
                self.assertGreater(len(checkout_refs), 0)
                self.assertTrue(all(ref in {"v6", CHECKOUT_V6_SHA} for ref in checkout_refs))
                self.assertNotIn("actions/checkout@v4", text)
                self.assertNotIn("actions/setup-python@v5", text)

    def test_v0_10_capture_schedule_and_authority_markers_are_preserved(self) -> None:
        text = (WORKFLOWS / "provider-equivalence-v0-10-render-metadata-capture.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(_action_refs(text, "actions/checkout").count(CHECKOUT_V6_SHA), 3)
        self.assertEqual(text.count("persist-credentials: false"), 3)
        self.assertIn('    - cron: "17,47 * 27,28,29,30,31 8 *"', text)
        self.assertIn('    - cron: "17,47 * 1,2,3 9 *"', text)
        self.assertIn('    - cron: "17,47 0,1 4 9 *"', text)
        self.assertIn("METADATA_RELAY_TOKEN: ${{ secrets.METADATA_RELAY_TOKEN }}", text)
        self.assertIn("--mode capture", text)
        self.assertIn("holdout_candles_accessed", text)
        self.assertIn("source_switch_authorized", text)
        self.assertIn("live_trading_authorized", text)

    def test_dashboard_static_smoke_name_no_longer_claims_d1_runtime(self) -> None:
        text = (WORKFLOWS / "dashboard-static-smoke.yml").read_text(encoding="utf-8")
        self.assertIn("name: Dashboard Static Smoke", text)
        self.assertNotIn("Dashboard D1 Static Smoke", text)


if __name__ == "__main__":
    unittest.main()
