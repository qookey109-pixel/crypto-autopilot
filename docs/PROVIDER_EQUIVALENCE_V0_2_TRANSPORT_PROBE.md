# Provider Equivalence V0.2 — Local Transport Connectivity Probe

Status: **PROTOCOL FROZEN / ONE-SHOT LOCAL PROBE AUTHORIZED / HOLDOUT FORBIDDEN**

Protocol:
`config/provider_equivalence_v0_2_transport_probe_v0_1.json`

Authorization:
`research/receipts/2026-08-19-provider-equivalence-v0-2-local-transport-probe-authority.json`

Upstream blocker:
`research/receipts/2026-08-19-provider-equivalence-v0-2-transport-blocked.json`

## Why this stage exists

The previously authorized hosted metadata-capture transport was suspended before its window began:

- GitHub Ubuntu returned Binance HTTP 451.
- GitHub macOS and Windows runners also returned HTTP 451.
- A temporary Cloudflare Worker path reached Binance as HTTP 403.
- zero metadata-capture receipts were written;
- zero R2 writes were performed;
- no holdout candles were accessed;
- the prior forward holdout was superseded unopened.

The frozen next required stage is therefore an **execution transport connectivity PASS before any
new forward holdout is frozen**.

## What is authorized

Exactly one class of evidence operation is authorized by this protocol:

- manual execution on an operator-controlled local host;
- public Pionex `GET /api/v1/common/symbols`;
- public Binance USD-M `GET /fapi/v1/exchangeInfo`;
- the same frozen M1A 15-symbol universe;
- JSON parsing, selected-symbol coverage checks, required metadata-field presence checks;
- raw response byte counts and SHA-256 hashes in the result.

The probe intentionally does **not** emit `quoteStep` or `tickSize` values. It proves transport and
contract reachability only.

## PASS criteria

One local execution is PASS only when both providers:

1. return HTTP 200;
2. return UTF-8 JSON;
3. contain every frozen selected symbol exactly once;
4. expose the required metadata field for every selected symbol.

Any HTTP 403/451, DNS/TLS error, timeout or network refusal is `BLOCKED`.
A reachable endpoint with an invalid payload/schema/symbol set is `FAIL`.

PASS, BLOCKED and FAIL are all valid outcomes. No threshold is tuned from the result.

## Safety boundary

This stage does not authorize:

- scheduled metadata capture;
- R2 client construction, writes or deletes;
- increment-value publication;
- any holdout candle request or evaluation;
- freezing a replacement holdout;
- provider source switching or splicing;
- Pionex-native relabeling;
- Trade-Kline W1 materialization;
- Historical Universe membership;
- backtest admission;
- automatic trade plans;
- real-money orders or live trading.

The existing metadata-capture CLI remains suspended.

## Operator command

From a fresh checkout of the branch/commit containing this protocol:

```bash
python -m pip install -e .
python scripts/probe_provider_equivalence_v0_2_transport.py \
  --output artifacts/provider-equivalence-v0-2-local-transport.json
```

A PASS result is only transport evidence. It must be reviewed and frozen in a separate authority
receipt before a new future metadata-capture window or holdout is declared.
