"""Review policies, including the two that cannot work by construction."""

from __future__ import annotations

import unittest

from memdec.policies import (
    POLICIES,
    apply_review,
    half_life,
    random_selection_hit_rate,
    retention,
    review_budget,
    select_review,
)
from memdec.prompts import RenderCfg
from memdec.store import build_store

CFG = RenderCfg("none", "template")


def fresh(seed: int = 0, delay: float = 7, chains: int = 40):
    return build_store(seed=seed, n_chains=chains, delay=delay)


class TestBudget(unittest.TestCase):
    def test_budget_is_forty_percent_of_the_store(self):
        store = fresh()
        budget = review_budget(store, CFG, 0.4)
        self.assertEqual(budget, int(store.total_chars(CFG) * 0.4))

    def test_absolute_budget_wins(self):
        store = fresh()
        self.assertEqual(review_budget(store, CFG, 0.4, absolute=500), 500)

    def test_selection_respects_the_budget(self):
        store = fresh()
        budget = review_budget(store, CFG, 0.4)
        for policy in POLICIES[1:]:
            picked = select_review(store, budget, policy, CFG)
            self.assertLessEqual(sum(len(e.text(CFG)) for e in picked), budget)

    def test_budget_fills_the_available_space(self):
        store = fresh()
        budget = review_budget(store, CFG, 0.4)
        picked = select_review(store, budget, "decay", CFG)
        self.assertGreater(len(picked), 20)


class TestSelection(unittest.TestCase):
    def test_none_reviews_nothing(self):
        self.assertEqual(select_review(fresh(), 10_000, "none", CFG), [])

    def test_unknown_policy_is_rejected(self):
        with self.assertRaises(ValueError):
            select_review(fresh(), 100, "recency", CFG)

    def test_recent_takes_the_newest_records(self):
        store = fresh()
        picked = select_review(store, review_budget(store, CFG), "recent", CFG)
        unseen = [e.day for e in store.entries if e not in picked]
        self.assertGreaterEqual(min(e.day for e in picked), max(unseen))

    def test_decay_takes_the_lowest_retention_first(self):
        store = fresh()
        picked = select_review(store, review_budget(store, CFG), "decay", CFG)
        self.assertLessEqual(max(retention(e) for e in picked),
                             min(retention(e) for e in store.entries if e not in picked) + 1e-12)

    def test_recent_cannot_archive_anything(self):
        """Enumeration over the shipped configuration: recency reaches no conflict.

        The 40 updated records are the newest entries and nearly fill the 41-record
        budget, so this holds for every seed and delay that was actually run. It is a
        property of the store, not a discovery about recency.
        """
        for seed in range(3):
            for delay in (1, 7, 30, 90):
                store = fresh(seed=seed, delay=delay)
                picked = select_review(store, review_budget(store, CFG), "recent", CFG)
                self.assertEqual(apply_review(picked), 0,
                                 f"seed={seed} delay={delay} archived a conflict")


class TestReview(unittest.TestCase):
    def test_archiving_is_deterministic_and_counted(self):
        store = fresh()
        budget = review_budget(store, CFG)
        picked = select_review(store, budget, "decay", CFG)
        archived = apply_review(picked)
        self.assertEqual(archived, sum(1 for e in picked if e.superseded_by))
        self.assertEqual(len(store.live()), 2 * len(store.chains) + 24 - archived)

    def test_archived_records_leave_retrieval(self):
        store = fresh()
        budget = review_budget(store, CFG)
        picked = select_review(store, budget, "decay", CFG)
        apply_review(picked)
        self.assertTrue(all(not e.archived for e in store.live()))

    def test_refreshing_moves_the_timestamp_to_now(self):
        store = fresh()
        target = next(e for e in store.entries if e.chain_id and not e.superseded_by)
        before = target.day
        apply_review([target])
        self.assertGreater(target.day, before)


class TestRetention(unittest.TestCase):
    def test_half_life_bands(self):
        self.assertEqual(half_life(0.9), 30.0)
        self.assertEqual(half_life(0.7), 12.0)
        self.assertEqual(half_life(0.3), 6.0)

    def test_retention_decays_with_age(self):
        store = fresh()
        entry = store.entries[0]
        self.assertGreater(retention(entry, now=entry.day), retention(entry, now=entry.day + 10))


class TestRandomReference(unittest.TestCase):
    def test_hit_rate_reference(self):
        self.assertAlmostEqual(random_selection_hit_rate(40), 40 / 104)
        self.assertAlmostEqual(random_selection_hit_rate(13), 13 / 50)

    def test_decay_beats_random_and_recency_does_not(self):
        reference = random_selection_hit_rate(40)
        store = fresh()
        budget = review_budget(store, CFG)
        picked = select_review(store, budget, "decay", CFG)
        self.assertGreater(apply_review(picked) / len(picked), reference)

        store = fresh()
        picked = select_review(store, budget, "recent", CFG)
        self.assertEqual(apply_review(picked), 0)


if __name__ == "__main__":
    unittest.main()
