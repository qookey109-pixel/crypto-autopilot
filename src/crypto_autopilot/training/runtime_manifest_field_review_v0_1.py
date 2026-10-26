"""Pure Core100 V0.2 runtime-manifest field-level diagnostic.

Accept only caller-provided complete manifests, never fetch or infer originals.
This diagnostic does NOT replace the governed fingerprint comparator and grants
no authority to train, access R2, or modify the baseline.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from crypto_autopilot.training.fingerprint_v0_2 import normalize_runtime_manifest


def _distribution_versions(rows: list[dict[str, str]]) -> dict[str, str]:
    return {row["name"]: row["version"] for row in rows}


def inspect_runtime_manifest_fields(
    *,
    baseline: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> dict[str, object]:
    """Return changed *field names only*, not values or source-authentication claims.

    normalize_runtime_manifest rejects missing/inconsistent evidence. Identical
    manifests here are not proof of unchanged dataset, source blobs or outputs.
    """
    original = normalize_runtime_manifest(baseline)
    current = normalize_runtime_manifest(observed)

    field_names = sorted(set(original) | set(current))
    changed_fields = [
        field for field in field_names
        if original[field] != current[field]
    ]
    changed_distributions: dict[str, list[str]] = {}
    for family in ("distributions", "install_tools"):
        before = _distribution_versions(original[family])
        after = _distribution_versions(current[family])
        changed_distributions[family] = sorted(
            name for name in before.keys() | after.keys()
            if before.get(name) != after.get(name)
        )
    return {
        "schema": "qookey-core100-runtime-manifest-field-review-v0.1",
        "status": (
            "DIFFERENCE_OBSERVED" if changed_fields else "NO_DIFFERENCE_IN_CALLER_DATA"
        ),
        "mode": "PURE_CALLER_SUPPLIED_DATA_NOT_SOURCE_AUTHENTICATED",
        "changed_top_level_fields": changed_fields,
        "changed_distribution_names": changed_distributions["distributions"],
        "changed_install_tool_names": changed_distributions["install_tools"],
        "runner_image_version_changed": original["runner_image"] != current["runner_image"],
        "complete_source_manifests_authenticated": False,
        "r2_manifest_read_performed": False,
        "runtime_changed_root_cause_proven": False,
        "governed_comparator_replaced": False,
        "model_quality_state_modified": False,
        "authority": {
            "research_diagnostic_only": True,
            "r2_access": False,
            "provider_access": False,
            "new_training": False,
            "baseline_mutation": False,
            "model_promotion": False,
            "holdout_access": False,
            "source_switch": False,
            "paper_submission": False,
            "live_trading": False,
        },
    }
