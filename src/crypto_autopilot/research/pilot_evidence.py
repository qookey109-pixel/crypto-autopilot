from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def aggregate_pilot_evidence(
    directory: Path,
    *,
    year: int,
    shard_count: int = 3,
) -> dict[str, Any]:
    finals: dict[int, dict[str, Any]] = {}
    planned_stop: list[dict[str, Any]] = []

    for path in sorted(directory.rglob("*.json")):
        payload = _load_json(path)
        name = path.name
        if name.startswith("final-shard-") and "-attempt-" not in name:
            shard_index = int(payload.get("shard_index", -1))
            finals[shard_index] = payload
        if name.startswith("planned-stop-shard-") and "-attempt-" not in name:
            planned_stop.append(payload)

    expected = set(range(shard_count))
    present = set(finals)
    missing = sorted(expected - present)
    failed = sorted(
        index for index, payload in finals.items() if payload.get("status") != "PASS"
    )

    status = "PASS" if not missing and not failed and present == expected else "INCOMPLETE"
    totals = {
        "work_items_total": sum(int(payload.get("work_items_total", 0)) for payload in finals.values()),
        "finalized_new": sum(int(payload.get("finalized_new", 0)) for payload in finals.values()),
        "skipped_finalized": sum(int(payload.get("skipped_finalized", 0)) for payload in finals.values()),
        "resumed_from_staged": sum(
            int(payload.get("resumed_from_staged", 0)) for payload in finals.values()
        ),
        "resumed_from_verified": sum(
            int(payload.get("resumed_from_verified", 0)) for payload in finals.values()
        ),
        "no_data": sum(int(payload.get("no_data", 0)) for payload in finals.values()),
        "pages_fetched": sum(int(payload.get("pages_fetched", 0)) for payload in finals.values()),
        "rows_fetched": sum(int(payload.get("rows_fetched", 0)) for payload in finals.values()),
    }

    return {
        "schema_version": 1,
        "status": status,
        "year": year,
        "shard_count": shard_count,
        "present_shards": sorted(present),
        "missing_shards": missing,
        "failed_shards": failed,
        "planned_stop_observed": any(
            payload.get("status") == "PLANNED_STOP" for payload in planned_stop
        ),
        "planned_stop_records": planned_stop,
        "totals": totals,
        "shards": [finals[index] for index in sorted(finals)],
    }
