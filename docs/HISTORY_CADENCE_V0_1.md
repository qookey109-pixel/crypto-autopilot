# History Cadence V0.1

Status: proposed execution appendix, effective only after reviewed main merge.
User request: accelerate the existing six-hour history backfill on 2026-09-09.

The existing workflow moves to every two hours at minute 23 UTC, September
9–30, under config/history_cadence_v0_1.json and its SHA-bound authority
receipt. This supersedes only the original six-hour trigger. It preserves
the original dataset, recovery and BNX config bytes and receipts. The
convergence index and automatic-operations V0.2 projection show this cadence;
V0.1 automatic-operations remains unchanged historical evidence.

Runtime remains GitHub-hosted ubuntu-latest, serialized in the same concurrency
group, with cancel-in-progress false, one shard per run and a 330-minute
timeout. Download workers/retries and the existing 128-attempt recovery journal
are unchanged. Slow runs may queue; queued triggers do not count as completed
shards. GitHub delivery times are not guaranteed. This is 12 planned daily
opportunities instead of four, not a promise of threefold throughput.

The preflight verifies the config, receipt, exact base config hashes and
delivery bindings before the step that receives R2 credentials. It rejects
non-main, PR/push, local and rerun execution. Real-clock entry expiry remains
exclusive 2026-10-01T00:00:00Z. Existing runner and repair write-time gates
remain binding. No execution is authorized by this branch or test results.

FREE-ONLY remains 0 USD/month, with the existing fresh 8 GB whole-bucket
metadata headroom gates. No live usage or remaining allowance was inspected
during preparation. A denied gate remains a stop; there is no paid fallback.
More frequent runs may increase metadata requests, including after completion;
the existing COMPLETE short-circuit prevents repeated partition downloads.
The fixed cutoff and existing recovery limit are not extended.

Health V0.2 keeps its current nine-hour freshness ceiling: the single writer
can legitimately run for 5.5 hours and queue a scheduled attempt. Tightening
this to two hours would generate false stale alarms. Scheduled-only evidence
and the seven-workflow inventory remain unchanged.

All ten original shards are still required for dataset COMPLETE. BNX formal
repair still needs exact lineage/readback evidence; this cadence appendix does
not add R2 inspection permission to a monitoring agent. It changes neither
weekly training nor metadata capture, holdout, provider provenance, strategy,
model promotion, paper activation, trade plans or real-money authority.

Acceptance: original bound configs/receipts unchanged; new receipt hashes pass;
preflight rejects tampering, wrong event/ref, reruns and expiry; exactly one
history cron matches the current inventory; synthetic CI passes. Human review
and merge are required before this can affect production scheduling.
