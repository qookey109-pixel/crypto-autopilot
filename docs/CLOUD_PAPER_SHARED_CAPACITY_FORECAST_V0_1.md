# Cloud Paper Shared-Account Demand Forecast V0.1 — synthetic only

Reviewed against GitHub `main` at preparation: `b45a93c738a627d2a7ab478842d1ccd1bb8eea4d` (2026-10-09 Asia/Taipei). Resolve `main` again before merge.

**CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER / FREE-ONLY / 0 USD. No new runtime authority.**

## What this addition actually does

`src/crypto_autopilot/paper/shared_capacity_forecast_v0_1.py` is a pure, deterministic planning calculator on caller-supplied `WriterDemand`, `SlotDemand`, `MeterAttemptDemand` and **hypothetical** daily/rolling cap values. It creates no D1/R2 client, schedules no workflow, reads no usage, writes no files, modifies no central policies, and generates no paper or real-money order.

Its calculation follows the **existing** `cloudflare_shared_writer_budget_gate_v0_4` contract, rather than implementing a competing admission gate.

The success-slot envelope already includes its reserved shared-ledger floor (at least 2 D1 query units, 1 read row and 7 written rows). Additional rejected attempts and exact replays must not be free. The current gate may make **two D1 query attempts** for a rejected/replayed reservation (insert plus readback); the forecast reserves a conservative two per such attempt. Every such statement consumes a separate prepaid meter debit even if the query fails. The *meter/controller itself* has separate modeled D1 query/read/write/storage costs: none are refunded or netted against the success reservation. These costs are synthetic assumptions pending actual calibration.

The projection aggregates **all explicitly included writers** and shows the daily demand, multi-day R2 Class A/B/new-byte usage, D1 storage **growth only** (not total storage), meter debit count, projected retained successful reservations (if no compaction), and the exact input-cap dimensions exceeded.

## Status outcomes

| Status | Meaning |
| --- | --- |
| `BLOCKED_UNKNOWN_CAPS` | No complete finite hypothetical caps supplied. This matches the real V0.4 central policy whose caps start NULL. |
| `BLOCKED_SCENARIO_OVER_CAP` | At least one supplied cap is exceeded by the synthetic scenario. |
| `SCENARIO_WITHIN_INPUT_CAPS_NOT_AUTHORIZED` | Math stays within *only those hypothetical inputs*; this is **not** approved account headroom or trading eligibility. |

Every outcome sets `paper_activation_allowed=false`, `production_execution_authority=false`, `zero_usd_monthly_cost_proven=false`, `writer_inventory_complete_proven=false`, `d1_provisioned=false`, and `durable_prepaid_controller_implemented_and_calibrated=false`. No caller-provided cap or workload can turn these flags on.

## Synthetic illustration — explicitly **not** observed account usage

Two fixture writers contribute **three** successful reservations per day and one replay plus one rejection. This reserves **seven** D1 prepaid query-attempt debits daily (three successes plus four conservative unsuccessful queries). The test-controller assumption is one D1 query, two rows read, one row written, and 64 bytes of storage growth **per debit**, plus two D1 rows read per unsuccessful statement.

Together with the three slot resource envelopes, this synthetic daily forecast is:

- provider requests 3; R2 Class A 6; R2 Class B 3; new R2 bytes 384;
- D1 queries 17; rows read 31; rows written 28; storage growth 748 bytes;
- 31-day R2 A 186 / B 93 / new bytes 11,904; **new** D1 bytes 23,188, with 93 retained successful reservations before compaction.

The cap-equality fixture returns `SCENARIO_WITHIN_INPUT_CAPS_NOT_AUTHORIZED`; setting any daily or rolling R2 cap one unit lower returns `BLOCKED_SCENARIO_OVER_CAP`. A missing cap returns `BLOCKED_UNKNOWN_CAPS`.

The above are *illustrative assumptions, not measured Cloudflare costs, D1 `meta.rows_read`/`rows_written`, actual resource headroom or zero-spend proof*. In reality, provider and R2 retries, transient failures, other writer traffic, accumulated object storage, trigger/scan costs, retention compaction, controller concurrency, and its own control-plane funding may exceed the fixture.

## Outstanding production prerequisites

The existing [Shared Writer Budget Gate V0.4](SHARED_WRITER_BUDGET_GATE_V0_4.md), [Shared Writer Admission V0.3](SHARED_WRITER_ADMISSION_V0_3.md), and [VNext work order](VNEXT_DELIVERY_WORK_ORDER_2026_10_09.md) retain authority.

1. Complete owner-attested registered inventory for *every* current and future writer; cross-project account usage remains UNKNOWN.
2. Obtain separately authorized fresh account-wide billing/R2/D1 evidence and verify actual no-overage headroom. **Do not rerun consumed Billing/Usage audits.**
3. Calibrate per-query D1 read/write/storage/query attempt costs and bound controller self-funding, concurrency, crash/retry durability and account quota allocation.
4. Obtain separate exact authority before any D1 provision/migration/cap update, runtime binding, Cloud Paper run or schedule activation.
5. Preserve empty production registry, Core100 REJECT, market-context `REGIME_UNAVAILABLE`, source/holdout locks, and all real-money/live trading prohibitions.

This PR is an engineering preparation, **not** Cloud Paper activation or a timestamped natural-run acceptance.
