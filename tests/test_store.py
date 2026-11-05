"""Store construction, including the properties that make the design degenerate."""

from __future__ import annotations

import json
import unittest

from memdec import paths
from memdec.store import build_store, build_store_real, load_real_chains


class TestSyntheticStore(unittest.TestCase):
    def test_shape(self):
        store = build_store(seed=0, n_chains=40, delay=7)
        self.assertEqual(len(store.chains), 40)
        self.assertEqual(len(store.entries), 2 * 40 + 24)

    def test_deterministic(self):
        a = build_store(seed=1, n_chains=10, delay=30)
        b = build_store(seed=1, n_chains=10, delay=30)
        self.assertEqual([e.day for e in a.entries], [e.day for e in b.entries])
        self.assertEqual([e.value for e in a.entries], [e.value for e in b.entries])

    def test_seed_changes_the_nuisance_but_not_the_values(self):
        a = build_store(seed=0, n_chains=10, delay=30)
        b = build_store(seed=1, n_chains=10, delay=30)
        self.assertEqual([c.new_value for c in a.chains], [c.new_value for c in b.chains])
        self.assertNotEqual([e.day for e in a.entries], [e.day for e in b.entries])

    def test_old_record_precedes_new(self):
        store = build_store(seed=2, n_chains=40, delay=90)
        for chain in store.chains:
            old = store.by_id(chain.old_id)
            new = store.by_id(chain.new_id)
            self.assertLess(old.day, new.day)

    def test_exactly_one_superseded_record_per_chain(self):
        store = build_store(seed=3, n_chains=40, delay=1)
        superseded = [e for e in store.entries if e.superseded_by]
        self.assertEqual(len(superseded), 40)

    def test_distractors_are_never_superseded(self):
        store = build_store(seed=4, n_chains=12, delay=7)
        decoys = [e for e in store.entries if e.eid.startswith("d")]
        self.assertEqual(len(decoys), 24)
        self.assertTrue(all(e.superseded_by is None for e in decoys))

    def test_importance_is_drawn_from_a_small_set(self):
        """Importance is random, which is why 'importance-first' has no signal."""
        store = build_store(seed=5, n_chains=40, delay=1)
        values = {round(e.importance, 2) for e in store.entries if e.chain_id}
        self.assertTrue(values <= {0.9, 0.7, 0.55, 0.5, 0.35})

    def test_updating_record_is_the_newest_of_its_slot(self):
        """The property that makes recency-first unable to archive anything."""
        store = build_store(seed=6, n_chains=40, delay=1)
        for chain in store.chains:
            slot = [e for e in store.entries if e.entity == chain.entity]
            self.assertEqual(max(slot, key=lambda e: e.day).value, chain.new_value)


class TestRealCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = load_real_chains(paths.data_dir() / "corpus" / "real_chains.json")
        cls.store = build_store_real(0, cls.raw, delay=7)

    def test_thirteen_chains(self):
        self.assertEqual(len(self.raw), 13)
        self.assertEqual(len(self.store.chains), 13)

    def test_single_entity_and_attribute(self):
        """The corpus cannot test wording heterogeneity: there is one sentence form."""
        self.assertEqual({c["entity"] for c in self.raw}, {"Web GUI"})
        self.assertEqual({c["attr"] for c in self.raw}, {"端口"})

    def test_one_template(self):
        templates = {c["new_text"].replace(c["new_value"], "#") for c in self.raw}
        self.assertEqual(len(templates), 1)

    def test_logs_do_not_always_provide_a_strict_order(self):
        same_day = [c for c in self.raw if c["old_date"] == c["new_date"]]
        self.assertEqual(len(same_day), 5)

    def test_rendered_timestamps_are_synthetic(self):
        """The log dates are never rendered; a generated date is."""
        from memdec.prompts import RenderCfg

        cfg = RenderCfg("date", "template")
        old = self.store.by_id(self.store.chains[0].old_id)
        self.assertTrue(old.text(cfg).startswith("[2026-"))
        self.assertNotIn("2026-10-25", old.text(cfg))

    def test_values_are_distinct(self):
        values = {c["old_value"] for c in self.raw} | {c["new_value"] for c in self.raw}
        self.assertEqual(len(values), 14)

    def test_corpus_is_valid_json(self):
        path = paths.data_dir() / "corpus" / "real_chains.json"
        self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), list)


if __name__ == "__main__":
    unittest.main()
