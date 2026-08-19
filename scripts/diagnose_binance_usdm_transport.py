from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"


def main() -> int:
    status: int | None = None
    raw = b""
    error_type: str | None = None
    try:
        request = Request(URL, headers={"User-Agent": "qookey-binance-transport-matrix/0.1"})
        with urlopen(request, timeout=20.0) as response:  # noqa: S310
            status = int(getattr(response, "status", 200))
            raw = response.read(8 * 1024 * 1024 + 1)
    except HTTPError as exc:
        status = int(exc.code)
        error_type = "HTTPError"
        raw = exc.read(4096)
    except (URLError, TimeoutError) as exc:
        error_type = type(exc).__name__

    json_ok = False
    symbols_array = False
    symbol_count: int | None = None
    if raw:
        try:
            payload = json.loads(raw.decode("utf-8"))
            json_ok = isinstance(payload, dict)
            if isinstance(payload, dict) and isinstance(payload.get("symbols"), list):
                symbols_array = True
                symbol_count = len(payload["symbols"])
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass

    result = {
        "transport_status": "PASS" if status == 200 and json_ok and symbols_array else "BLOCKED",
        "upstream_url": URL,
        "runner_os": os.getenv("RUNNER_OS"),
        "runner_arch": os.getenv("RUNNER_ARCH"),
        "http_status": status,
        "error_type": error_type,
        "json_ok": json_ok,
        "symbols_array": symbols_array,
        "symbol_count": symbol_count,
        "increment_values_emitted": False,
        "r2_client_constructed": False,
        "r2_writes_performed": False,
        "holdout_candles_accessed": False,
        "source_switch_authorized": False,
        "live_trading_authorized": False,
    }
    output = Path(os.environ.get("DIAGNOSTIC_OUTPUT", "artifacts/binance-transport.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
