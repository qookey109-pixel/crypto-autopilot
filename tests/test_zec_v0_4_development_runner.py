from __future__ import annotations

import json
import math
from pathlib import Path
import unittest

from crypto_autopilot.models import Candle
from crypto_autopilot.research.zec_v0_3_selection_policy import (
    validate_zec_v0_3_selection_policy,
)
from crypto_autopilot.research.zec_v0_4_development_contract import (
    build_zec_v0_4_candidate_grid,
)
from crypto_autopilot.research.zec_v0_4_development_execution_authority import (
    validate_zec_v0_4_development_execution_authority,
)
from crypto_autopilot.research.zec_v0_4_development_runner import (
    FIXED_MAX_LEVERAGE,
    FIXED_RISK_FRACTION,
    FIXED_STOP_ATR_MULTIPLIER,
    ZecV04CandidateFoldResult,
    ZecV04DevelopmentAuthorityError,
    ZecV04FoldMetrics,
    evaluate_zec_v0_4_candidate_fold,
    rank_zec_v0_4_development_results,
    run_zec_v0_4_development_matrix,
    select_zec_v0_4_development_champion,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "zec_strategy_v0_4_development_matrix_v0_1.json"
SELECTION_POLICY = ROOT / "config" / "zec_strategy_v0_3_selection_policy_v0_1.json"
EXECUTION_AUTHORITY = (
    ROOT
    / "research/receipts/2026-09-21-zec-v0-4-development-one-shot-authority.json"
)
FIFTEEN_MINUTES_MS = 15 * 60 * 1000


def _synthetic_source(bar_count: int = 5600) -> list[Candle]:
    rows: list[Candle] = []
    previous = 100.0
    for index in range(bar_count):
        close = (
            100.0
            + index * 0.003
            + 3.0 * math.sin(index / 18.0)
            + 0.7 * math.sin(index / 5.0)
        )
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
) -> ZecV04CandidateFoldResult:
    return ZecV04CandidateFoldResult(
        candidate_id=candidate_id,
        fold_id=fold_id,
        start_time_ms=0,
        end_exclusive_time_ms=1,
        initial_equity_usd=10_000.0,
        final_equity_usd=10_000.0,
        trades=(),
        metrics=ZecV04FoldMetrics(
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
        ),
    )


class ZecV04OfflineDevelopmentRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.selection_payload = json.loads(SELECTION_POLICY.read_text(encoding="utf-8"))
        cls.candidates = build_zec_v0_4_candidate_grid(cls.contract)

    def test_candidate_fold_engine_is_paper_only_and_preserves_fixed_risk(self) -> None:
        candidate = self.candidates[0]
        source = _synthetic_source()
        fold_start = 4000 * FIFTEEN_MINUTES_MS
        fold_end = 5600 * FIFTEEN_MINUTES_MS

        result = evaluate_zec_v0_4_candidate_fold(
            candles_15m=source,
            candidate=candidate,
            fold_id="synthetic-development",
            fold_start_time_ms=fold_start,
            fold_end_exclusive_time_ms=fold_end,
            funding_points=None,
        )

        self.assertGreaterEqual(result.metrics.trade_count, 0)
        self.assertEqual(FIXED_RISK_FRACTION, 0.01)
        self.assertEqual(FIXED_MAX_LEVERAGE, 3.0)
        self.assertEqual(FIXED_STOP_ATR_MULTIPLIER, 2.5)
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

    def test_ranking_requires_complete_matrix(self) -> None:
        candidates = self.candidates[:2]
        fold_ids = ("fold-a", "fold-b")
        rows = (
            _matrix_result(candidates[0].candidate_id, "fold-a", return_pct=1.0, drawdown=5.0, trades=40),
            _matrix_result(candidates[0].candidate_id, "fold-b", return_pct=0.5, drawdown=6.0, trades=40),
            _matrix_result(candidates[1].candidate_id, "fold-a", return_pct=0.8, drawdown=4.0, trades=40),
            _matrix_result(candidates[1].candidate_id, "fold-b", return_pct=0.7, drawdown=4.5, trades=40),
        )
        summaries, ranking = rank_zec_v0_4_development_results(
            candidates=candidates,
            fold_ids=fold_ids,
            results=rows,
        )
        self.assertEqual(summaries[0].candidate_id, candidates[1].candidate_id)
        self.assertEqual(ranking.diagnostic_leader_id, candidates[1].candidate_id)
        self.assertFalse(ranking.champion_frozen)

        with self.assertRaisesRegex(ValueError, "must be complete"):
            rank_zec_v0_4_development_results(
                candidates=candidates,
                fold_ids=fold_ids,
                results=rows[:-1],
            )

    def test_frozen_selection_policy_can_freeze_only_with_two_stable_neighbors(self) -> None:
        policy, policy_sha = validate_zec_v0_3_selection_policy(self.selection_payload)
        fold_ids = ("fold-a", "fold-b")
        special = {
            "zec-v0-4-01": (4.0, 5.0),
            "zec-v0-4-02": (3.4, 4.1),
            "zec-v0-4-04": (3.2, 3.8),
        }
        rows = []
        for candidate in self.candidates:
            fold_returns = special.get(candidate.candidate_id, (0.5, 0.6))
            rows.extend(
                (
                    _matrix_result(candidate.candidate_id, fold_ids[0], return_pct=fold_returns[0], drawdown=5.0, trades=40),
                    _matrix_result(candidate.candidate_id, fold_ids[1], return_pct=fold_returns[1], drawdown=5.5, trades=40),
                )
            )

        selection = select_zec_v0_4_development_champion(
            candidates=self.candidates,
            fold_ids=fold_ids,
            results=tuple(rows),
            policy=policy,
            policy_sha256=policy_sha,
        )
        self.assertEqual(selection.status, "DEVELOPMENT_CHAMPION_FROZEN")
        self.assertEqual(selection.selected_candidate_id, "zec-v0-4-01")
        self.assertIn("zec-v0-4-02", selection.stable_neighbor_ids)
        self.assertIn("zec-v0-4-04", selection.stable_neighbor_ids)
        self.assertFalse(selection.fresh_confirmation_accessed)
        self.assertFalse(selection.live_trading_authorized)

    def test_selection_policy_requires_30_trades_in_every_fold(self) -> None:
        policy, policy_sha = validate_zec_v0_3_selection_policy(self.selection_payload)
        fold_ids = ("fold-a", "fold-b")
        rows = []
        for candidate in self.candidates:
            rows.extend(
                (
                    _matrix_result(candidate.candidate_id, fold_ids[0], return_pct=2.0, drawdown=4.0, trades=29),
                    _matrix_result(candidate.candidate_id, fold_ids[1], return_pct=2.0, drawdown=4.0, trades=40),
                )
            )
        selection = select_zec_v0_4_development_champion(
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
            ZecV04DevelopmentAuthorityError,
            "development execution is not authorized",
        ):
            run_zec_v0_4_development_matrix(
                candles_15m=(),
                contract=self.contract,
                selection_policy_payload=self.selection_payload,
            )

    def test_separate_merged_authority_passes_gate_without_mutating_contract(self) -> None:
        payload = json.loads(EXECUTION_AUTHORITY.read_text(encoding="utf-8"))
        authority = validate_zec_v0_4_development_execution_authority(
            payload,
            authority_pr_merged=True,
            observed_blob_shas=dict(payload["bound_git_blobs"]),
        )
        self.assertFalse(
            self.contract["authority"]["offline_development_runner_authorized"]
        )
        with self.assertRaisesRegex(ValueError, "development source candles are required"):
            run_zec_v0_4_development_matrix(
                candles_15m=(),
                contract=self.contract,
                selection_policy_payload=self.selection_payload,
                execution_authority=authority,
            )


if __name__ == "__main__":
    unittest.main()
