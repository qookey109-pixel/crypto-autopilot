from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import build_dashboard_authority_snapshot as dashboard_builder
from scripts import build_research_calendar_projection as calendar_builder


def test_research_evidence_fixture_matches_fail_closed_schema_contract() -> None:
    schema = json.loads(
        Path("web/data/research-evidence.schema.json").read_text(encoding="utf-8")
    )
    fixture = json.loads(
        Path("web/data/research-evidence.json").read_text(encoding="utf-8")
    )

    assert fixture["authority"] is False
    assert fixture["mode"] == "PAPER_ONLY_READ_ONLY"
    assert fixture["projectedAtUtc"] is None
    assert fixture["positionsState"] == "NOT_READY"
    assert fixture["backtestsState"] == "NOT_AUTHORIZED"
    assert fixture["positions"] == []
    assert fixture["backtests"] == []
    assert set(schema["required"]) <= set(fixture)
    assert schema["properties"]["authority"]["const"] is False

    safety_properties = schema["properties"]["safetyBoundary"]["properties"]
    assert set(safety_properties) == set(fixture["safetyBoundary"])
    assert all(rule == {"const": False} for rule in safety_properties.values())
    assert all(value is False for value in fixture["safetyBoundary"].values())


def test_checked_in_calendar_is_derived_from_versioned_sources() -> None:
    expected = calendar_builder.build_projection(generated_at_utc="2026-08-26T00:00:00Z")
    checked_in = json.loads(
        Path("web/data/research-calendar.json").read_text(encoding="utf-8")
    )

    expected["projectionGeneratedAtUtc"] = None
    assert checked_in == expected
    assert checked_in["authority"] is False
    assert checked_in["projectionGeneratedAtUtc"] is None
    assert checked_in["safetyBoundary"]["backtestAdmissionAuthorized"] is False
    detailed = next(
        item for item in checked_in["items"] if item["id"] == "detailed-history-backfill"
    )
    current = checked_in["items"][0]
    assert current["id"] == "v0-10-metadata-window"
    assert current["status"] == "AUTHORIZED"
    strategy_loop = next(
        item for item in checked_in["items"] if item["id"] == "strategy-research-loop-v0-1"
    )
    assert strategy_loop["status"] == "PREPARED"
    assert "120" in strategy_loop["detail"]
    assert detailed["startsAtUtc"] == "2026-09-04T06:23:00Z"
    assert detailed["endsAtUtc"] == "2026-10-01T00:00:00Z"
    alternative = next(
        item
        for item in checked_in["items"]
        if item["id"] == "pionex-alternative-assets-catalog-v0-1"
    )
    assert alternative["status"] == "AUTHORIZED_METADATA_ONLY"
    assert alternative["startsAtUtc"] == "2026-09-04T02:53:00Z"
    assert alternative["endsAtUtc"] == "2026-10-01T00:00:00Z"
    assert "125" in alternative["detail"]
    paper = next(
        item
        for item in checked_in["items"]
        if item["id"] == "paper-training-resumption-v0-2"
    )
    assert paper["status"] == "WAITING_AUTHORITY"
    assert paper["startsAtUtc"] is None
    assert paper["endsAtUtc"] is None


def test_calendar_fails_closed_if_prepared_successor_gains_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = json.loads(calendar_builder.SUCCESSOR_SCHEDULE.read_text(encoding="utf-8"))
    source["current_authority"]["provider_access"] = True
    changed = tmp_path / "successor.json"
    changed.write_text(json.dumps(source), encoding="utf-8")
    monkeypatch.setattr(calendar_builder, "SUCCESSOR_SCHEDULE", changed)

    with pytest.raises(RuntimeError, match="gained runtime authority"):
        calendar_builder.build_projection(generated_at_utc="2026-08-26T00:00:00Z")


def test_calendar_fails_closed_if_strategy_research_execution_is_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = json.loads(calendar_builder.STRATEGY_RESEARCH_LOOP.read_text(encoding="utf-8"))
    source["candidate_search"]["execution_authorized"] = True
    changed = tmp_path / "strategy-research.json"
    changed.write_text(json.dumps(source), encoding="utf-8")
    monkeypatch.setattr(calendar_builder, "STRATEGY_RESEARCH_LOOP", changed)

    with pytest.raises(RuntimeError, match="execution became authorized"):
        calendar_builder.build_projection(generated_at_utc="2026-08-28T00:00:00Z")


def test_dashboard_generation_time_must_be_explicit_utc() -> None:
    assert dashboard_builder.normalize_generated_at("2026-08-26T12:34:56Z") == (
        "2026-08-26T12:34:56Z"
    )
    with pytest.raises(RuntimeError, match="must be a UTC timestamp"):
        dashboard_builder.normalize_generated_at("2026-08-26T12:34:56+08:00")
