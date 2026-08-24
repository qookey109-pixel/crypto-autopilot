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

Every run performs a fresh whole-bucket R2 inventory before fetching sources and
again before writing. The 8 GB FREE-ONLY hard stop and immutable run namespace
are mandatory. A blocked gate performs no provider fetch and no write. The
latest pointer is the only mutable object; run payloads and manifests are
immutable and SHA-bound.

This stage does not append candles to the historical Binance dataset, promote
models, open the holdout, create trade plans, trigger paper trades, or place
orders. Latest closed market simulation remains the existing Pionex paper
workflow; historical model training remains the existing weekly Binance
workflow. KOL outputs are challenger evidence for later calibration and
walk-forward evaluation only.
