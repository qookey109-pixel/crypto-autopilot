# Research Receipts

Research receipts freeze externally observed or executed evidence. Cost estimates and budget policies live under `research/estimates/` and `config/` until their CI-backed gate is merged and reflected in `PROJECT_STATUS.md`.

For the repository-wide evidence classification and read order, see `docs/EVIDENCE_AND_DATA_INDEX_V0_1.md`.

## Retention rules

This directory is an immutable evidence store, not a cleanup queue.

- Do not rewrite, rename, move, squash, or delete receipts as routine organization work.
- Preserve PASS, FAIL, REJECT, blocked, prepared, superseded, and historical receipts.
- A newer version may supersede an older receipt operationally, but it does not erase the older evidence.
- A prepared or authority receipt must not be edited into an execution result; create a new completion / observation / report receipt instead.
- Preserve exact GitHub Actions run IDs, attempts, SHAs, artifact references, and provider provenance recorded by a receipt.
- Repository `main` and current status entrypoints determine present operations; a receipt proves its own dated event only.

For R2 cost control, see:

- `docs/R2_COST_BUDGET_V0_1.md`
- `research/estimates/2026-08-18-r2-cost-budget.json`
- `config/r2_budget_v0_1.json`

A budget estimate is not a market-data authority receipt and does not authorize live trading.
