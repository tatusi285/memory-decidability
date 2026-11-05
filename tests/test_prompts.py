"""Rendering and prompt assembly: golden strings, so a silent rewrite fails CI."""

from __future__ import annotations

import unittest

from memdec import prompts
from memdec.prompts import RenderCfg

CFG = RenderCfg("none", "template")


class TestRecordRendering(unittest.TestCase):
    def test_template_body_is_stable(self):
        body = prompts.record_text("服务00", "端口", "8000", 199, "o0", "template", "none")
        self.assertEqual(body, "服务00·端口 = 8000")

    def test_date_prefix(self):
        text = prompts.record_text("服务00", "端口", "8000", 199, "o0", "template", "date")
        # day 199 after 2026-01-01 is 2026-07-19
        self.assertEqual(text, "[2026-07-19] 服务00·端口 = 8000")

    def test_day_prefix(self):
        text = prompts.record_text("服务00", "端口", "8000", 199, "o0", "template", "day")
        self.assertEqual(text, "[第199天] 服务00·端口 = 8000")

    def test_natural_style_rotates_by_entry_id(self):
        a = prompts.record_text("e", "端口", "1", 10, "o0", "natural", "none")
        b = prompts.record_text("e", "端口", "1", 10, "n0", "natural", "none")
        self.assertNotEqual(a, b)
        self.assertIn("1", a)

    def test_value_position_variant_moves_the_number(self):
        first = prompts.record_text("e", "端口", "8000", 10, "o0", "vary_number", "none")
        self.assertTrue(first.startswith("记录："))
        third = prompts.record_text("e", "端口", "8000", 10, "o2", "vary_number", "none")
        self.assertIn("这个值对应", third)


class TestPromptAssembly(unittest.TestCase):
    def test_prompt_without_timestamp(self):
        prompt = prompts.build_prompt(["服务00·端口 = 8000"], "服务00", "端口", "none")
        self.assertEqual(
            prompt,
            "你的长期记忆里与「服务00」相关的记录如下：\n"
            "服务00·端口 = 8000\n\n"
            "问题：服务00 的端口现在是多少？只输出值本身，不要解释。",
        )

    def test_prompt_with_date(self):
        prompt = prompts.build_prompt(["[2026-07-19] x"], "服务00", "端口", "date")
        self.assertIn("现在是 2026-07-20。", prompt)

    def test_prompt_with_relative_day(self):
        prompt = prompts.build_prompt(["[第199天] x"], "服务00", "端口", "day")
        self.assertIn("现在是 第200天。", prompt)

    def test_empty_context_is_explicit(self):
        prompt = prompts.build_prompt([], "服务00", "端口", "none")
        self.assertIn("（无相关记录）", prompt)

    def test_filler_tail_appends_after_records(self):
        lines = prompts.with_filler(["a", "b"], 2, "tail")
        self.assertEqual(lines, ["a", "b", prompts.FILLER, prompts.FILLER])

    def test_filler_gap_sits_between_records(self):
        lines = prompts.with_filler(["a", "b"], 2, "gap")
        self.assertEqual(lines, ["a", prompts.FILLER, prompts.FILLER, "b"])

    def test_filler_has_no_digits(self):
        self.assertFalse(any(ch.isdigit() for ch in prompts.FILLER))

    def test_filler_is_a_no_op_at_zero(self):
        self.assertEqual(prompts.with_filler(["a"], 0, "gap"), ["a"])

    def test_prompt_fingerprint_is_stable(self):
        prompt = prompts.build_prompt(["a"], "e", "端口", "none")
        self.assertEqual(prompts.prompt_fingerprint(prompt),
                         prompts.prompt_fingerprint(prompt))
        self.assertEqual(len(prompts.prompt_fingerprint(prompt)), 16)


class TestRenderCfg(unittest.TestCase):
    def test_rejects_unknown_values(self):
        with self.assertRaises(ValueError):
            RenderCfg("absolute", "template")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            RenderCfg("none", "chatty")  # type: ignore[arg-type]

    def test_prompt_version_is_declared(self):
        self.assertTrue(prompts.PROMPT_VERSION)
        self.assertRegex(prompts.PROMPT_VERSION, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
