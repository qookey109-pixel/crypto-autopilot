#!/usr/bin/env python3
from pathlib import Path

from crypto_autopilot.history.ctk_diagnosis_v0_2 import run


if __name__ == "__main__":
    raise SystemExit(
        run(
            Path(__file__).resolve().parents[1],
            Path("ctk-diagnosis-v0-2-output/report.json"),
        )
    )
