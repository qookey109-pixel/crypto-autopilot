"""Fail-closed audit-only GitHub workflow contract (no permanent collector)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/shadow-archive-original-zip-audit-20261025.yml"


def test_shadow_archive_workflow_is_read_only_pr_only():
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "on:\n  pull_request:" in content
    assert "  schedule:" not in content
    assert "  workflow_dispatch:" not in content
    assert "permissions:\n  contents: read\n  actions: read" in content
    assert "40162915838" in content
    assert "12586364157" in content
    assert "sha256:191fa626fbddd7f4a2a639618157605ab382a343936584fa2755ec2f6c08f03d" in content
    assert "upload-artifact" not in content
    assert "cloudflare" not in content.lower()
    assert "pionex" not in content.lower()
    assert "secrets." not in content.lower()
    assert "workflow_run" not in content
