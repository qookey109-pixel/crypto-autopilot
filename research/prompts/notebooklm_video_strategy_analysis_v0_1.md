# NotebookLM Video Strategy Analysis V0.1

Analyze only the provided video/source material. Do not invent missing rules, parameters, performance, or causal claims.

Return **JSON only** with this exact top-level shape:

```json
{
  "strategy_name": "string",
  "summary": "string",
  "timeframes": ["string"],
  "markets": ["string"],
  "indicators": [
    {
      "name": "string",
      "parameters": {},
      "role": "string"
    }
  ],
  "entry_rules": ["string"],
  "exit_rules": ["string"],
  "risk_rules": ["string"],
  "claimed_metrics": [
    {
      "metric": "string",
      "value": "string",
      "source_locator": "timestamp, quote locator, or source section"
    }
  ],
  "uncertainties": ["string"],
  "evidence": [
    {
      "claim": "string",
      "source_locator": "timestamp, quote locator, or source section",
      "confidence": "high|medium|low"
    }
  ]
}
```

Rules:

- Separate what the speaker explicitly states from your interpretation.
- Put ambiguous, visual-only, missing, or contradictory details in `uncertainties`.
- Do not treat claimed win rate, profit, Sharpe, drawdown, or account growth as verified performance.
- Preserve exact indicator parameters only when the source states or visibly establishes them.
- Describe entry/exit logic as deterministic rules where possible; otherwise mark it uncertain.
- Never recommend model promotion, live trading, leverage changes, or real-money execution.
- Do not use outside market knowledge unless it is another source already present in the same notebook.
