"""The manipulations added for the roadmap, and the defaults they must not disturb."""

from __future__ import annotations

import random
import unittest

from memdec.policies import (
    SELECTABLE_POLICIES,
    apply_review,
    random_selection_hit_rate,
    review_budget,
    select_review,
)
from memdec.prompts import FILLER, RenderCfg, build_prompt, with_filler
from memdec.store import build_store

CFG = RenderCfg("none", "template")


def hit_rate(policy: str, **kwargs) -> tuple[int, int]:
    store = build_store(0, 40, 7, **kwargs)
    budget = review_budget(store, CFG)
    rng = random.Random("test")
    picked = select_review(store, budget, policy, CFG, rng=rng)
    return apply_review(picked), len(picked)


class TestDefaultsUnchanged(unittest.TestCase):
    def test_optional_manipulations_are_off_by_default(self):
        plain = build_store(0, 12, 7)
        explicit = build_store(0, 12, 7, importance_mode="random", late_duplicates=0.0)
        self.assertEqual([e.day for e in plain.entries], [e.day for e in explicit.entries])
        self.assertEqual([e.importance for e in plain.entries],
                         [e.importance for e in explicit.entries])

    def test_all_shipped_chains_strictly_order_the_records(self):
        store = build_store(0, 40, 7)
        for chain in store.chains:
            self.assertLess(store.by_id(chain.old_id).day, store.by_id(chain.new_id).day)


class TestLateDuplicates(unittest.TestCase):
    def test_late_writes_invert_the_order_for_some_chains(self):
        store = build_store(0, 40, 7, late_duplicates=0.5)
        inverted = [c for c in store.chains
                    if store.by_id(c.old_id).day > store.by_id(c.new_id).day]
        self.assertTrue(inverted)
        self.assertLess(len(inverted), 40)

    def test_late_writes_let_recency_reach_a_conflict(self):
        """The control for blocker B2: break the correlation and recency works."""
        archived, reviewed = hit_rate("recent", late_duplicates=0.5)
        self.assertGreater(archived, 0)
        self.assertGreater(archived / reviewed, 0.1)


class TestImportanceSignal(unittest.TestCase):
    def test_signal_separates_superseded_from_current(self):
        store = build_store(0, 40, 7, importance_mode="signal", importance_signal=0.8)
        new = [e.importance for e in store.entries if e.eid.startswith("n")]
        old = [e.importance for e in store.entries if e.eid.startswith("o")]
        self.assertGreater(sum(old) / len(old), sum(new) / len(new))

    def test_zero_signal_is_uninformative(self):
        store = build_store(0, 40, 7, importance_mode="signal", importance_signal=0.0)
        new = [e.importance for e in store.entries if e.eid.startswith("n")]
        old = [e.importance for e in store.entries if e.eid.startswith("o")]
        self.assertAlmostEqual(sum(old) / len(old), sum(new) / len(new), delta=0.08)

    def test_strong_signal_makes_the_policy_effective(self):
        """The control for blocker B3: coverage tracks the signal, not the policy name."""
        weak = hit_rate("importance", importance_mode="signal", importance_signal=0.0)
        strong = hit_rate("importance", importance_mode="signal", importance_signal=0.9)
        self.assertGreater(strong[0] / strong[1], weak[0] / weak[1])
        self.assertGreater(strong[0], 30)

    def test_signal_is_monotone_across_the_sweep(self):
        coverage = []
        for rho in (0.0, 0.25, 0.5, 0.75, 1.0):
            archived, reviewed = hit_rate("importance", importance_mode="signal",
                                          importance_signal=rho)
            coverage.append(archived / reviewed)
        self.assertEqual(coverage, sorted(coverage))
        self.assertGreater(coverage[-1], coverage[0] + 0.2)

    def test_bounds_are_enforced(self):
        with self.assertRaises(ValueError):
            build_store(0, 4, 7, importance_mode="signal", importance_signal=1.5)
        with self.assertRaises(ValueError):
            build_store(0, 4, 7, importance_mode="magic")


class TestRandomPolicy(unittest.TestCase):
    def test_random_is_selectable(self):
        self.assertIn("random", SELECTABLE_POLICIES)
        self.assertEqual(len(SELECTABLE_POLICIES), 5)

    def test_random_needs_a_seed(self):
        store = build_store(0, 40, 7)
        with self.assertRaises(ValueError):
            select_review(store, 500, "random", CFG, rng=None)

    def test_random_is_reproducible(self):
        first = [e.eid for e in select_review(build_store(0, 40, 7), 576, "random", CFG,
                                              rng=random.Random("x"))]
        second = [e.eid for e in select_review(build_store(0, 40, 7), 576, "random", CFG,
                                               rng=random.Random("x"))]
        self.assertEqual(first, second)

    def test_random_hit_rate_tracks_the_theoretical_reference(self):
        archived, reviewed = hit_rate("random")
        observed = archived / reviewed
        self.assertAlmostEqual(observed, random_selection_hit_rate(40), delta=0.12)


class TestPrefixFiller(unittest.TestCase):
    def test_prefix_puts_fillers_before_the_records(self):
        lines = with_filler(["a", "b"], 2, "prefix")
        self.assertEqual(lines, [FILLER, FILLER, "a", "b"])

    def test_prefix_prompt_mentions_no_digits_in_the_filler(self):
        prompt = build_prompt(["a·b = 8000"], "e", "b", "none", filler_k=3,
                              filler_mode="prefix")
        head = prompt.splitlines()[1]
        self.assertEqual(head, FILLER)

    def test_prefix_differs_from_tail(self):
        tail = build_prompt(["r1", "r2"], "e", "b", "none", 2, "tail")
        prefix = build_prompt(["r1", "r2"], "e", "b", "none", 2, "prefix")
        self.assertNotEqual(tail, prefix)


if __name__ == "__main__":
    unittest.main()
