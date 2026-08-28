from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from crypto_autopilot.storage.ephemeral import require_ephemeral_output


class EphemeralStorageTests(unittest.TestCase):
    def test_repository_output_is_rejected_outside_github_actions(self) -> None:
        persistent_output = Path.home() / "crypto-autopilot-test-output" / "dataset.parquet"
        with self.assertRaisesRegex(RuntimeError, "persistent local generated-data"):
            require_ephemeral_output(persistent_output, github_actions=False)

    def test_system_temporary_output_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            path = Path(temporary_dir) / "dataset.parquet"
            self.assertEqual(
                require_ephemeral_output(path, github_actions=False),
                path,
            )

    def test_github_actions_workspace_is_ephemeral(self) -> None:
        path = Path("online-training/dataset.parquet")
        self.assertEqual(require_ephemeral_output(path, github_actions=True), path)


if __name__ == "__main__":
    unittest.main()
