from __future__ import annotations

import subprocess
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ai_worktree.sh"


class AiWorktreeScriptTests(unittest.TestCase):
    def test_script_has_valid_bash_syntax(self) -> None:
        subprocess.run(["bash", "-n", str(SCRIPT)], cwd=REPO_ROOT, check=True)

    def test_help_is_available_without_mutating_repository(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "--help"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("setup", result.stdout)
        self.assertIn("start <research|web-docs>", result.stdout)
        self.assertIn("finish <research|web-docs>", result.stdout)


if __name__ == "__main__":
    unittest.main()
