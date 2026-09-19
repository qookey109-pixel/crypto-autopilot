# Operator Status Resolver V0.1

Status date: 2026-09-19

Status: **OFFLINE READ-ONLY STATUS PROJECTION**

## Purpose

Complete the small read-only path prepared by Operator Messaging V0.1:

```text
exact operator text
  -> parse_operator_command_request()
  -> resolve_operator_status()
  -> provider-neutral text + structured data
```

The resolver performs no network I/O, reads no secrets and executes no command.

## Source of truth

V0.1 accepts only:

`research/status/current-operations-v0-3.json`

with schema:

`qookey-current-operations-v0.3`

It deliberately preserves the source file's repository rule:

`RESOLVE_MAIN_LIVE_AT_READ_TIME`

The response therefore marks:

`snapshot_is_latest_main_claim = false`

This prevents an offline status snapshot from being presented as a live GitHub
main lookup.

## Commands

### help

Returns only the supported read-only commands:

- `help`
- `status`
- `paper_status`

It does not advertise write commands.

### status

Projects a concise subset of already-recorded current operations:

- operating mode;
- Core100 history state;
- model-quality state;
- Strategy Validation;
- replacement holdout;
- automatic promotion;
- source-switch flag;
- real-money/live-trading gates;
- live-paper status.

### paper_status

Projects the existing live-paper boundary:

- public live market data;
- live-paper simulation;
- paper-state persistence;
- private exchange API;
- replacement holdout;
- real-money orders;
- real live trading.

## Fail-closed behavior

Resolution fails if:

- the command was not already recognized;
- the request is not read-only;
- the request claims execution authority;
- the current-operations schema changes;
- repository-authority semantics drift.

This avoids silently guessing how a future status schema should be interpreted.

## Local CLI

The provider-neutral resolver is executable without Telegram, GitHub or any
other network transport:

```bash
PYTHONPATH=src python scripts/operator_status_v0_1.py status
PYTHONPATH=src python scripts/operator_status_v0_1.py paper_status
PYTHONPATH=src python scripts/operator_status_v0_1.py help --format json
```

The CLI reads only `research/status/current-operations-v0-3.json` by default.
A different offline file may be supplied with `--status-file`.

Unknown commands, missing files, malformed JSON or schema drift fail closed
with exit code `2`. The failure envelope explicitly records that no network
access, execution or state mutation occurred.

This is the intended reusable boundary for a future Telegram or other transport:
the transport only supplies command text and delivers the returned text/JSON;
it does not receive trading authority from the resolver.

## Authority

Authorized:

- deterministic offline projection of existing status fields;
- response formatting for the three read-only commands.

Not authorized:

- GitHub/provider/network access;
- Telegram runtime or delivery;
- secret access;
- command execution;
- state mutation;
- Strategy Router changes;
- Portfolio Admission;
- real-money orders;
- real live trading.
