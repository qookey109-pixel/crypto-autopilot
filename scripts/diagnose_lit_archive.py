#!/usr/bin/env python3
from pathlib import Path

from crypto_autopilot.history.lit_diagnosis import run


if __name__ == "__main__":
    raise SystemExit(run(Path(__file__).resolve().parents[1], Path("lit-diagnosis-output/report.json")))
