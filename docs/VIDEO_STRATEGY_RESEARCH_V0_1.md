# Video Strategy Research V0.1

Status: `PREPARED_RESEARCH_ONLY`

## Goal

Turn a trading video or YouTube source into a grounded, reviewable strategy candidate without allowing the source video to mutate production strategy, access holdout data, promote a model, or authorize trading.

## Local NotebookLM MCP

Reference implementation for V0.1: `euisuk-chung/notebooklm-mcp` (`notebooklm-mcp-cli`). It exposes NotebookLM through local MCP tools such as `notebook_create`, `source_add`, and `notebook_query`.

Authentication must remain local to the operator machine. Never commit NotebookLM cookies, browser profiles, session tokens, or Google credentials to this repository.

Typical local preparation:

```bash
uv tool install notebooklm-mcp-cli
nlm login
nlm login --check
nlm setup add json
```

Use the generated MCP configuration in the chosen MCP-capable client. The server command is `notebooklm-mcp` over stdio.

## Research flow

1. Create a notebook for the source video.
2. Add the YouTube URL or local video through the NotebookLM MCP.
3. Query NotebookLM with `research/prompts/notebooklm_video_strategy_analysis_v0_1.md`.
4. Save the returned JSON as a local analysis file.
5. Materialize a fail-closed candidate:

```bash
python scripts/build_video_strategy_candidate_v0_1.py \
  --input /path/to/notebooklm-analysis.json \
  --source 'https://www.youtube.com/watch?v=...' \
  --output /tmp/video-strategy-candidate.json
```

The result remains `UNVERIFIED_RESEARCH_CANDIDATE`. Claimed performance is explicitly unverified.

## Next gate

The candidate may be proposed to the existing `strategy_research_loop_v0_1` for deterministic research. Current repository authority does **not** authorize production-dataset backtest admission from this video intake alone. Separate reviewed authority is required before using production Core100 data for candidate evaluation.

## Hard boundaries

- No repository storage of NotebookLM authentication material.
- No automatic production strategy mutation.
- No replacement holdout access.
- No source switch.
- No synthetic/interpolated candles.
- No automatic model promotion.
- No formal trade-plan authority.
- No real-money orders.
- No live trading.

## Why MCP instead of a NotebookLM API dependency

The NotebookLM integration is intentionally outside the Python package dependency graph. The repository consumes only a strict grounded-analysis contract. If an unofficial NotebookLM MCP implementation changes or breaks, the strategy research core remains reproducible and unaffected.
