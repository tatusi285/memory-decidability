"""Scoring rules, including the leniency the paper does not mention."""

from __future__ import annotations

import unittest

from memdec.scoring import classify, is_ambiguous, score_answer
from memdec.store import Chain

CHAIN = Chain("服务00", "端口", "8000", "9000", "o0", "n0")


class TestScoring(unittest.TestCase):
    def test_exact_value(self):
        self.assertEqual(score_answer("9000", CHAIN), "correct")
        self.assertEqual(score_answer("8000", CHAIN), "stale")

    def test_whitespace_and_punctuation_are_ignored(self):
        self.assertEqual(score_answer(" 9000。", CHAIN), "correct")
        self.assertEqual(score_answer("8000 端口", CHAIN), "stale")

    def test_unrelated_text_is_unknown(self):
        self.assertEqual(score_answer("不知道", CHAIN), "unknown")
        self.assertEqual(score_answer("", CHAIN), "unknown")

    def test_errors_become_unknown(self):
        self.assertEqual(score_answer("<error:HTTP429>", CHAIN), "unknown")

    def test_both_values_count_as_correct_but_are_flagged(self):
        answer = "原来是 8000，现在是 9000"
        self.assertEqual(score_answer(answer, CHAIN), "correct")
        self.assertTrue(is_ambiguous(answer, CHAIN))
        self.assertTrue(classify(answer, CHAIN).ambiguous)

    def test_unambiguous_answers_are_not_flagged(self):
        self.assertFalse(is_ambiguous("9000", CHAIN))

    def test_new_value_is_tested_first(self):
        """A value that contains the other as a prefix would otherwise be misread."""
        chain = Chain("e", "a", "800", "8000", "o", "n")
        self.assertEqual(score_answer("8000", chain), "correct")


if __name__ == "__main__":
    unittest.main()
