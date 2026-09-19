# Operator Messaging Contract V0.1

Status date: 2026-09-19

Status: **PROVIDER-NEUTRAL OFFLINE CONTRACT ONLY**

## Purpose

Create one small message boundary before adding Telegram or any other delivery
provider.

V0.1 does two things only:

1. constructs deterministic notification envelopes;
2. recognizes three exact read-only operator requests.

It performs no network I/O and reads no secrets.

## Notification envelope

`build_operator_notification()` records:

- source;
- topic;
- title/body;
- INFO / WARNING / ERROR severity;
- caller-supplied timestamp;
- optional dedupe key;
- small scalar metadata.

Provider and destination remain null. Delivery is explicitly false.

Metadata keys containing obvious secret-bearing names such as token, secret,
password, API key or session fail closed.

## Read-only operator requests

V0.1 recognizes only:

- `help`
- `status`
- `paper_status`

A leading slash is accepted and hyphen/underscore spelling is normalized for
the exact command.

The parser does not execute the command. Every recognized request returns:

`execution_authorized = false`

A later status resolver may answer these requests from already-authorized
project state. Text such as `buy btc`, `pause`, `resume` or arguments
appended to a command remains unrecognized in V0.1.

## Why provider-neutral first

The Telegram MCP evaluation found that a full Telethon user session is much
broader than the project needs.

This contract lets a future dedicated Telegram Bot adapter remain thin:

```text
project state -> operator notification envelope -> provider adapter -> Telegram
Telegram -> exact command request -> parser -> read-only status resolver
```

The same envelope can later support another provider without moving project
authority into the transport layer.

## Authority

Authorized:

- offline notification construction;
- exact read-only command-request parsing.

Not authorized:

- Telegram Bot or user-session runtime;
- network delivery;
- secret access;
- write/mutation commands;
- automatic command execution;
- Strategy Router changes;
- Portfolio Admission;
- real-money orders;
- real live trading.
