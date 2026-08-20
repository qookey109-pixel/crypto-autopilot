from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

RETIRED = (
    "historical-backfill-pilot.yml",
    "diagnose-v0-2-self-hosted-mac-binance-transport.yml",
    "binance-2025-r2-pilot.yml",
    "binance-vision-live-proof.yml",
    "binance-vision-r2-proof.yml",
    "binance-funding-r2-v0-2-preflight.yml",
    "binance-funding-r2-v0-2-materialize.yml",
    "m1b-m1a-dataset-upload.yml",
    "m1b-r2-roundtrip.yml",
)

FORBIDDEN_EXECUTION_TOKENS = (
    "${{ secrets.",
    "runs-on: [self-hosted",
    "scripts/run_historical_backfill_pilot.py",
    "scripts/materialize_binance_2025_r2_pilot.py",
    "scripts/prove_binance_vision_source.py",
    "scripts/prove_binance_vision_r2.py",
    "scripts/preflight_binance_funding_r2_v0_2.py",
    "scripts/materialize_binance_funding_r2_v0_2.py",
    "scripts/upload_m1a_dataset_to_r2.py",
    "scripts/r2_roundtrip_proof.py",
    "urllib.request.urlopen",
)


def test_retired_historical_execution_workflows_are_validation_only() -> None:
    for name in RETIRED:
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        lines = text.splitlines()
        assert "RETIRED" in text, name
        assert "RETIRED_NO_EXECUTION" in text, name
        assert not any(line == "  schedule:" for line in lines), name
        assert not any(line == "  push:" for line in lines), name
        assert not any(line.strip() == "workflow_dispatch:" for line in lines), name
        for token in FORBIDDEN_EXECUTION_TOKENS:
            assert token not in text, f"{name}: {token}"
        for marker in (
            "provider_requests_performed=0",
            "r2_writes_performed=false",
            "holdout_candles_accessed=false",
            "source_switch_authorized=false",
            "live_trading_authorized=false",
        ):
            assert marker in text, f"{name}: {marker}"


def test_v0_10_current_metadata_schedule_remains_active_and_unique() -> None:
    current = (WORKFLOWS / "provider-equivalence-v0-10-render-metadata-capture.yml").read_text(
        encoding="utf-8"
    )
    old = (WORKFLOWS / "provider-equivalence-v0-2-metadata-capture.yml").read_text(
        encoding="utf-8"
    )
    assert any(line == "  schedule:" for line in current.splitlines())
    assert not any(line == "  schedule:" for line in old.splitlines())
    for cron in (
        '    - cron: "17,47 * 27-31 8 *"',
        '    - cron: "17,47 * 1-3 9 *"',
        '    - cron: "17,47 0-1 4 9 *"',
    ):
        assert cron in current
