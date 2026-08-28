from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SKILL_DIR = ROOT / ".agents/skills/change-walkthrough"
SKILL_PATH = SKILL_DIR / "SKILL.md"


class ChangeWalkthroughSkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.content = SKILL_PATH.read_text(encoding="utf-8")
        cls.normalized = " ".join(cls.content.split())

    def test_skill_is_minimal_and_discoverable(self) -> None:
        files = tuple(path.relative_to(SKILL_DIR).as_posix() for path in SKILL_DIR.rglob("*") if path.is_file())
        self.assertEqual(files, ("SKILL.md",))
        self.assertTrue(self.content.startswith("---\nname: change-walkthrough\n"))
        self.assertIn("description:", self.content.split("---", 2)[1])

    def test_source_identity_and_local_diff_classes_are_explicit(self) -> None:
        self.assertIn("base and head SHAs", self.content)
        self.assertIn("staged, unstaged and untracked", self.content)
        self.assertIn("Recheck them before advancing", self.content)

    def test_repository_authority_and_evidence_classes_are_distinct(self) -> None:
        self.assertIn("Repository `main` remains authority", self.content)
        for label in (
            "Repository authority",
            "change claim",
            "diff evidence",
            "test evidence",
            "unknown",
        ):
            self.assertIn(label, self.normalized)

    def test_walkthrough_cannot_mutate_or_grant_authority(self) -> None:
        for boundary in (
            "do not edit files",
            "do not post comments",
            "do not rerun workflows",
            "do not request, display or store secrets",
            "do not open frozen holdout data",
        ):
            self.assertIn(boundary, self.content)
        self.assertIn("not approval, a merge decision or execution authority", self.content)

    def test_readme_records_single_action_contract_without_new_runtime(self) -> None:
        readme = ROOT.joinpath("README.md").read_text(encoding="utf-8")
        self.assertIn(".agents/skills/change-walkthrough/SKILL.md", readme)
        self.assertIn("one canonical Python domain action", readme)
        self.assertIn("does not justify a second runtime", readme)


if __name__ == "__main__":
    unittest.main()
