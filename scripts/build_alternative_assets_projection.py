#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.providers.pionex_alternative_assets import sha256_bytes
from crypto_autopilot.providers.pionex_alternative_assets_observability import (
    build_safe_projection,
    validate_observability_config,
)


ROOT = Path(__file__).resolve().parents[1]
CATALOG_CONFIG = ROOT / "config/pionex_alternative_assets_v0_1.json"
OBSERVABILITY_CONFIG = ROOT / "config/pionex_alternative_assets_observability_v0_2.json"
AUTHORITY = (
    ROOT
    / "research/receipts/2026-08-30-pionex-alternative-assets-observability-v0-2-authority.json"
)


def build_projection() -> dict[str, object]:
    catalog_bytes = CATALOG_CONFIG.read_bytes()
    observability_bytes = OBSERVABILITY_CONFIG.read_bytes()
    catalog = json.loads(catalog_bytes)
    observability = json.loads(observability_bytes)
    authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    if authority.get("config_sha256") != sha256_bytes(observability_bytes):
        raise RuntimeError("alternative-assets projection authority/config SHA mismatch")
    if authority.get("catalog_source_sha256") != sha256_bytes(catalog_bytes):
        raise RuntimeError("alternative-assets projection catalog-source SHA mismatch")
    validate_observability_config(observability, catalog_config_bytes=catalog_bytes)
    return build_safe_projection(
        catalog_config=catalog,
        observability_config=observability,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the non-authoritative Pionex alternative-assets website projection"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    projection = build_projection()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(projection, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": projection["status"],
                "candidate_count": projection["candidate_registry"]["total"],
                "authority": projection["authority"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
