"""Statistics are pinned against published critical values."""

from __future__ import annotations

import math
import unittest

from memdec.stats import (
    clopper_pearson,
    design_effect,
    effective_sample_size,
    holm,
    mean_ci,
    pooled_rate,
    t_critical,
    wilson,
)


class TestCriticalValues(unittest.TestCase):
    def test_t_table(self):
        self.assertAlmostEqual(t_critical(2), 4.303, places=3)
        self.assertAlmostEqual(t_critical(4), 2.776, places=3)
        self.assertAlmostEqual(t_critical(11), 2.201, places=3)
        self.assertAlmostEqual(t_critical(1), 12.706, places=3)

    def test_t_large_df_approaches_normal(self):
        self.assertAlmostEqual(t_critical(1000), 1.96, places=2)

    def test_t_is_not_hard_coded(self):
        """The original bug: one constant for every sample size."""
        self.assertGreater(t_critical(2), t_critical(4))
        self.assertGreater(t_critical(4), t_critical(11))

    def test_mean_ci_uses_df(self):
        values = [1.0, 2.0, 3.0]
        mean, half = mean_ci(values)
        self.assertAlmostEqual(mean, 2.0)
        sd = 1.0
        self.assertAlmostEqual(half, 4.303 * sd / math.sqrt(3), places=3)


class TestBinomialIntervals(unittest.TestCase):
    def test_clopper_pearson_all_successes(self):
        lo, hi = clopper_pearson(10, 10)
        self.assertAlmostEqual(lo, 0.025 ** 0.1, places=4)
        self.assertEqual(hi, 1.0)

    def test_clopper_pearson_no_successes(self):
        lo, hi = clopper_pearson(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 1 - 0.025 ** 0.1, places=4)

    def test_clopper_pearson_saturated_grid(self):
        """480/480 is not certainty; the paper reports it as if it were."""
        lo, hi = clopper_pearson(480, 480)
        self.assertLess(lo, 0.995)
        self.assertGreater(lo, 0.985)
        self.assertEqual(hi, 1.0)

    def test_clopper_pearson_contains_point_estimate(self):
        for k, n in ((1, 480), (76, 480), (17, 40), (0, 40)):
            lo, hi = clopper_pearson(k, n)
            self.assertLessEqual(lo, k / n)
            self.assertGreaterEqual(hi, k / n)

    def test_wilson_symmetric_at_half(self):
        lo, hi = wilson(20, 40)
        self.assertAlmostEqual(lo, 1 - hi, places=9)

    def test_clopper_pearson_validation(self):
        with self.assertRaises(ValueError):
            clopper_pearson(5, 4)
        with self.assertRaises(ValueError):
            clopper_pearson(0, 0)


class TestSampleSizeHonesty(unittest.TestCase):
    def test_effective_sample_size_is_the_chain_count(self):
        self.assertEqual(effective_sample_size(480, 40), 40)

    def test_design_effect(self):
        self.assertAlmostEqual(design_effect(480, 40), math.sqrt(12), places=9)

    def test_pooled_rate_recovers_counts(self):
        k, n = pooled_rate([1.0, 1.0, 1.0], 40)
        self.assertEqual((k, n), (120, 120))


class TestHolm(unittest.TestCase):
    def test_monotone_and_bounded(self):
        adjusted = holm([0.01, 0.04, 0.03])
        self.assertTrue(all(0.0 <= p <= 1.0 for p in adjusted))
        self.assertEqual(adjusted, sorted(adjusted))


if __name__ == "__main__":
    unittest.main()
