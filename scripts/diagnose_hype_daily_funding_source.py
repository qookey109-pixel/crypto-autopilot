from __future__ import annotations

import csv
import hashlib
import io
import json
import time
import zipfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SYMBOL = "HYPEUSDT"
DAY = "2026-06-24"
BASE = "https://data.binance.vision/data/futures/um/daily/fundingRate"
ZIP_URL = f"{BASE}/{SYMBOL}/{SYMBOL}-fundingRate-{DAY}.zip"
CHECKSUM_URL = ZIP_URL + ".CHECKSUM"
OUTPUT = "artifacts/hype-daily-funding-source-diagnostic.json"
TARGET_TIME_MS = 1782273600000  # 2026-06-24 04:00:00 UTC


def fetch(url: str, *, attempts: int = 3) -> tuple[int, bytes | None, str | None]:
    last_error: str | None = None
    for attempt in range(attempts):
        request = Request(url, headers={"Accept": "*/*", "User-Agent": "qookey-hype-funding-diagnostic/0.1"})
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310 - explicit Binance Vision URL
                return int(response.status), response.read(), None
        except HTTPError as exc:
            if exc.code == 404:
                return 404, None, "NOT_FOUND"
            last_error = f"HTTP {exc.code}: {exc.reason}"
        except (URLError, TimeoutError) as exc:
            last_error = str(exc)
        if attempt + 1 < attempts:
            time.sleep(1.0 * (attempt + 1))
    return 0, None, last_error or "UNKNOWN_ERROR"


def main() -> int:
    zip_status, zip_bytes, zip_error = fetch(ZIP_URL)
    checksum_status, checksum_bytes, checksum_error = fetch(CHECKSUM_URL)
    payload: dict[str, object] = {
        "schema": "hype-daily-funding-source-diagnostic-v0.1",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "symbol": SYMBOL,
        "day": DAY,
        "target_time_ms": TARGET_TIME_MS,
        "zip_url": ZIP_URL,
        "checksum_url": CHECKSUM_URL,
        "zip_http_status": zip_status,
        "checksum_http_status": checksum_status,
        "zip_error": zip_error,
        "checksum_error": checksum_error,
        "diagnostic_only": True,
        "source_switch_authorized": False,
        "r2_writes_performed": False,
    }
    if zip_status == 200 and zip_bytes is not None:
        payload["zip_sha256"] = hashlib.sha256(zip_bytes).hexdigest()
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
                names = [name for name in archive.namelist() if not name.endswith("/")]
                payload["zip_members"] = names
                rows: list[list[str]] = []
                if len(names) == 1:
                    text = archive.read(names[0]).decode("utf-8-sig")
                    rows = [row for row in csv.reader(io.StringIO(text)) if row]
                payload["row_count_including_header_if_present"] = len(rows)
                target_rows = [row for row in rows if row and row[0].strip() == str(TARGET_TIME_MS)]
                payload["target_0400_row_count"] = len(target_rows)
                payload["target_0400_rows"] = target_rows[:5]
        except Exception as exc:
            payload["zip_parse_error"] = f"{type(exc).__name__}: {exc}"
    if checksum_status == 200 and checksum_bytes is not None:
        payload["checksum_text"] = checksum_bytes.decode("utf-8", errors="replace").strip()

    output = Path(OUTPUT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
