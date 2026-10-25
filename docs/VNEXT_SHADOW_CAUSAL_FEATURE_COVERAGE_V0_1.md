# VNext Shadow causal feature-coverage review V0.1

**Status:** PREPARED_RESEARCH_ONLY / CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER / 0 USD / PAPER-LIVE-PAPER ONLY. Pure normalized-artifact validation; no network, GitHub artifact download, provider request, R2/D1, persistence write, training, holdout, strategy routing or trading. No additional execution authority is created by this module or by its tests.

## Why this is a new additive module

The existing `prospective_shadow_continuity_v0_1.inspect_shadow_batch_continuity` validates caller-supplied original normalized reports for run identity *shape*, inline hashes, closed 60M candles, replay boundaries and across-run candle overlaps. It does **not** authenticate the original GitHub ZIP archive or full GitHub run metadata; independent original-ZIP audit remains essential. Existing receipts are frozen and unchanged.

`shadow_feature_coverage_v0_1.inspect_shadow_feature_coverage` now calls that validator first, then measures which named existing technical, market-structure, pattern and radar fields have an attested source bar and available-at timestamp. The output is an evidence **coverage diagnostic**, not a detector, synthetic strategy, ranked candidate, profitable-edge proof or production feature store.

### Strict causal review

- Snapshot family timestamps must be finite nonnegative integer milliseconds; when present, `available_at_ms` cannot predate the referenced **closed** 60M bar or be later than the batch capture time. The feature source `bar_time_ms` (or `observed_at_ms` for radar) must match the last closed candle's start exactly. A mismatch, premature/future availability, invalid numeric feature value, revised overlap, forged record hash or authority drift fails closed.
- A family missing either the source-bar identity or availability time is `unattested_time`, not ready just because it contains a number. Present `null` is `explicit_null`; absent key is `missing`; recorded 0, `False` or `NONE` is a valid observed value, **not** evidence of a positive event. Coverage percentage remains null when the sample includes untrusted timestamps or missing keys; a fully timestamped explicit-null field can have a measured 0 fraction without pretending an unknown is zero.
- `market_snapshot_rows` counts repeated captures, and `closed_60m_input_rows_including_overlap` explicitly includes repeated historical candles. Distinct 60M (symbol, candle start) identities are counted separately; equal-source candles are already checked by the existing cross-batch validator.
- `15M` and `4H` timeframes are explicitly `NOT_COLLECTED_IN_THIS_REPORT`. They are never inferred from 60M snapshots. Macro context, independent provider truth, fee/funding/slippage and return/candidate outcomes remain unavailable until separate admissible evidence exists.
- Historical Shadow reports are collection-only; they did not select signals or evaluate outcomes. No candidate reranking, production strategy qualification, model promotion, paper submission, threshold/source switch, holdout or real-money/live-trading path is opened.

## Additional fail-closed type guard (2026-10-25 review)

A second code review found that a generic nonempty string or boolean could previously be counted as an available numeric observation even when the source field was `ema20`, `atr14` or Radar relative volume. **That is not admissible feature coverage.** The diagnostic now enforces the specific collector output schema: finite non-boolean numeric values for indicator/price/volume/imbalance fields; known strict categorical states for structure/pattern outputs; nonnegative relative volume and bounded liquidation imbalance. A valid `0`, `NONE`, or valid neutral state remains an observed value, not evidence of a positive trading signal. Tests explicitly mutate hash-valid synthetic reports to strings, booleans, unsupported states, out-of-range values and extreme integers, all of which must fail closed. This is an engineering validation hardening; actual external ZIPs still have not been re-audited.

## Engineering acceptance evidence versus actual research

Tests in `tests/test_prospective_shadow_continuity_v0_1.py` use **synthetic fixtures only**. They assert complete timestamped fields, explicit-null and absent fields, missing lineage, premature/future timestamps, source-bar mismatch, invalid values, tampered authority and de-duplication of overlapping candle identities. Passing CI proves the **code contract**, not empirical feature coverage or live market validity.

The last independently audited **real** Shadow source subset remains 16 original GitHub ZIPs / 21 target context observations, 15,604 matching overlapping 60M candle instances, nine capture gaps > 6 hours, source lag <= 55 minutes, `REVIEW_REQUIRED / INSUFFICIENT`, as authenticated at [#38117712031](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/38117712031) on 2026-10-11. Do not silently promote subsequent successful collectors into this count.

Two newer natural collectors were observed by metadata on reviewed `main=944895170f80af21e8f9b544ec42b279c45c0d6e`, not independently ZIP-audited in this task:

| Run | Natural time UTC | Artifact id | Reported ZIP SHA-256 | Evidence status |
| --- | --- | --- | --- | --- |
| [#40138750452](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40138750452) | 2026-10-24 22:29:05 | 12577963902 | `5d95ffb20d2c4000862eea0515a8237a517830e7a4439e91d6dd0c77be8ea13b` | Metadata only |
| [#40162915838](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40162915838) | 2026-10-25 04:43:22 | 12586364157 | `191fa626fbddd7f4a2a639618157605ab382a343936584fa2755ec2f6c08f03d` | Metadata only |

A future *separately reviewed* GitHub-only original-archive read-only audit may reuse this pure validator with already existing artifacts and explicit run/attempt/source/artifact identity. That audit must compare original ZIP SHA-256 with trusted GitHub metadata, validate bytes inside, check sources and point-in-time feature availability and only then update an append-only receipt/dashboard projection. Do not dispatch a new collector, rerun consumed one-shot jobs or store raw provider histories to perform this review.

## Distinct operational tracks as of 2026-10-25

- New natural [Maintenance #40165410002](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40165410002) inspect **success**, propose **success**, followed by [draft PR #808](https://github.com/qookey109-pixel/crypto-autopilot/pull/808) at head `dccc4db33e7de72db9054d80515755e6bc964ef2`; head checks are `action_required` / **UNKNOWN**, not successful. The earlier stale #803 is CLOSED_UNMERGED. Healthy maintenance delivery does not fix Core100.
- Latest observed [Health #40165377547](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40165377547) remains failed, distinct from successful Shadow collector and Maintenance job.
- VNext Dashboard [PR #807](https://github.com/qookey109-pixel/crypto-autopilot/pull/807) has successful exact-head CI plus 64/64 desktop/mobile PR build browser checks; it is **OPEN_UNMERGED** as of this review. Do not count that as deployment of its changes. Existing main [Pages #40167566635](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40167566635) has independent build/deploy/production-browser success.
- Production PAPER remains `NOT_WIRED / NOT_RUN / NOT_CONFIGURED`; registry empty, Core100 `REJECT`; planned 10,000 USD genesis is **not** confirmed initialized equity. Incomplete shared Cloudflare writer admission, D1 authority/provisioning and account costs/headroom block controlled production activation. Spent Billing/Usage/bootstrap authorities do not repeat.

## Next decision

Treat this as an **additive pure research engineering PR**, not a request to merge, dispatch, launch or change provider authority. Obtain GitHub cloud tests for both Python versions, confirm the exact PR head/base and existing freezes, and defer publishing real coverage percentages until original production ZIPs have been separately authenticated. In parallel, review #807 for authorized main merge and complete actual production Pages desktop/mobile hash acceptance; review #808's action_required separately rather than treating it as passed.
