# Resource Hub Supply Chain V0.2

Status: **AUTHORIZED READ-ONLY CHANGE WATCH ON PROTECTED MAIN MERGE**

V0.2 keeps the V0.1 discovery and review boundary but adds one scheduled
operation:

- every day at `01:13 UTC` / `09:13 Asia/Taipei`;
- resolve the exact public `qookey109-pixel/ai-resource-hub` main commit;
- restore the last successful source-state artifact when available;
- compare the exact source commit;
- if the source commit is unchanged, emit `NO_CHANGE` without rebuilding
  candidates;
- if the source commit changed, rebuild the research-only candidate registry
  and compare its content fingerprint;
- never install or execute newly discovered third-party code;
- never open an integration PR automatically.

The baseline source at review time is:

`3318a49e784c9a40925f7277e12d2dd55dd79a60`

The catalog blob reviewed with that baseline is:

`2b10ee6fbbcbd49fab1b635f12d4d3a9a5e7e5c2`

## Authority

V0.2 authorizes only the scheduled read of the public Resource Hub catalog and
the creation of secret-free GitHub Actions artifacts describing whether the
catalog changed.

The following remain closed:

- automatic install;
- automatic runtime execution;
- automatic adapter creation;
- automatic pull-request creation;
- market-provider access;
- R2 access;
- holdout access;
- source switching;
- automatic strategy mutation;
- automatic model promotion;
- formal trade plans;
- real-money orders;
- live real trading.

A changed candidate is still `REVIEW_REQUIRED`. Catalog discovery does not
become integration authority.

## Website projection

The dashboard projects this schedule through
`web/data/operations-schedule.json`. That file is explicitly
`authority=false`.

The Pages workflow also gains a daily `12:43 Asia/Taipei` backstop. It builds
a business-content hash that removes build-only timestamps before comparison.
If the deployed business-content hash is unchanged, the Pages deployment is
skipped.

This does not grant ZEC V0.3 development execution or hourly Live Paper
scheduling. Both remain waiting for separate authority.
