"""Replay the deterministic half of the pipeline against the shipped data.

This is the test that matters for reproducibility.  It rebuilds every store from the
seed and delay recorded in the manifest, re-applies the review policy, re-assembles
the retrieved context, and re-predicts the verdict with a single rule -- "the model
answers the last record it can see".  If the shipped ``results.csv`` files were
produced by the pipeline described in the paper, the replayed counts have to match.

Nothing here calls a model: the replay checks the *design*, and the rule it applies
is the rule the audit recovered from the data.

One detail is easy to get wrong and would invalidate the comparison: the original
runner builds a **fresh store for every (delay, seed, policy)**.  Reusing a store
across policies would let one policy's timestamp refreshes leak into the next.
"""

from __future__ import annotations

import unittest

from memdec import manifest
from memdec.policies import apply_review, review_budget, select_review
from memdec.prompts import RenderCfg
from memdec.runner import build_context
from memdec.store import build_store

CORE_RUNS = ("out_live_bare", "out_live_bare_rev", "out_live_date", "out_live")
POLICIES = ("none", "recent", "importance", "decay")


def _blocks(run_id: str):
    """Yield ``(delay, seed, policy, fresh_store, review counts)`` for one run.

    A new store is built for each block, exactly as the original runner does.
    """
    spec = manifest.load_runs()[run_id]
    cfg = RenderCfg(spec.time_format, spec.text_style)
    for delay in spec.delay_list:
        for seed in range(spec.seeds):
            for policy in POLICIES:
                store = build_store(seed, spec.chains, delay)
                budget = review_budget(store, cfg)
                picked = select_review(store, budget, policy, cfg)
                archived = apply_review(picked)
                yield delay, seed, policy, store, (len(picked), archived)


class TestReplayCoreGrid(unittest.TestCase):
    def test_review_counts_match_the_shipped_summary_rows(self):
        """The review and archiving accounting must reproduce exactly."""
        for run_id in CORE_RUNS:
            expected = {(r["delay"], r["seed"], r["policy"]):
                        (int(float(r["reviewed"])), int(float(r["archived"])))
                        for r in manifest.summary_rows(run_id)}
            seen = 0
            for delay, seed, policy, _store, (reviewed, archived) in _blocks(run_id):
                key = (str(delay), str(seed), policy)
                self.assertEqual((reviewed, archived), expected[key],
                                 f"{run_id} {delay}d seed{seed} {policy}")
                seen += 1
            self.assertEqual(seen, len(expected))

    def test_position_rule_reproduces_every_probe(self):
        """All 1,920 probes in each core order condition follow one rule.

        The rule: a context with one visible record yields that record's value, and a
        context with two yields the last one.  Because the last record is the outdated
        one exactly when the context is ordered newest-first, the verdict is a
        deterministic function of order and archive state.
        """
        for run_id in ("out_live_bare", "out_live_bare_rev"):
            spec = manifest.load_runs()[run_id]
            cfg = RenderCfg(spec.time_format, spec.text_style)
            rows = {(r["delay"], r["seed"], r["policy"], r["entity"]): r
                    for r in manifest.probe_rows(run_id)}
            matched = mismatched = 0
            for delay, seed, policy, store, _counts in _blocks(run_id):
                for chain in store.chains:
                    row = rows[(str(delay), str(seed), policy, chain.entity)]
                    ctx = build_context(store, chain, 1200, spec.ctx_order, cfg)
                    self.assertIn(len(ctx), (1, 2))
                    predicted = "stale" if ctx[-1].value == chain.old_value else "correct"
                    if predicted == row["verdict"]:
                        matched += 1
                    else:
                        mismatched += 1
            self.assertEqual(mismatched, 0, f"{run_id}: {mismatched} probes disagreed")
            self.assertEqual(matched, 1920)

    def test_context_is_one_or_two_records(self):
        """Retrieval is per-slot, so the 24 distractors never reach a queried context."""
        spec = manifest.load_runs()["out_live_bare"]
        cfg = RenderCfg(spec.time_format, spec.text_style)
        for _delay, _seed, _policy, store, _counts in _blocks("out_live_bare"):
            for chain in store.chains:
                ctx = build_context(store, chain, 1200, spec.ctx_order, cfg)
                self.assertLessEqual(len(ctx), 2)


class TestReplayIdentity(unittest.TestCase):
    def test_stale_equals_one_minus_coverage_cell_by_cell(self):
        """The identity is arithmetic; the replay shows there is no residual."""
        run_id = "out_live_bare"
        spec = manifest.load_runs()[run_id]
        checked = 0
        for row in manifest.summary_rows(run_id):
            archived = float(row["archived"])
            self.assertAlmostEqual(float(row["stale"]), 1 - archived / spec.chains, places=12)
            self.assertAlmostEqual(
                float(row["correct"]) + float(row["stale"]) + float(row["unknown"]), 1.0,
                places=9)
            checked += 1
        self.assertEqual(checked, 48)


class TestContextOrdering(unittest.TestCase):
    def test_no_review_newest_first_puts_the_stale_record_last(self):
        store = build_store(0, 40, 1)
        cfg = RenderCfg("none", "template")
        stale_last = sum(
            1 for chain in store.chains
            if build_context(store, chain, 1200, "newest_first", cfg)[-1].value == chain.old_value
        )
        self.assertEqual(stale_last, 40)

    def test_no_review_oldest_first_puts_the_stale_record_first(self):
        store = build_store(0, 40, 1)
        cfg = RenderCfg("none", "template")
        stale_first = sum(
            1 for chain in store.chains
            if build_context(store, chain, 1200, "oldest_first", cfg)[0].value == chain.old_value
        )
        self.assertEqual(stale_first, 40)


if __name__ == "__main__":
    unittest.main()
