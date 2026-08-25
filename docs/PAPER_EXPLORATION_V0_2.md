# Paper Exploration V0.2

Status: `PREPARED_LOCAL_REPLAY_ONLY`.

The governed Paper Broker V0.1 remains capped at three new portfolio trades per
UTC day and one open position at a time. V0.2 adds a separate high-sample
research replay that can retain up to 12 independent samples per UTC day and
two per symbol. Each sample uses 0.25% reference risk, explicit taker fees and
slippage, and the existing 3x leverage ceiling.

Samples may overlap because they are evaluated independently. Their monetary
results must never be compounded into a portfolio equity curve or presented as
the governed Paper Broker's performance. The output reports sample count, win
rate, average R, costs and rejection reasons for training diagnostics only.

V0.2 performs no provider or R2 access and has no schedule. It cannot promote a
model, create a formal trade plan, automate Pionex Demo, place a real-money
order or enable live trading. Activation from an online workflow requires a
separate versioned authority after the current frozen window.
