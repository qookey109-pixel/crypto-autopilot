# Research Signal Layer V0.2

Status: **ACTIVE ON MERGE / RESEARCH ONLY**.

V0.2 connects the V0.1 time-safe contracts to one bounded GitHub Actions
collector. It runs daily at `02:17 UTC`, fetches the three configured HTTPS
public URLs, stores secret-free source metadata and structured forecasts in
Cloudflare R2, and leaves the current Pionex hourly paper path unchanged.

Configured sources are the Capafy category page, the Capafy Bitcoin Cycle Radar
page, and the public `@aleabitoreddit` X profile. The collector never logs in,
uses private APIs, bypasses anti-bot controls, or treats prose as a forecast.
Only a source response containing an explicit JSON `forecasts` array can create
a `KOLForecast`; ordinary HTML is retained as metadata-only evidence.

Each enabled source must declare `parse_mode` as either
`structured_json_only` or `metadata_only`. The collector validates the full
enabled-source configuration before its first request. `metadata_only` records
response metadata and the content hash but never parses forecast entries.
`structured_json_only` requires each forecast's `published_at_ms` to be an
explicit integer and applies the existing V0.1 temporal and value checks.
If any forecast entry in a response is invalid, that source is marked
`FETCH_FAILED` and none of its forecasts are retained; collection may continue
with the other configured sources.

The collector checks capacity before fetching sources and again before publishing. Each
whole-bucket scan is limited to 32 LIST calls of up to 1,000 keys, the same scan size used
by the prepared Core100 reader. A missing size, incomplete listing or truncated page 32
stops that stage. Publishing also requires all three encoded objects to fit the existing
2,500,000-byte reservation and the bucket to have room for the full reservation under
the 8 GB hard stop. The manifest and signals keep their immutable keys. The latest
pointer is written last.

For one scheduled or manually dispatched collector run, the application can issue up to
64 LIST, 2 GET and 3 PUT calls. The collection step configures one total standard SDK
attempt. These are per-run request bounds. A bucket listing spans multiple requests,
so concurrent writers can change its contents during a scan or after it finishes.
Account-wide reservations and current billing headroom remain unverified.

The default collector sends one request to each configured HTTPS source and
does not follow redirects. A redirect is recorded as a failed source; the
collector can continue with the other configured sources. A changed endpoint
requires review of its provenance before the configuration is updated.

The separate read-only Quality V0.1 check verifies the exact
`latest -> manifest -> payload` lineage with at most three object reads. An
exact verified-run reuse reads only the latest pointer and still rechecks
freshness and upstream-run binding. Full evaluation requires the four
model/order prohibition flags to be explicitly `false`; known optional
prohibition flags may appear only as `false`; producer capability flags, when
present, must be booleans; unknown authority fields fail closed. These input
declarations do not grant the evaluator provider, R2-list, R2-write, holdout,
promotion or trading authority.

This stage does not append candles to the historical Binance dataset, promote
models, open the holdout, create trade plans, trigger paper trades, or place
orders. Latest closed market simulation remains the existing Pionex paper
workflow; historical model training remains the existing weekly Binance
workflow. KOL outputs are challenger evidence for later calibration and
walk-forward evaluation only.
