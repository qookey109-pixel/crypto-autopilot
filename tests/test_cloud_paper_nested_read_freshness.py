from __future__ import annotations

from crypto_autopilot.paper.cloud_loop_v0_3 import run_cloud_step
from test_cloud_paper_loop_v0_1 import MemoryStore, NeverCalledFeed, REGISTRY


def test_replay_checks_freshness_before_every_nested_read():
    store = MemoryStore()
    kwargs = dict(
        tick_ms=420000, previous_slot=None, feed=NeverCalledFeed(),
        market_supplier=lambda: {"provider_requests_performed": 0},
        candidate_supplier=lambda market, state: (),
        strategy_registry=REGISTRY,
    )
    run_cloud_step(store=store, before_external=lambda: None, **kwargs)

    class ReadGuardedStore:
        def __init__(self, delegate):
            self.delegate = delegate
            self.fresh = False
            self.reads = 0

        def check(self):
            self.fresh = True

        def get_json(self, kind, object_id):
            assert self.fresh, f"freshness not checked before {kind} read"
            self.fresh = False
            self.reads += 1
            return self.delegate.get_json(kind, object_id)

    guarded = ReadGuardedStore(store)
    result = run_cloud_step(store=guarded, before_external=guarded.check, **kwargs)
    assert result["state"] == "REPLAYED"
    assert guarded.reads > 1
