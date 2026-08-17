# Security Policy

## Secrets

Never commit:

- `PIONEX_API_KEY`
- `PIONEX_API_SECRET`
- Cloudflare API tokens
- account credentials
- private keys

Use deployment secret stores. Repositories must contain placeholders only.

## Trading safety

V0.1 contains no private Pionex execution implementation. Any future live implementation must default to disabled and require explicit configuration plus validated safety gates.

If a credential is ever committed, revoke/rotate it immediately; deleting the file alone is not sufficient because Git history may retain it.
