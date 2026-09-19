# Telegram MCP Evaluation V0.1

Status date: 2026-09-19

Status: **EVALUATED / NOT SELECTED AS DEFAULT OPERATOR TRANSPORT**

## Candidate

Registry capability: `telegram_mcp`

Reviewed upstream:

`chigwell/telegram-mcp@c95e136f5f852f4ce6f400dc03d0d9f6ef0b4e42`

License: Apache-2.0.

## Verified capability

The pinned project is a full Telethon-based Telegram **user-account** MCP
server. It exposes more than 80 tools across messages, chats/groups, contacts,
media, folders, profile/privacy, events and administrative operations.

It can read messages, but it can also send/edit/delete/forward messages, create
or alter groups, manage admins/bans, modify contacts/profile/settings, upload
files and perform other account mutations.

Runtime requires:

- Telegram API ID;
- Telegram API hash;
- a Telegram session string or session file.

Those credentials provide access to a Telegram user session and must be treated
as high-value secrets.

## Tool-surface restriction is useful but not a session sandbox

The upstream supports:

`TELEGRAM_EXPOSED_TOOLS=read-only`

and narrower variants such as:

`read-only+send_message,reply_to_message`

This is a meaningful MCP exposure control.

However, the upstream documentation explicitly notes that it **does not reduce
the authority of the underlying Telegram session inside the server process**.
It only controls which tools are registered to the MCP client.

For Crypto Autopilot, that distinction is decisive: a broad personal-account
session is substantially more authority than is needed to deliver trading
reports or receive a small command vocabulary.

## Local-data and third-party boundaries

The candidate may persist account-related local state such as aliases, incoming
event feeds and transcript caches. The transcript cache can contain personal
chat text in plaintext on disk, albeit with restrictive file permissions.

Optional Groq voice transcription downloads Telegram media and uploads it to a
third-party service using a separate API key.

These capabilities are unnecessary for the project's planned operator channel.

## Fit for Crypto Autopilot

The project needs a much narrower transport:

- send status/report notifications;
- optionally receive explicit bounded commands;
- identify a fixed allowed chat/user;
- never expose arbitrary Telegram account administration;
- never turn chat text directly into trade authority.

For that use case, a dedicated Telegram Bot transport is the preferred
architecture over this full user-session MCP.

A future bot adapter should default to:

- dedicated bot credential;
- explicit allowed chat/user IDs;
- small command allowlist;
- read-only project status queries plus notification delivery;
- command-to-project action mapping through existing authority gates;
- no free-form command that can directly place a real-money order;
- secret redaction and no token/session in Git/log/artifacts.

## Command authority

Telegram is only a transport.

A message such as `status`, `pause paper`, or a future bounded operator
command may request an action, but it does not bypass repository governance,
risk gates, holdout/training/model-promotion locks or real-money authority.

Untrusted incoming chat content must never be executed as shell/code or treated
as a policy/configuration override.

## Decision

**EVALUATED / NOT SELECTED AS DEFAULT OPERATOR TRANSPORT**

The Telethon MCP remains a reference candidate for workflows that genuinely
need full user-account chat access.

For Crypto Autopilot's notification/control need, prefer a dedicated Telegram
Bot integration with a materially smaller privilege surface.

No Telegram runtime is enabled by this evaluation.

Evaluation receipt:

`research/receipts/2026-09-19-telegram-mcp-evaluation-v0-1.json`

## Authority

This evaluation grants no Telegram API credential access, session generation,
account login, message sending, incoming-feed monitoring, Groq transcription,
remote HTTP exposure, bot token use, automatic command execution, strategy
authority, Portfolio Admission, real-money orders or real live trading.
