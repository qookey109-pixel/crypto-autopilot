# Research collection V0.3 — clock guard preparation

This default-disabled successor uses the V0.6 monotonic-in-call shared writer
guard via a prepared R2 admission bridge. Existing V0.2 collection and its
workflows remain unchanged. CI uses in-memory SQLite and synthetic source/R2
clients to test disabled behavior, normal publication and a backward clock step
after the shared reservation commits.

This code grants no external access or activation authority. Live account
coverage, provider budgets, D1 costs, time across calls, credentials and actual
all-writer migration remain unproven. The bridge is preparation only and does not
establish that every caller uses it.
