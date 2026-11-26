import hashlib
import json
import re
import unittest
from pathlib import Path

from crypto_autopilot.paper.run_coordinator_v0_1 import (
    live_paper_run_coordinator_input_from_dict,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config/live_paper_coordinator_input_registry_v0_1.json"


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


class CoordinatorInputRegistryTest(unittest.TestCase):
    def test_approved_paths_match_committed_inputs(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"), object_pairs_hook=unique_fields)
        self.assertEqual(set(registry), {"schema", "workflow_id", "approved_inputs"})
        self.assertEqual(registry["schema"], "qookey-live-paper-coordinator-input-registry-v0.1")
        self.assertEqual(registry["workflow_id"], "361536775")
        entries = registry["approved_inputs"]
        self.assertIsInstance(entries, list)
        self.assertLessEqual(len(entries), 64)
        seen = set()
        for entry in entries:
            with self.subTest(entry=entry):
                self.assertEqual(set(entry), {"input_path", "blob_sha"})
                path = entry["input_path"]
                self.assertTrue(re.fullmatch(
                    r"research/inputs/live-paper/(?:[A-Za-z0-9_-][A-Za-z0-9._-]*/)*"
                    r"[A-Za-z0-9_-][A-Za-z0-9._-]*\.json", path
                ))
                self.assertLessEqual(len(path), 384)
                self.assertLessEqual(len(path.split("/")), 12)
                self.assertNotIn(path, seen)
                seen.add(path)
                source = ROOT / path
                self.assertEqual(source.resolve(strict=True), source)
                self.assertTrue(source.is_file())
                data = source.read_bytes()
                header = f"blob {len(data)}\0".encode("ascii")
                self.assertEqual(hashlib.sha1(header + data, usedforsecurity=False).hexdigest(), entry["blob_sha"])
                live_paper_run_coordinator_input_from_dict(json.loads(data, object_pairs_hook=unique_fields))
