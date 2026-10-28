# Seal-guarded Cloud Paper composition V0.1

This disabled-by-default successor wraps a prepared Cloud Paper composition.
It verifies each existing result seal against its request, immutable step, tick,
run and sequence before the frozen loop consumes it. No frozen file is changed.

Each found seal adds two metered reads (step and tick). The same R2 per-run guard
and existing admitted envelope apply; exhausted or stale evidence stops before
a further external call. The 128-read bound is not a claim that every possible
namespace fits: measure the actual workload before activation. Full central
reservations remain retained on failure.

This is synthetic engineering readiness only. It does not create an entrypoint,
change a workflow, establish all-writer coverage, verify Cloudflare usage or
grant provider, R2, D1, recovery, schedule, promotion or trading authority.
Separate versioned authorization, fresh account evidence and immutable namespace
ownership are required before production use. Prepaid historical recovery remains
blocked pending its own separately admitted successor.
