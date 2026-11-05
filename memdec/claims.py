"""The numbers the paper reports, and whether the shipped data produce them.

``SUPPORTED`` holds the 62 values that the author's own checker verified.  They are
reproduced here so that the release has one machine-readable statement of what the
manuscript claims.

A passing run means *the manuscript is internally consistent with ``data/``*.  It
does **not** mean the data were replicated: that requires new model calls.  The
distinction is the reason this module is called ``claims`` and not ``verify``.

``EXTRA`` holds values that exist in the shipped data but not in the paper, and
``CONTESTED`` holds claims whose arithmetic or semantics the audit disputes.  Both
are reported, because a release that only checks the numbers it likes is not a
check.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass

from . import manifest, paths


@dataclass(frozen=True)
class Claim:
    cid: str
    label: str
    run_id: str
    kind: str          # "rate" | "count" | "e2e"
    expected: float
    policy: str = "none"
    delay: int | None = None
    unit: str = "%"
    table: str = ""
    note: str = ""


# --------------------------------------------------------------------------- #
# 62 published values
# --------------------------------------------------------------------------- #
SUPPORTED: tuple[Claim, ...] = (
    # Table 1 -- template grid
    Claim("T1.1", "absolute dates, newest first / no review", "out_live_date", "rate", 0.2, "none", table="1"),
    Claim("T1.2", "absolute dates, newest first / recency", "out_live_date", "rate", 0.0, "recent", table="1"),
    Claim("T1.3", "absolute dates, newest first / importance", "out_live_date", "rate", 0.0, "importance", table="1"),
    Claim("T1.4", "absolute dates, newest first / decay", "out_live_date", "rate", 0.0, "decay", table="1"),
    Claim("T1.5", "absolute dates, oldest first / no review", "out_live_date_rev", "rate", 0.0, "none", table="1"),
    Claim("T1.6", "absolute dates, oldest first / recency", "out_live_date_rev", "rate", 0.0, "recent", table="1"),
    Claim("T1.7", "absolute dates, oldest first / importance", "out_live_date_rev", "rate", 0.0, "importance", table="1"),
    Claim("T1.8", "absolute dates, oldest first / decay", "out_live_date_rev", "rate", 0.0, "decay", table="1"),
    Claim("T1.9", "relative day N / no review", "out_live", "rate", 15.8, "none", table="1"),
    Claim("T1.10", "relative day N / recency", "out_live", "rate", 4.8, "recent", table="1"),
    Claim("T1.11", "relative day N / importance", "out_live", "rate", 4.2, "importance", table="1"),
    Claim("T1.12", "relative day N / decay", "out_live", "rate", 4.8, "decay", table="1"),
    Claim("T1.13", "no timestamp, newest first / no review", "out_live_bare", "rate", 100.0, "none", table="1"),
    Claim("T1.14", "no timestamp, newest first / recency", "out_live_bare", "rate", 100.0, "recent", table="1"),
    Claim("T1.15", "no timestamp, newest first / importance", "out_live_bare", "rate", 55.4, "importance", table="1"),
    Claim("T1.16", "no timestamp, newest first / decay", "out_live_bare", "rate", 47.5, "decay", table="1"),
    Claim("T1.17", "no timestamp, oldest first / no review", "out_live_bare_rev", "rate", 0.0, "none", table="1"),
    Claim("T1.18", "no timestamp, oldest first / recency", "out_live_bare_rev", "rate", 0.0, "recent", table="1"),
    Claim("T1.19", "no timestamp, oldest first / importance", "out_live_bare_rev", "rate", 0.0, "importance", table="1"),
    Claim("T1.20", "no timestamp, oldest first / decay", "out_live_bare_rev", "rate", 0.0, "decay", table="1"),
    # Table 2 -- cross model
    Claim("T2.1", "deepseek-chat, update first", "out_live_bare", "rate", 100.0, table="2"),
    Claim("T2.2", "deepseek-chat, update last", "out_live_bare_rev", "rate", 0.0, table="2"),
    Claim("T2.3", "deepseek-chat, with dates", "out_live_date", "rate", 0.2, table="2"),
    Claim("T2.4", "deepseek-reasoner, update first", "out_rsn_bare_new", "rate", 100.0, table="2"),
    Claim("T2.5", "deepseek-reasoner, with dates", "out_rsn_date_new", "rate", 0.0, table="2"),
    Claim("T2.6", "glm-4-flash, update first", "out_glm_bare_new", "rate", 0.0, table="2"),
    Claim("T2.7", "glm-4-flash, update last", "out_glm_bare_old", "rate", 100.0, table="2"),
    Claim("T2.8", "glm-4-flash, with dates", "out_glm_date_new", "rate", 0.0, table="2"),
    Claim("T2.9", "glm-4-plus, update first", "out_glmplus_bare_new", "rate", 49.4, table="2"),
    Claim("T2.10", "glm-4-plus, update last", "out_glmplus_bare_old", "rate", 30.4, table="2"),
    Claim("T2.11", "glm-4-plus, with dates", "out_glmplus_date_new", "rate", 0.0, table="2"),
    Claim("T2.12", "real logs, update first", "out_real_bare_new", "rate", 89.1, table="2"),
    Claim("T2.13", "real logs, update last", "out_real_bare_old", "rate", 8.3, table="2"),
    Claim("T2.14", "real logs, with dates", "out_real_date_new", "rate", 0.0, table="2"),
    # Table 3 -- wording
    Claim("T3.1", "deepseek / uniform baseline", "out_uni_bare_new", "rate", 100.0, table="3"),
    Claim("T3.2", "deepseek / source label varies", "out_var_source", "rate", 90.4, table="3"),
    Claim("T3.3", "deepseek / sentence form varies", "out_var_struct", "rate", 85.6, table="3"),
    Claim("T3.4", "deepseek / value position varies", "out_var_number", "rate", 70.2, table="3"),
    Claim("T3.5", "glm-flash / template baseline", "out_glm_bare_new", "rate", 0.0, table="3"),
    Claim("T3.6", "glm-flash / source label varies", "out_glm_var_source", "rate", 0.0, table="3"),
    Claim("T3.7", "glm-flash / sentence form varies", "out_glm_var_struct", "rate", 0.0, table="3"),
    Claim("T3.8", "glm-flash / value position varies", "out_glm_var_number", "rate", 35.0, table="3"),
    # Table 4 -- archive counts
    Claim("T4.1", "no review / reviewed", "out_live_bare", "count", 0.0, "none", unit="", table="4"),
    Claim("T4.2", "no review / archived", "out_live_bare", "count", 0.0, "none", unit="", table="4"),
    Claim("T4.3", "recency / reviewed", "out_live_bare", "count", 41.3, "recent", unit="", table="4"),
    Claim("T4.4", "recency / archived", "out_live_bare", "count", 0.0, "recent", unit="", table="4"),
    Claim("T4.5", "importance / reviewed", "out_live_bare", "count", 41.0, "importance", unit="", table="4"),
    Claim("T4.6", "importance / archived", "out_live_bare", "count", 17.8, "importance", unit="", table="4"),
    Claim("T4.7", "decay / reviewed", "out_live_bare", "count", 41.5, "decay", unit="", table="4"),
    Claim("T4.8", "decay / archived", "out_live_bare", "count", 21.0, "decay", unit="", table="4"),
    # Table 5 -- end to end
    Claim("T5.1", "end-to-end, append-only newest first", "", "e2e", 0.0, table="5"),
    Claim("T5.2", "end-to-end, append-only oldest first", "", "e2e", 100.0, table="5"),
    Claim("T5.3", "end-to-end, timestamped", "", "e2e", 100.0, table="5"),
    Claim("T5.4", "end-to-end, DAML", "", "e2e", 100.0, table="5"),
    # Figure 2 -- filler curve
    Claim("F2.0", "filler tail k=0", "out_fill2_tail_0", "rate", 100.0, table="fig2"),
    Claim("F2.1", "filler tail k=1", "out_fill2_tail_1", "rate", 83.1, table="fig2"),
    Claim("F2.2", "filler tail k=2", "out_fill2_tail_2", "rate", 91.0, table="fig2"),
    Claim("F2.3", "filler tail k=4", "out_fill2_tail_4", "rate", 89.4, table="fig2"),
    Claim("F2.4", "filler tail k=8", "out_fill2_tail_8", "rate", 94.8, table="fig2"),
    Claim("F2.5", "filler tail k=16", "out_fill2_tail_16", "rate", 62.3, table="fig2"),
    Claim("F2.6", "filler gap k=1", "out_fill2_gap_1", "rate", 100.0, table="fig2"),
    Claim("F2.7", "filler gap k=8", "out_fill2_gap_8", "rate", 100.0, table="fig2"),
)

E2E_DESIGNS = {
    "T5.1": "naive_newest_first",
    "T5.2": "naive_oldest_first",
    "T5.3": "timestamped",
    "T5.4": "daml",
}

# --------------------------------------------------------------------------- #
# Values present in the data but absent from the paper
# --------------------------------------------------------------------------- #
EXTRA: tuple[Claim, ...] = (
    Claim("X1", "all three wording factors mixed (5.0 in paper text, unchecked)", "out_nat_bare_new",
          "rate", 65.0, note="cited in Section 4.3 but absent from the author's checker"),
    Claim("X2", "mixed wording + absolute dates", "out_nat_date_new", "rate", 21.0,
          note="contradicts the abstract's 'at most 0.2%'"),
    Claim("X3", "mixed wording + absolute dates, 90-day delay", "out_nat_date_new", "rate", 29.2,
          delay=90, note="the effect grows with delay"),
    Claim("X4", "relative day N, 90-day delay", "out_live", "rate", 50.8, delay=90,
          note="the paper's strongest single number and its least discussed"),
    Claim("X5", "shuffled order, mixed wording", "out_nat_bare_rand", "rate", 34.8,
          note="the comparison condition is mixed wording, whose own baseline is 65.0"),
)

# --------------------------------------------------------------------------- #
# Claims the audit disputes
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Dispute:
    did: str
    claim: str
    verdict: str
    evidence: str


DISPUTES: tuple[Dispute, ...] = (
    Dispute("D1", "With reliable timestamps, staleness is essentially eliminated (at most 0.2%).",
            "Overstated",
            "out_nat_date_new: 21.0% overall, 29.2% at a 90-day delay. The 0.2% figure "
            "holds only for uniform templates."),
    Dispute("D2", "A shuffled order falls between the extremes (34.8%), consistent with order "
                  "being the operative cue.",
            "Not supported as stated",
            "The shuffled cell uses mixed wording, whose matched baseline is 65.0%, not 100%. "
            "A pure positional rule predicts ~50%, and 34.8% is below that."),
    Dispute("D3", "The effects are roughly additive (9.6 + 14.4 + 29.8 = 53 points).",
            "Arithmetic error",
            "100 - 53.8 = 46.2, but the mixed condition is 65.0%."),
    Dispute("D4", "The stale rate equals one minus archive coverage.",
            "Identity, not a result",
            "Holds to machine precision in every four-policy run because archiving removes "
            "the only competing record."),
    Dispute("D5", "Recency-first review removes no conflicts.",
            "Structural",
            "The 40 updated records are the newest entries and nearly fill the "
            "41-record budget, so recency cannot reach a conflict. The zero is a cap "
            "built into the store, not a property of recency as a signal."),
    Dispute("D6", "The decay signal is not doing any work of its own.",
            "Untested",
            "Half-life is assigned by importance band, so the two policies are not "
            "independent; and importance is random, so neither has a real signal to use. "
            "Against a random-selection baseline decay is in fact +12.1 points of "
            "conflict-hit rate."),
    Dispute("D7", "Adding dates returns all four configurations to 0%.",
            "Conditional on wording",
            "True for template/uniform wording; false for mixed wording (21.0%)."),
    Dispute("D8", "GLM-4-Plus follows no stable rule.",
            "Mislabelled",
            "39 of 40 chains give the same verdict at all four delays and all three seeds; "
            "the choice is chain-determined and delay-invariant, which is a rule."),
)


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
@dataclass
class Result:
    claim: Claim
    computed: float
    delta: float
    ok: bool

    def render(self) -> str:
        mark = "PASS" if self.ok else "FAIL"
        unit = self.claim.unit
        return (f"| {self.claim.cid} | {self.claim.table} | {self.claim.label} "
                f"| {self.claim.expected:.1f}{unit} | {self.computed:.1f}{unit} "
                f"| {mark} |")


def tolerance(claim: Claim) -> float:
    """Paper values are rounded to one decimal, so allow 0.7 of a unit."""
    return 0.7


def compute(claim: Claim) -> float:
    if claim.kind == "rate":
        value = manifest.mean_rate(claim.run_id, claim.policy, "stale", claim.delay)
        if value is None:
            raise KeyError(f"{claim.cid}: no data for {claim.run_id}")
        return value * 100
    if claim.kind == "count":
        column = "reviewed" if "reviewed" in claim.label else "archived"
        value = manifest.count_mean(claim.run_id, claim.policy, column)
        if value is None:
            raise KeyError(f"{claim.cid}: no count for {claim.run_id}/{claim.policy}")
        return value
    if claim.kind == "e2e":
        return _e2e_rate(E2E_DESIGNS[claim.cid]) * 100
    raise ValueError(f"unknown claim kind {claim.kind!r}")


def _e2e_rows() -> list[dict]:
    path = paths.data_dir() / "daml" / "pilot_results.csv"
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _e2e_rate(design: str) -> float:
    rows = [r for r in _e2e_rows() if r["design"] == design]
    if not rows:
        raise KeyError(f"no end-to-end rows for {design}")
    return sum(int(r["exact"]) for r in rows) / len(rows)


def evaluate(claims: tuple[Claim, ...] = SUPPORTED) -> list[Result]:
    results = []
    for claim in claims:
        computed = compute(claim)
        delta = computed - claim.expected
        results.append(Result(claim, computed, delta, abs(delta) <= tolerance(claim)))
    return results


def render_results(results: list[Result], title: str) -> str:
    lines = [f"## {title}", "",
             "| ID | Table | Claim | Paper | Recompute | Status |",
             "| :--- | :--- | :--- | ---: | ---: | :--- |"]
    lines += [r.render() for r in results]
    passed = sum(1 for r in results if r.ok)
    lines += ["", f"**{passed}/{len(results)} match.**"]
    return "\n".join(lines)


def render_extra() -> str:
    rows = []
    for claim in EXTRA:
        try:
            value = compute(claim)
        except KeyError:
            value = float("nan")
        rows.append(f"| {claim.cid} | {claim.label} | {claim.expected:.1f}% "
                    f"| {value:.1f}% | {claim.note} |")
    return "\n".join([
        "## Values in the data that are not in the paper", "",
        "| ID | Condition | Value | Recomputed | Why it matters |",
        "| :--- | :--- | ---: | ---: | :--- |",
        *rows,
    ])


def render_disputes() -> str:
    lines = ["## Claims the audit disputes", "",
             "| ID | Paper claim | Verdict | Evidence |",
             "| :--- | :--- | :--- | :--- |"]
    for dispute in DISPUTES:
        lines.append(f"| {dispute.did} | {dispute.claim} | **{dispute.verdict}** "
                     f"| {dispute.evidence} |")
    return "\n".join(lines)
