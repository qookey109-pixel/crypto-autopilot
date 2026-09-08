# History Recovery V0.1

Status: EFFECTIVE_ONLY_AFTER_PROTECTED_MAIN_MERGE

## Problem and resulting behavior

Run [34188345285](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34188345285)
rejected BNXUSDT, August 2022, 15m: one gap, 288 missing bars, zero
misaligned/invalid candles. The verified archive SHA is
`a3351bdf83dad7f503fb5732c88c85253101954c47b0cdb6791a11d61b131543`.
This does not establish the cause of the source gap or the total dataset completion count.

Previously the runner repeatedly selected the first incomplete shard.
The appendix selects never-attempted incomplete shards first, then the oldest
attempt sequence with shard index as a deterministic tie-break.
A quality failure records QUALITY_REJECT and still exits 1. No failed shard
is counted as complete. Ten valid original PASS shards are still required
before the existing trainer can use the dataset.

## Exact authority and activation

Original config SHA-256:
`fc4e42b855229ecb62e12e681778080c2aa749112036a6e8b3af9e9da98b716a`
(`config/binance_usdm_detailed_history_v0_1_2.json`).

Appendix: `config/binance_usdm_history_recovery_v0_1.json`.
Its exact bytes are bound by
`research/receipts/2026-09-08-binance-usdm-history-recovery-v0-1-authority.json`.
Both documents and the implementation must be reviewed and merged to protected
main before execution. A branch or PR is not execution authority.

The existing workflow passes both appendix paths. The loader validates all
contract fields, hashes, real wall-clock expiry and the repository/main ref
before constructing an R2 client. No new workflow, cron, secret or provider is introduced.
Manual overrides inconsistent with the selected shard fail before provider access.

## Journal storage and failure semantics

Dedicated root: `training/binance_usdm/history-recovery-v0.1/`.
Each catalog SHA and appendix SHA has an independent directory. Deterministic
`attempt=NNN.json` objects bind the original config, catalog, appendix, run,
shard, previous receipt SHA and aggregate diagnostic. At most 128 attempts
are committed. A duplicate run is rejected before provider access.

The latest pointer is written only after immutable attempt publication and
SHA-verified readback. Each metadata write has a fresh whole-bucket 8 GB gate
and a real-clock check, reserving 1 MB for metadata. Loading verifies the
complete bounded receipt chain and checks the next deterministic key.
An orphan record, missing record, chain mismatch or moved pointer stops work.
No automatic deletion, reconciliation or overwriting of immutable attempts
is permitted. Recovery of interrupted state needs a separately reviewed decision.

The existing serialized concurrency group remains mandatory. This design uses
that single writer; it is not a general multi-writer compare-and-swap protocol.
Do not launch a second execution path.

Only the typed BinanceVisionEvidenceError with the exact aggregate K-line
audit schema may be journaled as QUALITY_REJECT; its symbol/interval/month must
belong to the selected shard. Checksum, provider/network, permission, headroom,
authority and unknown failures halt without advancing the attempt journal.
Successful shard publication retains original completion receipts; those
receipts are verified when selecting the next incomplete shard.

Original data, quality thresholds, catalog and completion state schemas are
preserved. Binance provenance remains separate from Pionex. No interpolation,
replacement, exclusion, source switch, holdout, partial-dataset training,
model promotion, paper activation or live trading is authorized by this appendix.

## Validation and acceptance

Local synthetic tests cover fair rotation, failures never granting completion,
duplicate runs, invalid indices, fake attempt PASS, chain tampering, orphan
writes, stale writers, blocked headroom, exact expiry, contract tampering,
non-main execution and the real CLI main's failure-to-next-shard behavior.
CLI tests compile the real main function with synthetic storage/provider
dependencies; production imports and complete regression coverage are left to CI.
No production provider/R2 call was made for these tests.

After merge, use existing scheduled run receipts to verify rotation and
preserved failure status. Code/test PASS is not dataset completion. BNXUSDT
and any other rejected partition still require a separate evidence-based
data decision. There is no reliable completion date while gaps remain.
