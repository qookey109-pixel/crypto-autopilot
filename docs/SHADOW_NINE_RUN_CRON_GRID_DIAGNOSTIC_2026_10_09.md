# Qookey Shadow: nine-run theoretical UTC cron grid diagnostic (2026-10-09)

**CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER · READ-ONLY · RESEARCH ONLY · 0 USD budget.**

This is a **finite observation of existing GitHub Actions metadata** anchored in `research/receipts/2026-10-09-shadow-nine-run-cron-grid-v0-1.json`. It neither schedules an action nor retrieves provider data, changes model thresholds, writes Cloudflare resources, or grants trading authority. Reviewed `main` before this work: `36de16ee68a0be323e4d2b61716cdf2c1458ed32`; re-resolve current `main` before future work.

## Verified sources and exact boundary

- Governing workflow `.github/workflows/prospective-shadow-collection-v0-1.yml` and versioned `config/prospective_shadow_collection_execution_v0_1.json` both declare `17 */4 * * *` UTC, giving **six theoretical triggers daily** at 00:17, 04:17, 08:17, 12:17, 16:17, 20:17.
- The nine **previously executed natural runs** are: `37510931727`, `37548642486`, `37579330430`, `37644930944`, `37688505983`, `37735861279`, `37802372751`, `37846141319`, `37892197952`. Their `event=schedule`, successful conclusion, main SHA, attempt 1 and `created_at` values were reviewed from GitHub run metadata. This is *not* evidence of the nominal cron slot used to trigger each individual run.
- The original normalized artifacts for these runs and their ZIP SHA-256, embedded provenance, single-run report validity and eight adjacent pair consistencies were independently validated by GitHub-only [read-only Action #37895797841](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/37895797841) from [temporary PR #790](https://github.com/qookey109-pixel/crypto-autopilot/pull/790), **closed unmerged**. This is **9 / 21 distinct context observations** with 8,604 identical overlapping candles, five >6h *capture* gaps (372, 571, 527, 571, 529 minutes) and overall `REVIEW_REQUIRED`. Historical third-batch and two-batch snapshots remain separately valid subsets.

## What reference-grid comparison shows

- First GitHub Actions `created_at`: **2026-10-06T18:23:26Z**. Last `created_at`: **2026-10-09T06:10:49Z**.
- **15 theoretical cron time points strictly between those two timestamps.** These are reference coordinates only. They cannot be counted as actual dispatched, missed or failed runs, nor is `15 - 9` a verified missing-run count.
- Adjacent `created_at` differences in whole minutes: **325, 372, 571, 344, 527, 571, 342, 529**; **five are over six hours**, consistent in count with the separate artifact capture-gap audit. The intervals measured here use **GitHub run creation** times, *not* the capture timestamps inside artifacts.
- The difference between each run creation time and the nearest earlier theoretical UTC cron point ranges **61–212 minutes**. This is a *clock-grid offset only*, **not authenticated GitHub scheduling queue latency or delayed execution**. The actual intended cron trigger slot corresponding to each run is unknown.

The pure `shadow_cron_grid_diagnostic` helper validates exact frozen run IDs/created times/main SHAs, reviewed nine-archive audit identity, exact versioned cron and all false privilege/cause fields, before projecting any grid number. It does not assign a run to a slot. Missing or altered receipt, source timestamp, cron, attempts, source SHA or falsified authority gates **fails closed**; the website retains only earlier verified data and omits grid claims. Python unit tests and Playwright phone/desktop checks exercise this behavior.

## Root-cause finding and next decision

**UNKNOWN:** Available GitHub Action `created_at` plus the report contents do not supply a per-run authenticated `original_nominal_cron_slot` or a separate known schedule delivery timestamp. We cannot distinguish **GitHub trigger delay**, **undelivered trigger**, **workflow-level failure**, and **collector failure** for any one nominal slot on this evidence alone. We have evidence that nine observed runs successfully uploaded their existing reports, *not* that every intended trigger generated a run.

Do not manually backfill, rerun consumed authorizations, infer results of unobserved slots, change `cron`, add external requests, alter storage, train, promote, or authorize Cloud Paper/trading. A **separately reviewed prospective evidence-contract successor** could add safe, normalized dispatch/source event provenance for future natural runs if technically available; this document alone **does not authorize** changing collection scope or schedule. Keep `Core100 REJECT`, `REGIME_UNAVAILABLE`, `Cloud Paper NOT_WIRED / NOT_RUN / NOT_CONFIGURED` and no live money unchanged.
