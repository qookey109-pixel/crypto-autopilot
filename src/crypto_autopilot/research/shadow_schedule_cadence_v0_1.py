"""Fail-closed, pure arrival-time review for bounded Shadow GitHub Actions runs.

This reviews only caller-supplied GitHub run metadata. GitHub does not provide
the original nominal cron slot in these fields: preceding cron windows are
*arrival buckets*, not authenticated schedule-trigger attribution. This code
does no network, provider, GitHub, storage, holdout, training or trading work.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta

CRON_UTC = "17 */4 * * *"
_WORKFLOW = ".github/workflows/prospective-shadow-collection-v0-1.yml"
_WORKFLOW_NAME = "Prospective Shadow Collection V0.1"
_WORKFLOW_ID = 376238582
_INTERVAL = timedelta(hours=4)
_MAX_RUNS = 100
_MAX_WINDOWS = 180
_MAX_SHA_LENGTH = 40


class ShadowCadenceReviewRequired(ValueError):
    """Incomplete, unexpected or unsafe metadata for cadence diagnosis."""


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise ShadowCadenceReviewRequired(detail)


def _timestamp(value: object) -> datetime:
    _require(isinstance(value, str), "TIMESTAMP_TYPE")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError) as exc:
        raise ShadowCadenceReviewRequired("TIMESTAMP_UTC_FORMAT") from exc
    return parsed.replace(tzinfo=UTC)


def _utc_label(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _candidate_arrival_bucket(created: datetime) -> datetime:
    """Nearest prior UTC :17 four-hour cron window; NOT a proven trigger time."""
    candidate = created.replace(
        hour=(created.hour // 4) * 4, minute=17, second=0, microsecond=0
    )
    return candidate if candidate <= created else candidate - _INTERVAL


def inspect_shadow_run_arrival_cadence(
    runs: Sequence[Mapping[str, object]], *, cron_utc: str = CRON_UTC
) -> dict[str, object]:
    """Assess bounded nominal arrival windows without claiming missed triggers.

    Inputs must already have come from a separately reviewed GitHub API read;
    metadata is NOT authenticated by this pure function. A missing record in
    a window might mean queue delay, dropped/absent trigger, pagination,
    retention, disabled workflow, or another cause. Never backfill or rerun.
    """
    _require(cron_utc == CRON_UTC, "UNREVIEWED_CRON")
    _require(isinstance(runs, (list, tuple)), "INVALID_RUN_COLLECTION")
    _require(1 <= len(runs) <= _MAX_RUNS, "RUN_COUNT_OUT_OF_BOUNDS")
    observed: list[dict[str, object]] = []
    for item in runs:
        _require(isinstance(item, Mapping), "INVALID_RUN")
        run_id = item.get("run_id")
        _require(type(run_id) is int and run_id > 0, "INVALID_RUN_ID")
        _require(
            item.get("workflow_id") == _WORKFLOW_ID
            and item.get("workflow_path") == _WORKFLOW
            and item.get("workflow_name") == _WORKFLOW_NAME,
            "WRONG_WORKFLOW",
        )
        _require(
            item.get("event") == "schedule"
            and item.get("head_branch") == "main"
            and item.get("status") == "completed"
            and item.get("conclusion") == "success"
            and item.get("run_attempt") == 1
            and item.get("job_name") == "collect"
            and item.get("job_conclusion") == "success",
            "NOT_SUCCESSFUL_NATURAL_MAIN",
        )
        sha = item.get("head_sha")
        _require(
            isinstance(sha, str)
            and len(sha) == _MAX_SHA_LENGTH
            and all(c in "0123456789abcdef" for c in sha),
            "INVALID_SOURCE_SHA",
        )
        created = _timestamp(item.get("created_at"))
        started = _timestamp(item.get("run_started_at"))
        _require(started >= created, "RUN_STARTED_BEFORE_CREATION")
        bucket = _candidate_arrival_bucket(created)
        observed.append(
            {
                "run_id": run_id,
                "created": created,
                "started": started,
                "candidate": bucket,
                "phase_min": int((created - bucket).total_seconds() // 60),
            }
        )
    observed.sort(key=lambda r: r["created"])
    _require(
        len({r["run_id"] for r in observed}) == len(observed),
        "DUPLICATE_RUN_ID",
    )
    _require(
        len({r["created"] for r in observed}) == len(observed),
        "DUPLICATE_RUN_CREATION_TIME",
    )
    first = observed[0]["candidate"]
    last = observed[-1]["candidate"]
    window_count = int((last - first) / _INTERVAL) + 1
    _require(1 <= window_count <= _MAX_WINDOWS, "WINDOW_SPAN_OUT_OF_BOUNDS")
    candidate_windows = [
        first + i * _INTERVAL for i in range(window_count)
    ]
    occupied = {r["candidate"] for r in observed}
    no_creation_windows = [
        _utc_label(w) for w in candidate_windows if w not in occupied
    ]
    gaps = [
        {
            "from_run_id": prior["run_id"],
            "to_run_id": later["run_id"],
            "minutes": int((later["created"] - prior["created"]).total_seconds() // 60),
        }
        for prior, later in zip(observed, observed[1:])
        if later["created"] - prior["created"] > timedelta(hours=6)
    ]
    return {
        "schema": "qookey-shadow-nominal-arrival-cadence-review-v0.1",
        "status": "REVIEW_REQUIRED_UNKNOWN_CAUSE",
        "cron_utc": cron_utc,
        "evidence_scope": "CALLER_SUPPLIED_GITHUB_ACTIONS_RUN_METADATA",
        "run_metadata_independently_authenticated": False,
        "nominal_trigger_timestamp_available": False,
        "candidate_arrival_bucket_is_trigger_attribution": False,
        "actual_queue_delay_measured": False,
        "missed_trigger_count_proven": False,
        "missing_workflow_run_proven": False,
        "source_collector_failure_proven": False,
        "full_collection_continuity_proven": False,
        "github_schedule_changes_authorized": False,
        "retry_or_backfill_authorized": False,
        "execution_authority": False,
        "unique_natural_successful_runs": len(observed),
        "bounded_first_candidate_utc": _utc_label(first),
        "bounded_last_candidate_utc": _utc_label(last),
        "candidate_four_hour_windows": len(candidate_windows),
        "windows_with_created_run": len(occupied),
        "windows_without_created_run": len(no_creation_windows),
        "unoccupied_candidate_window_utc": no_creation_windows,
        "arrival_phase_minutes_minimum": min(r["phase_min"] for r in observed),
        "arrival_phase_minutes_maximum": max(r["phase_min"] for r in observed),
        "observed_interarrival_over_6h_count": len(gaps),
        "observed_interarrival_over_6h": gaps,
        "arrivals": [
            {
                "run_id": row["run_id"],
                "created_at": _utc_label(row["created"]),
                "run_started_at": _utc_label(row["started"]),
                "candidate_arrival_bucket_utc": _utc_label(row["candidate"]),
                "arrival_phase_minutes": row["phase_min"],
            }
            for row in observed
        ],
    }
