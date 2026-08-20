from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONSTRAINTS = ROOT / "requirements" / "ci-constraints.txt"
WORKFLOWS = ROOT / ".github" / "workflows"
SETUP_PYTHON_V6_SHA = "ece7cb06caefa5fff74198d8649806c4678c61a1"

EXPECTED = {
    "boto3": "1.43.75",
    "botocore": "1.43.75",
    "jmespath": "1.1.0",
    "pyarrow": "21.0.0",
    "python-dateutil": "2.9.0.post0",
    "s3transfer": "0.19.2",
    "six": "1.17.0",
    "urllib3": "2.7.0",
    "pytest": "9.1.1",
    "iniconfig": "2.3.0",
    "packaging": "26.3",
    "pluggy": "1.6.0",
    "pygments": "2.21.0",
}

CRITICAL = (
    "ci.yml",
    "provider-equivalence-v0-10-render-metadata-capture.yml",
    "validate-v0-11-metadata-stability-evaluator.yml",
    "provider-equivalence-v0-8-render-metadata-capture.yml",
    "validate-v0-7-render-metadata-capture-protocol.yml",
)


def _constraint_map() -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in CONSTRAINTS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==", 1)
        result[name] = version
    return result


class CIDependencyConstraintsTests(unittest.TestCase):
    def test_constraints_match_the_validated_pr135_snapshot(self) -> None:
        self.assertEqual(_constraint_map(), EXPECTED)

    def test_public_project_metadata_keeps_compatibility_ranges(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertEqual(
            project["dependencies"],
            ["boto3>=1.35,<2", "pyarrow>=18,<22"],
        )

    def test_current_scientific_workflows_do_not_use_unconstrained_pip_installs(self) -> None:
        for name in CRITICAL:
            with self.subTest(workflow=name):
                text = (WORKFLOWS / name).read_text(encoding="utf-8")
                self.assertNotIn("python -m pip install -e .", text)
                self.assertNotIn("python -m pip install pytest", text)
                if "pip install" in text:
                    self.assertIn("requirements/ci-constraints.txt", text)

    def test_constraints_changes_revalidate_versioned_scientific_workflows(self) -> None:
        for name in (
            "provider-equivalence-v0-10-render-metadata-capture.yml",
            "validate-v0-11-metadata-stability-evaluator.yml",
            "provider-equivalence-v0-8-render-metadata-capture.yml",
            "validate-v0-7-render-metadata-capture-protocol.yml",
        ):
            with self.subTest(workflow=name):
                text = (WORKFLOWS / name).read_text(encoding="utf-8")
                trigger_section = text.split("permissions:", 1)[0]
                self.assertIn("requirements/ci-constraints.txt", trigger_section)
                self.assertIn("tests/test_ci_dependency_constraints.py", trigger_section)

    def test_v0_10_capture_pins_python_before_freshness_and_provider_access(self) -> None:
        text = (WORKFLOWS / "provider-equivalence-v0-10-render-metadata-capture.yml").read_text(
            encoding="utf-8"
        )
        capture = text.split("\n  capture:\n", 1)[1]
        setup_index = capture.index(f"- uses: actions/setup-python@{SETUP_PYTHON_V6_SHA}")
        freshness_index = capture.index("- id: freshness")
        install_index = capture.index("python -m pip install -c requirements/ci-constraints.txt -e .")
        provider_index = capture.index("python scripts/capture_provider_equivalence_v0_10_metadata.py")
        self.assertLess(setup_index, freshness_index)
        self.assertLess(freshness_index, install_index)
        self.assertLess(install_index, provider_index)
        self.assertIn('python-version: "3.13"', capture[:freshness_index])
        self.assertIn("if: steps.freshness.outputs.eligible == 'true'", capture)


if __name__ == "__main__":
    unittest.main()
