# LIT Archive Diagnosis V0.1

Status: AUTHORIZED ONLY AFTER REVIEWED MAIN MERGE.

Run 34346196907 rejected LITUSDT, 2025-12, 15m because the official monthly
archive had 2,906 rows and one 70-bar gap. This appendix authorizes one fresh
manual GitHub Actions diagnosis against only that monthly archive and the
bounded official daily archives needed for the missing dates plus one overlap
day. It has no R2 credentials, R2 access, raw artifacts, retries, redirects,
provider fallback or repair permission.

The diagnosis requires the observed monthly SHA
`246dca9c1bcc046af274cc4d5b61fdd1fb818f243a2ae3c82a20471bdecdd160`.
Revision, archive absence, disagreement, unexpected quality state, archive
size violation or a daily request beyond five days fails closed. At most twelve
public requests and 20 MB total response data are allowed. GitHub retains only
the aggregate diagnosis, checksums and normalized candidate SHA; it never
retains candle rows.

A PASS-like candidate is `REPAIR_CANDIDATE_REQUIRES_PUBLICATION_AUTHORITY`,
not a repair. Any actual partition creation requires a new SHA-bound LIT
publication authority after this diagnosis, including exact daily hashes,
candidate hash, readback and receipt-last gates. This appendix changes no
schedule, existing history/BNX authority, provider provenance, holdout,
strategy, model, paper or trading authority. It expires at
2026-10-01T00:00:00Z.
