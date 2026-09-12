#!/usr/bin/env python3
from pathlib import Path

from crypto_autopilot.history.bnx_diagnosis_v0_3 import run


if __name__ == "__main__":
    raise SystemExit(
        run(
            Path(__file__).resolve().parents[1],
            Path("bnx-diagnosis-v0-3-output/report.json"),
        )
    )
