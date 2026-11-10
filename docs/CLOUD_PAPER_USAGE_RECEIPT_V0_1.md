# Cloud Paper runner usage receipt V0.1

This prepared exporter accepts only the exact V0.1 observation vocabulary and
bounded counters. A successful observation must match the digest and slot of
the V0.3 immutable Paper report supplied in memory. Failure observations retain
only the redacted partial counters and do not claim a completed report. Raw
reports, account information, credentials and arbitrary fields are not exported.

In an existing trusted GitHub-hosted Linux runner directory the exporter fsyncs
a temporary file, publishes the fixed final name with an exclusive hard link,
then removes the temporary name. It never overwrites an existing file or
symlink. A failure after publication is ambiguous; retain and inspect the
existing file instead of automatically retrying. A crash before publication can
leave only a temporary file, which is not a valid receipt.

The file exists only on the runner until a separately authorized workflow uploads
it. No production upload workflow or runtime authority is created here. GitHub's
[Actions settings documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
limits public-repository artifact retention to at most 90 days, so artifacts are
supplementary evidence, not a permanent account ledger. The eventual uploader
must pin its action, bound size and retention, require upload success, and
include its costs and failure semantics in the versioned execution scope.

An observed SDK invocation is not a confirmed billable provider request; this
file proves neither complete account usage, trusted caller identity, zero cost,
nor permission to activate PAPER. Failure or cancellation may prevent the file
or artifact from existing.

## Synthetic cloud CI evidence

The ordinary GitHub CI job runs a socket-blocked synthetic V0.5 PAPER fixture,
then an ambiguous D1-response fixture. It exports two redacted receipts and a
manifest labeled `SYNTHETIC_CI_ONLY`, uploads them as a seven-day artifact,
downloads the same artifact and compares the three files and their SHA-256
digests. Its source SHA is the GitHub Actions checkout SHA, which can be a
pull-request merge commit; it is not an independently attested production run.
No real provider, R2 or D1 operation is authorized or performed by the fixture.
Artifact readback demonstrates the test channel only; actual production
persistence, budgets and activation remain separate and unproven.
