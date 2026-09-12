#!/usr/bin/env python3
from pathlib import Path

from crypto_autopilot.history.ctk_diagnosis_v0_1 import run


if __name__ == "__main__":
    raise SystemExit(
        run(
            Path(__file__).resolve().parents[1],
            Path("ctk-diagnosis-v0-1-output/report.json"),
        )
    )
