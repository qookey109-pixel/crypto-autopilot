# Research Automation Health V0.2

Research Automation Health V0.2 replaces the V0.1 cron with one complete,
read-only GitHub control plane.

## Schedule

It runs every two hours at `57 */2 * * *` UTC and checks all seven current
Repository cron workflows. The monitor itself is included in the inventory, so
adding or removing a cron without updating the versioned coverage contract
fails closed.

Only `schedule` events count as health evidence. Pull-request and manual runs
are ignored when the latest automatic run is selected.

## Classifications

- `WAITING_WINDOW`: the authorized start time has not arrived.
- `STARTUP_GRACE`: the window opened recently and the first cron is still due.
- `WAITING_DEPENDENCY`: a conditional trainer is waiting for its complete data.
- `IN_PROGRESS` / `HEALTHY`: the latest automatic run is timely.
- `EXPECTED_STOP`: a bounded schedule reached its authority end.
- `STALE`, `STALE_NO_RUN`, `STALE_IN_PROGRESS` or `FAILED`: alert and fail the
  health workflow.

The result is uploaded as a secret-free GitHub Actions artifact with 90-day
retention. No provider, R2, holdout, model, trade or order authority is present.
