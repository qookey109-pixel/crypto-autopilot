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
it. No upload workflow or runtime authority is created here. GitHub's
[Actions settings documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
limits public-repository artifact retention to at most 90 days, so artifacts are
supplementary evidence, not a permanent account ledger. The eventual uploader
must pin its action, bound size and retention, require upload success, and
include its costs and failure semantics in the versioned execution scope.

An observed SDK invocation is not a confirmed billable provider request; this
file proves neither complete account usage, trusted caller identity, zero cost,
nor permission to activate PAPER. Failure or cancellation may prevent the file
or artifact from existing.
