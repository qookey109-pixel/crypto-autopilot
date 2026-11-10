# GitHub job identity primitives V0.1

Status: **PREPARED / DISABLED / NO EXECUTION AUTHORITY**.

Extracted without functional change from draft [PR #856](https://github.com/qookey109-pixel/crypto-autopilot/pull/856). These modules are reference primitives for a later independently enforced Cloud Paper identity boundary. They do not expose a Worker route or bind credentials. Default calls make no network request.

The verifier checks a fixed issuer, RS256 signature and scoped claims using an injected key reader, policy and clock. The separate key and metadata readers have fixed endpoints, bounded responses and no redirects. The metadata comparison checks the signed IDs against run and job records. Synthetic cloud CI tests cover incorrect signatures and claims, malformed inputs, key and response failures, disabled operation and metadata mismatches.

**This is not production authentication.** The policy, clock and fetchers are supplied by the caller; the caller can lie. A signed bearer can be copied or raced. No protected claim, rate limit, all-writer budget, Cloudflare Worker compatibility, live OIDC claims, account headroom or credential isolation is proven here. Existing writers retain their existing authority and direct credentials.

Next: prepare a separately versioned finite GitHub-only diagnostic for actual OIDC claim availability and run/job correlation, with no Cloudflare, R2, D1, provider, order or training access. No token or raw response may be logged or saved. A diagnostic pass must not authorize Paper activation. Its execution requires its own reviewed scope merged on main.

CLOUD_ONLY / FREE_ONLY / PAPER-LIVE-PAPER ONLY. Holdout, source switch, promotion and real-money trading remain closed.
