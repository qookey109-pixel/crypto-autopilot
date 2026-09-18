# Bitget MACD 30m Preregistered Validation V0.1

Status date: 2026-09-18

This document freezes the validation method **before** any new real ZECUSDT historical data access is authorized.

## Purpose

The goal is robustness, not maximum in-sample return. The existing 2,304-candidate Bitget-style MACD grid is evaluated chronologically:

- first 70% of the authorized ZECUSDT dataset: development only
- development is split into 4 non-overlapping chronological windows
- candidate selection uses development windows only
- top 24 development candidates advance
- final 30%: confirmation only
- confirmation cannot change parameters
- confirmation is repeated at 2, 5, and 10 bps slippage per side
- the project's formal replacement holdout is not accessed

Each temporal window starts from its own local slice, so MACD warm-up occurs inside that window. No pre-window candles are injected as hidden state.

## Development ordering

Candidates are ordered using only development evidence:

1. number of windows meeting the minimum trade-count requirement
2. number of profitable development windows
3. worst development-window return
4. median development-window return
5. median development-window profit factor
6. lower maximum development-window drawdown
7. total development trades

This intentionally rewards stability across regimes before raw headline return.

## Confirmation boundary

Confirmation results are descriptive evidence only. They are not allowed to:

- change MACD periods
- change stop loss
- change leverage or risk profile
- change the fluctuation approximation
- expand the candidate grid
- change the ranking rule

Any such change requires a new version and a new pre-registration before another confirmation dataset is read.

## Data and authority boundary

This PR grants no data-access authority. The runner accepts a local authorized candle JSON file only.

It performs no provider requests, R2 reads/writes, holdout access, training, source switch, model promotion, trade-plan generation, real-money orders, or live trading.

The actual real ZECUSDT historical run remains separately gated.
