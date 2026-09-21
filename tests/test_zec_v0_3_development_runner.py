from __future__ import annotations

import json
import math
from pathlib import Path
import unittest

from crypto_autopilot.models import Candle
from crypto_autopilot.research.zec_v0_3_development_contract import (
    build_zec_v0_3_candidate_grid,
)
from crypto_autopilot.research.zec_v0_3_development_runner import (
    ZecV03CandidateFoldResult,
    ZecV03DevelopmentAuthorityError,
    ZecV03FoldMetrics,
    aggregate_15m_to_4h,
    evaluate_zec_v0_3_candidate_fold,
    rank_zec_v0_3_development_results,
    run_zec_v0_3_development_matrix,
    select_zec_v0_3_development_champion,
)
from crypto_autopilot.research.zec_v0_3_selection_policy import (
    validate_zec_v0_3_selection_policy,
)
from crypto_autopilot.research.zec_v0_3_development_execution_authority import (
    validate_zec_v0_3_development_execution_authority,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "zec_strategy_v0_3_development_matrix_v0_1.json"
SELECTION_POLICY = ROOT / "config" / "zec_strategy_v0_3_selection_policy_v0_1.json"
EXECUTION_AUTHORITY = (
    ROOT
    / "research/receipts/2026-09-21-zec-v0-3-development-one-shot-authority.json"
)
FIFTEEN_MINUTES_MS = 15 * 60 * 1000
FOUR_HOURS_MS = 4 * 60 * 60 * 1000


def _synthetic_source(bar_count: int = 5200) -> list[Candle]:
    rows: list[Candle] = []
    previous = 100.0
    for index in range(bar_count):
        close = 100.0 + index * 0.002 + 2.5 * math.sin(index / 18.0)
        high = max(previous, close) * 1.002
        low = min(previous, close) * 0.998
        rows.append(
            Candle(
                time_ms=index * FIFTEEN_MINUTES_MS,
                open=previous,
                high=high,
                low=low,
                close=close,
                volume=10.0 + index % 11,
            )
        )
        previous = close
    return rows


def _matrix_result(
    candidate_id: str,
    fold_id: str,
    *,
    return_pct: float,
    drawdown: float,
    trades: int,
) -> ZecV03CandidateFoldResult:
    metrics = ZecV03FoldMetrics(
        trade_count=trades,
        win_count=0,
        loss_count=0,
        mean_net_pnl_usd=0.0,
        return_pct=return_pct,
        max_drawdown_pct=drawdown,
        profit_factor=None,
        total_fees_usd=0.0,
        total_funding_usd=0.0,
        total_slippage_cost_usd=0.0,
        funding_status="UNAVAILABLE_NOT_FABRICATED",
    )
    return ZecV03CandidateFoldResult(
        candidate_id=candidate_id,
        fold_id=fold_id,
        start_time_ms=0,
        end_exclusive_time_ms=1,
        initial_equity_usd=10_000.0,
        final_equity_usd=10_000.0,
        trades=(),
        metrics=metrics,
    )


class ZecV03OfflineDevelopmentRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.candidates = build_zec_v0_3_candidate_grid(cls.contract)

    def test_4h_aggregation_is_canonical_and_uses_sixteen_15m_bars(self) -> None:
        source = [
            Candle(
                time_ms=index * FIFTEEN_MINUTES_MS,
                open=100.0 + index,
                high=102.0 + index,
                low=99.0 + index,
                close=101.0 + index,
                volume=1.0 + index,
            )
            for index in range(16)
        ]

        result = aggregate_15m_to_4h(source)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].time_ms, 0)
        self.assertEqual(result[0].open, 100.0)
        self.assertEqual(result[0].high, 117.0)
        self.assertEqual(result[0].low, 99.0)
        self.assertEqual(result[0].close, 116.0)
        self.assertEqual(result[0].volume, sum(1.0 + index for index in range(16)))

    def test_candidate_fold_engine_is_paper_only_and_preserves_leverage_cap(self) -> None:
        candidate = next(
            item
            for item in self.candidates
            if item.macd == "12/26/9"
            and item.trend_regime == "TREND_BASIC"
            and item.volatility_filter == "ATR_FILTER_OFF"
            and item.stop_model == "VOL_STOP_2ATR_BB_HALF"
            and item.account_risk_fraction == 0.1
        )
        source = _synthetic_source()
        fold_start = 3600 * FIFTEEN_MINUTES_MS
        fold_end = 5200 * FIFTEEN_MINUTES_MS

        result = evaluate_zec_v0_3_candidate_fold(
            candles_15m=source,
            candidate=candidate,
            fold_id="synthetic-development",
            fold_start_time_ms=fold_start,
            fold_end_exclusive_time_ms=fold_end,
            funding_points=None,
        )

        self.assertGreater(result.metrics.trade_count, 0)
        self.assertEqual(result.metrics.funding_status, "UNAVAILABLE_NOT_FABRICATED")
        self.assertTrue(result.paper_only)
        self.assertEqual(result.provider_requests_performed, 0)
        self.assertFalse(result.r2_reads_performed)
        self.assertFalse(result.r2_writes_performed)
        self.assertFalse(result.formal_holdout_accessed)
        self.assertFalse(result.live_trading_authorized)
        for trade in result.trades:
            self.assertLessEqual(trade.realized_leverage, 3.0)
            self.assertLessEqual(trade.realized_risk_usd, trade.target_risk_usd + 1e-8)
            self.assertLess(trade.stop_price, trade.entry_price)
            self.assertLess(trade.entry_time_ms, fold_end)
            self.assertLess(trade.exit_time_ms, fold_end)

    def test_interior_gap_fails_closed_before_research(self) -> None:
        source = _synthetic_source(64)
        del source[20]

        with self.assertRaisesRegex(ValueError, "strictly contiguous"):
            aggregate_15m_to_4h(source)

    def test_diagnostic_ranking_requires_complete_matrix_and_freezes_no_champion(self) -> None:
        candidates = self.candidates[:2]
        fold_ids = ("fold-a", "fold-b")
        rows = (
            _matrix_result(
                candidates[0].candidate_id,
                "fold-a",
                return_pct=1.0,
                drawdown=5.0,
                trades=12,
            ),
            _matrix_result(
                candidates[0].candidate_id,
                "fold-b",
                return_pct=0.5,
                drawdown=6.0,
                trades=10,
            ),
            _matrix_result(
                candidates[1].candidate_id,
                "fold-a",
                return_pct=0.8,
                drawdown=4.0,
                trades=20,
            ),
            _matrix_result(
                candidates[1].candidate_id,
                "fold-b",
                return_pct=0.7,
                drawdown=4.5,
                trades=18,
            ),
        )

        summaries, ranking = rank_zec_v0_3_development_results(
            candidates=candidates,
            fold_ids=fold_ids,
            results=rows,
        )

        self.assertEqual(summaries[0].candidate_id, candidates[1].candidate_id)
        self.assertEqual(ranking.diagnostic_leader_id, candidates[1].candidate_id)
        self.assertFalse(ranking.champion_frozen)
        self.assertEqual(ranking.selection_status, "DIAGNOSTIC_RANKING_ONLY")
        self.assertFalse(ranking.fresh_confirmation_accessed)
        self.assertFalse(ranking.live_trading_authorized)

        with self.assertRaisesRegex(ValueError, "must be complete"):
            rank_zec_v0_3_development_results(
                candidates=candidates,
                fold_ids=fold_ids,
                results=rows[:-1],
            )


    def test_frozen_selection_policy_rejects_isolated_peak(self) -> None:
        policy_payload = json.loads(SELECTION_POLICY.read_text(encoding="utf-8"))
        policy, policy_sha = validate_zec_v0_3_selection_policy(policy_payload)
        fold_ids = ("fold-a", "fold-b")
        rows = []
        for candidate in self.candidates:
            base = 0.5
            if candidate.candidate_id == "zec-v0-3-01":
                base = 4.0
            rows.extend(
                (
                    _matrix_result(
                        candidate.candidate_id,
                        fold_ids[0],
                        return_pct=base,
                        drawdown=5.0,
                        trades=40,
                    ),
                    _matrix_result(
                        candidate.candidate_id,
                        fold_ids[1],
                        return_pct=base,
                        drawdown=5.5,
                        trades=40,
                    ),
                )
            )

        selection = select_zec_v0_3_development_champion(
            candidates=self.candidates,
            fold_ids=fold_ids,
            results=tuple(rows),
            policy=policy,
            policy_sha256=policy_sha,
        )

        self.assertEqual(selection.status, "ISOLATED_DEVELOPMENT_PEAK_REJECTED")
        self.assertIsNone(selection.selected_candidate_id)
        self.assertFalse(selection.champion_frozen)
        self.assertFalse(selection.fresh_confirmation_accessed)
        self.assertFalse(selection.formal_holdout_accessed)
        self.assertFalse(selection.live_trading_authorized)

    def test_frozen_selection_policy_can_freeze_stable_development_champion(self) -> None:
        policy_payload = json.loads(SELECTION_POLICY.read_text(encoding="utf-8"))
        policy, policy_sha = validate_zec_v0_3_selection_policy(policy_payload)
        fold_ids = ("fold-a", "fold-b")
        rows = []
        special = {
            "zec-v0-3-01": (4.0, 5.0),
            "zec-v0-3-02": (3.4, 4.1),
            "zec-v0-3-05": (3.2, 3.8),
        }
        for candidate in self.candidates:
            fold_returns = special.get(candidate.candidate_id, (0.5, 0.6))
            rows.extend(
                (
                    _matrix_result(
                        candidate.candidate_id,
                        fold_ids[0],
                        return_pct=fold_returns[0],
                        drawdown=5.0,
                        trades=40,
                    ),
                    _matrix_result(
                        candidate.candidate_id,
                        fold_ids[1],
                        return_pct=fold_returns[1],
                        drawdown=5.5,
                        trades=40,
                    ),
                )
            )

        selection = select_zec_v0_3_development_champion(
            candidates=self.candidates,
            fold_ids=fold_ids,
            results=tuple(rows),
            policy=policy,
            policy_sha256=policy_sha,
        )

        self.assertEqual(selection.status, "DEVELOPMENT_CHAMPION_FROZEN")
        self.assertEqual(selection.selected_candidate_id, "zec-v0-3-01")
        self.assertTrue(selection.champion_frozen)
        self.assertIn("zec-v0-3-02", selection.stable_neighbor_ids)
        self.assertIn("zec-v0-3-05", selection.stable_neighbor_ids)
        self.assertGreaterEqual(len(selection.stable_neighbor_ids), 2)
        self.assertFalse(selection.fresh_confirmation_accessed)
        self.assertFalse(selection.formal_holdout_accessed)
        self.assertFalse(selection.live_trading_authorized)

    def test_selection_policy_requires_30_trades_in_every_fold(self) -> None:
        policy_payload = json.loads(SELECTION_POLICY.read_text(encoding="utf-8"))
        policy, policy_sha = validate_zec_v0_3_selection_policy(policy_payload)
        fold_ids = ("fold-a", "fold-b")
        rows = []
        for candidate in self.candidates:
            rows.extend(
                (
                    _matrix_result(
                        candidate.candidate_id,
                        fold_ids[0],
                        return_pct=2.0,
                        drawdown=4.0,
                        trades=29,
                    ),
                    _matrix_result(
                        candidate.candidate_id,
                        fold_ids[1],
                        return_pct=2.0,
                        drawdown=4.0,
                        trades=40,
                    ),
                )
            )

        selection = select_zec_v0_3_development_champion(
            candidates=self.candidates,
            fold_ids=fold_ids,
            results=tuple(rows),
            policy=policy,
            policy_sha256=policy_sha,
        )

        self.assertEqual(selection.status, "NO_ELIGIBLE_DEVELOPMENT_CANDIDATE")
        self.assertFalse(selection.champion_frozen)

    def test_repository_contract_blocks_real_development_execution(self) -> None:
        with self.assertRaisesRegex(
            ZecV03DevelopmentAuthorityError,
            "development execution is not authorized",
        ):
            run_zec_v0_3_development_matrix(
                candles_15m=(),
                contract=self.contract,
            )

    def test_separate_merged_authority_passes_authority_gate_without_mutating_contract(self) -> None:
        payload = json.loads(EXECUTION_AUTHORITY.read_text(encoding="utf-8"))
        authority = validate_zec_v0_3_development_execution_authority(
            payload,
            authority_pr_merged=True,
            observed_blob_shas=dict(payload["bound_git_blobs"]),
        )
        self.assertFalse(
            self.contract["authority"]["offline_development_runner_authorized"]
        )
        with self.assertRaisesRegex(ValueError, "development source candles are required"):
            run_zec_v0_3_development_matrix(
                candles_15m=(),
                contract=self.contract,
                execution_authority=authority,
            )


if __name__ == "__main__":
    unittest.main()
