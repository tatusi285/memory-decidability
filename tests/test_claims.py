"""The manuscript's numbers must follow from ``data/``."""

from __future__ import annotations

import unittest

from memdec import claims


class TestSupportedClaims(unittest.TestCase):
    def test_all_published_values_reproduce(self):
        results = claims.evaluate()
        failures = [(r.claim.cid, r.claim.label, r.claim.expected, r.computed)
                    for r in results if not r.ok]
        self.assertEqual(failures, [], f"{len(failures)} published values did not reproduce")

    def test_there_are_sixty_two_of_them(self):
        self.assertEqual(len(claims.SUPPORTED), 62)

    def test_claim_ids_are_unique(self):
        ids = [c.cid for c in claims.SUPPORTED]
        self.assertEqual(len(ids), len(set(ids)))


class TestExtraValues(unittest.TestCase):
    def test_values_the_paper_omits_are_present_in_the_data(self):
        for claim in claims.EXTRA:
            value = claims.compute(claim)
            self.assertAlmostEqual(value, claim.expected, delta=claims.tolerance(claim),
                                   msg=f"{claim.cid} {claim.label}")

    def test_the_contradicting_cell_exists(self):
        """Mixed wording + dates is 21.0%, not <= 0.2%."""
        claim = next(c for c in claims.EXTRA if c.cid == "X2")
        self.assertGreater(claims.compute(claim), 15.0)


class TestDisputes(unittest.TestCase):
    def test_disputes_are_declared(self):
        self.assertGreaterEqual(len(claims.DISPUTES), 8)

    def test_every_dispute_has_evidence(self):
        for dispute in claims.DISPUTES:
            self.assertTrue(dispute.evidence.strip())
            self.assertTrue(dispute.verdict.strip())


if __name__ == "__main__":
    unittest.main()
