# V0.10 Mid-window Emergency Change Template

Status: **TEMPLATE PREPARED / NOT AUTHORITY**

This document is a response template for an exceptional production-critical incident during the frozen V0.10 metadata-capture window. It does not authorize a code, runtime, secret, transport, provider, R2, or holdout change.

## Use only after normal frozen recovery is insufficient

The normal response remains: preserve the observed failure and let the next already-frozen scheduled attempt run. In particular, a failed `:17` run is not itself a reason to intervene before the normal `:47` attempt.

An emergency change proposal may be created only when there is an observed production-critical incident and waiting for the next frozen scheduled attempt is explicitly reviewed and judged insufficient.

## Mandatory evidence before an emergency PR

A future emergency authority must bind the incident ID/time/classification, exact observed failure evidence references, affected critical paths, exact pre-change `main` SHA, and the current Render deploy ID when transport is affected. It must explain why the next frozen scheduled attempt is insufficient and state the minimum necessary change, exact files allowed to change, reviewed test plan, rollback/stop condition, and post-change SHA lineage.

The change must go through a protected-main PR with `test (3.12)` and `test (3.13)` PASS plus all relevant critical path checks. If Render transport is affected, both pre-change and post-change deploy IDs must be recorded. Render Auto-Deploy must remain off; this template cannot trigger a deploy.

## Scientific invariants that emergency authority cannot change

Even an actual future emergency authority may not:

- backfill or retroactively validate an earlier missing hourly slot;
- rewrite timestamps or remove failed/blocked/stale runs from lineage;
- change frozen thresholds, window boundaries, 194 hourly slots, `:17/:47` minutes, 15-symbol scope, or 45-pair scope;
- bypass the 30-minute freshness guard;
- raise or bypass the 8 GB FREE-ONLY R2 hard stop, delete existing evidence for headroom, or perform partial writes;
- substitute/splice providers or relabel Binance evidence as Pionex-native;
- open/read/evaluate the replacement holdout;
- run V0.11 production R2 evaluation;
- authorize source switch, W1 materialization, backtest admission, strategy changes, automatic trade plans, real-money orders, or live trading.

## Required interpretation after any future emergency intervention

A successful emergency repair can only affect future scheduled attempts after the reviewed change. It cannot turn earlier failed or missing evidence into PASS, cannot manufacture a complete historical slot, and cannot authorize downstream scientific/trading stages.

If the incident cannot be fixed without violating these invariants, preserve the failure and allow the post-window V0.11 result to fail closed.
