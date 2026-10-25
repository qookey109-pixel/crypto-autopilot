# Pages publication hash propagation — 2026-10-25 cloud incident

Status: ENGINEERING MITIGATION IN PR, NOT MERGED. CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER, 0 USD/month, PAPER / LIVE-PAPER ONLY. Nothing in this incident grants new research/provider/R2/D1/trading authority.

## Observed GitHub-only evidence

GitHub `main=944895170f80af21e8f9b544ec42b279c45c0d6e` remained unchanged during the two observations below. Both workflows used a shared production concurrency group, configured with `queue: max`, `cancel-in-progress: false`, so no concurrent production workflow writer is proven by this evidence.

| Natural Pages run | GitHub observed result | Exact build hash | Cloud browser |
| --- | --- | --- | --- |
| [#40173621426](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40173621426) (from scheduled Research Signal Layer) | build+deploy PASS | `ef4c676a3b89e380ae9951c939a167559c41920b1190ca2e1312363c8e11f429` | 64/64 PASS |
| [#40174256013](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40174256013) (from scheduled Research Signal Quality) | build+deploy PASS | `6f8d7c2e3dc8e787a7b7dbbebe136d030e8c963b3a76a81e6f91a29dc6c83a80` | 63/64; desktop exact hash failed |

The failed browser-production job [#121111529329](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40174256013/job/121111529329) started the hash test at approximately 07:51:06 UTC; after the previously bounded 30-second poll, it still received the **previous** `ef4c676a...`, not the expected current `6f8d7c2e...`. This mismatch is a **real failed production acceptance result** and is preserved.

The evidence is consistent with GitHub Pages edge-cache or publication propagation lag after a successful deploy response, but does NOT identify the responsible cache, prove that the current build eventually became visible, or establish a GitHub bug. It is also not an instruction to weaken the identity gate or to regard previous content as current.

## Narrow fail-closed engineering correction

- The single deployed-content-hash Playwright test now permits **up to 120 seconds** for the exact expected 64-character SHA-256, with a per-test runtime ceiling of 150 seconds. All other browser tests retain their ordinary timeouts.
- Every observation still compares the expected exact job build digest to the returned live `data/content-hash.txt`, with query nonce and cache-control headers. **HTTP error, malformed/old/new-unexpected digest, timeout and non-transient transport errors never become PASS**. No generic fallback to `main`, a status file or `200 OK`.
- Add a Playwright negative test that repeatedly returns a well-formed but permanently stale digest; it must terminate in failure after its own short bounded poll. Maintain the existing recoverable mismatch and transient-transport tests.
- Add workflow static assertions so future changes cannot silently restore the too-short interval or remove the permanent mismatch regression.
- No workflow dispatch, extra cron, cloud storage, paid service, model training, source switch or production PAPER activation was introduced.

## Completion gate

This PR can only claim **PR build/browser + Python cloud checks** once the exact PR head passes. It cannot retrospectively relabel #40174256013 as successful or validate a GitHub Pages deployment until the change is **separately authorized for main merge** and a subsequent natural or accepted production Pages run has `build / deploy / browser-production` PASS with the expected exact published hash.

If a future 120-second probe still receives a wrong version, leave production acceptance RED, investigate publication/artifact identity and CDN behavior, and do not increase the timeout repeatedly without new evidence.
