"""Generated tables, figures and audit report."""

from __future__ import annotations

import re
import unittest

from memdec.analysis import audit, figures, tables


def _assert_valid_svg(test: unittest.TestCase, svg: str) -> None:
    test.assertTrue(svg.startswith("<svg"), "SVG must start with the root element")
    test.assertTrue(svg.rstrip().endswith("</svg>"), "SVG must be closed")
    test.assertNotIn("None", svg, "a coordinate rendered as None")
    test.assertNotIn("nan", svg, "a coordinate rendered as nan")
    for value in re.findall(r'(?<![A-Za-z])(?:x|y|cx|cy)="([^"]+)"', svg):
        float(value)  # raises if a coordinate is not numeric


class TestTables(unittest.TestCase):
    def test_all_tables_render(self):
        produced = tables.all_tables()
        self.assertEqual(len(produced), 8)
        for name, body in produced.items():
            self.assertIn("| :---", body, f"{name} is not a markdown table")
            self.assertGreater(len(body.splitlines()), 3, name)

    def test_table1_reproduces_the_published_cells(self):
        body = tables.table1()
        self.assertIn("100.0", body)
        self.assertIn("15.8", body)

    def test_uncertainty_table_has_both_denominators(self):
        body = tables.table1_uncertainty()
        self.assertIn("95% CI over probes", body)
        self.assertIn("95% CI over chains", body)

    def test_interaction_table_exposes_the_missing_cell(self):
        body = tables.table_interaction()
        self.assertIn("Mixed natural sentences", body)
        self.assertIn("21.0", body)

    def test_table4_carries_the_random_reference(self):
        body = tables.table4()
        self.assertIn("Conflict-hit rate", body)
        self.assertIn("Random reference", body)

    def test_inventory_lists_every_run(self):
        body = tables.inventory()
        self.assertEqual(body.count("\n") - 1, 37)


class TestFigures(unittest.TestCase):
    def test_figures_are_valid_svg(self):
        for _name, svg in figures.all_figures().items():
            _assert_valid_svg(self, svg)

    def test_figure2_contains_every_dose(self):
        svg = figures.figure2()
        self.assertEqual(svg.count("<circle"), 8)  # six tail points + two gap points

    def test_figure_counts_match_series(self):
        self.assertEqual(figures.figure1().count("<circle"), 4 * 4)


class TestAudit(unittest.TestCase):
    def test_report_builds_and_has_every_section(self):
        report = audit.build_audit_report()
        for heading in ("Inventory", "determined by the design", "independent unit",
                        "arithmetic, not a finding", "Which records get reviewed",
                        "same t value", "not a decay curve", "does not add up",
                        "end-to-end table", "real-log corpus", "Byte-identical",
                        "Scoring leniency"):
            self.assertIn(heading, report, heading)

    def test_findings_are_ordered_by_severity(self):
        severities = [f.severity for f in audit.findings()]
        order = {"blocker": 0, "major": 1, "minor": 2, "info": 3}
        self.assertEqual(severities, sorted(severities, key=lambda s: order[s]))

    def test_determinism_claim(self):
        rows = audit.determinism()
        core = [r for r in rows if r.run_id == "out_live_bare"]
        self.assertTrue(core)
        self.assertEqual(sum(r.exceptions for r in core), 0)
        self.assertEqual(sum(r.matched for r in core), 1920)

    def test_inventory_totals(self):
        inv = audit.inventory()
        self.assertEqual(inv.n_runs, 37)
        self.assertEqual(inv.n_probes, 50_832)

    def test_archive_identity_holds(self):
        rows = audit.archive_identity()
        core = next(r for r in rows if r.run_id == "out_live_bare")
        self.assertLess(core.max_deviation, 1e-9)

    def test_filler_curve_is_not_monotone(self):
        points = [p for p in audit.filler_curve() if p.mode == "tail" and p.k >= 1]
        rising = all(a.mean <= b.mean for a, b in zip(points, points[1:], strict=False))
        self.assertFalse(rising)

    def test_chain_invariance_of_the_core_grid(self):
        rows = {r.run_id: r for r in audit.chain_invariance()}
        self.assertEqual(rows["out_live_bare"].varying, 0)
        self.assertEqual(rows["out_live_bare"].chains, 40)

    def test_scoring_leniency_is_negligible(self):
        info = audit.scoring_leniency()
        self.assertLess(info["ambiguous"] / info["total"], 0.01)


if __name__ == "__main__":
    unittest.main()
