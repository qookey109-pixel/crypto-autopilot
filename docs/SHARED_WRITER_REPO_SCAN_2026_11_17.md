# Shared account writer inventory — bounded repository scan

Observed 2026-11-17 Asia/Taipei using GitHub metadata and repository files only. This is a partial inventory aid, not execution authority.

The GitHub connector listed 12 accessible repositories owned by qookey109-pixel. The 11 other repositories below were inspected at these exact default-branch commits via non-truncated recursive tree listings. The scan searched filenames for standard `wrangler.toml`, `wrangler.json`, and `wrangler.jsonc`; it does not inspect all code or configuration. Only crypto-autopilot reported its code-search index as available; absence from owner-wide search is not negative evidence for the other repositories.

| Repository | Inspected commit | Standard Wrangler files |
| --- | --- | ---: |
| [texas-holdem](https://github.com/qookey109-pixel/texas-holdem/tree/3504939fbfcb38fcc04ff2fcebd55fb8d2767e57) | `3504939fbfcb38fcc04ff2fcebd55fb8d2767e57` | 1 |
| [Jet-Ski](https://github.com/qookey109-pixel/Jet-Ski/tree/3eb1eaaeba407325074c762d6d476734aaf5b525) | `3eb1eaaeba407325074c762d6d476734aaf5b525` | 0 |
| [ai-resource-hub](https://github.com/qookey109-pixel/ai-resource-hub/tree/84c2e57abbf18068a1eae74b5af64fc225443df2) | `84c2e57abbf18068a1eae74b5af64fc225443df2` | 2 |
| [virtual-guitar-studio](https://github.com/qookey109-pixel/virtual-guitar-studio/tree/159e0dc086802a28dbe21dbdf88369eef128d38f) | `159e0dc086802a28dbe21dbdf88369eef128d38f` | 0 |
| [Sudoku](https://github.com/qookey109-pixel/Sudoku/tree/46ab50f8027b34dbd2279bd69dbaf22179411885) | `46ab50f8027b34dbd2279bd69dbaf22179411885` | 0 |
| [car](https://github.com/qookey109-pixel/car/tree/1d71e974cb3fb227d152136caf6b18bab6ad7642) | `1d71e974cb3fb227d152136caf6b18bab6ad7642` | 0 |
| [IQ](https://github.com/qookey109-pixel/IQ/tree/0012bdcff224471767051a7d0ec585d222e783e6) | `0012bdcff224471767051a7d0ec585d222e783e6` | 0 |
| [NeuroFly](https://github.com/qookey109-pixel/NeuroFly/tree/33f08dafbfdca9c8f405f72f7fef433683280014) | `33f08dafbfdca9c8f405f72f7fef433683280014` | 0 |
| [knock-knock](https://github.com/qookey109-pixel/knock-knock/tree/68c1d1bebf1f51a2279210d4f219dd0df3f2f525) | `68c1d1bebf1f51a2279210d4f219dd0df3f2f525` | 0 |
| [AXIOM-Extreme-Reasoning-Game](https://github.com/qookey109-pixel/AXIOM-Extreme-Reasoning-Game/tree/76b544025423abed4571fcc0cba2a08f03b8a24b) | `76b544025423abed4571fcc0cba2a08f03b8a24b` | 0 |
| [orbit-guardians](https://github.com/qookey109-pixel/orbit-guardians/tree/c8806c340d2c13df90aa3461858e9aff29092e99) | `c8806c340d2c13df90aa3461858e9aff29092e99` | 0 |

Three located configuration files were read at those commits:

- [texas-holdem/backend/gemini-worker/wrangler.jsonc](https://github.com/qookey109-pixel/texas-holdem/blob/3504939fbfcb38fcc04ff2fcebd55fb8d2767e57/backend/gemini-worker/wrangler.jsonc): no literal `r2_buckets` or `d1_databases` declaration in the checked file.
- [ai-resource-hub/worker-clicks/wrangler.jsonc](https://github.com/qookey109-pixel/ai-resource-hub/blob/84c2e57abbf18068a1eae74b5af64fc225443df2/worker-clicks/wrangler.jsonc): no literal `r2_buckets` or `d1_databases` declaration in the checked file.
- [ai-resource-hub/worker/wrangler.jsonc](https://github.com/qookey109-pixel/ai-resource-hub/blob/84c2e57abbf18068a1eae74b5af64fc225443df2/worker/wrangler.jsonc): no literal `r2_buckets` or `d1_databases` declaration in the checked file.

These observations do **not** establish whether any running deployment, other branch, private repository, external service, REST/S3 client, dashboard-created binding, secret or administrator credential accesses R2 or D1. They do not establish account-wide cost, current headroom, or exclusive writing. All-writer coverage and namespace ownership remain UNKNOWN. Existing credentials remain unchanged; do not revoke them based on this scan.

No Cloudflare, R2, D1, provider, training, schedule or production PAPER access or configuration change was performed by this GitHub-only scan. Existing frozen evidence and consumed authorizations remain unchanged.
