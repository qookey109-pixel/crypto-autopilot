#!/usr/bin/env python3
from pathlib import Path
from crypto_autopilot.history.bnx_diagnosis import run

if __name__ == "__main__":
    raise SystemExit(run(Path(__file__).resolve().parents[1], Path("bnx-diagnosis-output/report.json")))
