"""Table builders.

Every table in the paper is reconstructed here from ``data/runs``.  Nothing is
hard-coded: the numbers come from the shipped condition files, so a table that
disagrees with the paper is a real disagreement rather than a stale constant.

The builders also emit the quantities the paper's tables omit:

* exact binomial intervals, so a cell of 480/480 is not reported as if it were
  known without error;
* the independent unit (40 chains, not 480 queries), because the same chain is
  measured at 4 delays x 3 seeds and returns the same verdict each time;
* the conflict-hit rate and its random-selection reference, which is the only way
  to tell a good selection function from a lucky one.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .. import manifest
from ..manifest import RunSpec
from ..policies import POLICIES, POLICY_INFO, random_selection_hit_rate
from ..stats import clopper_pearson, pooled_rate


# --------------------------------------------------------------------------- #
# markdown helpers
# --------------------------------------------------------------------------- #
def md_table(headers: Iterable[str], rows: Iterable[Iterable[object]],
             align: str | None = None) -> str:
    headers = list(headers)
    rows = [[("" if cell is None else str(cell)) for cell in row] for row in rows]
    align = align or ("l" + "r" * (len(headers) - 1))
    sep = {"l": ":---", "r": "---:", "c": ":---:"}
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join(sep[a] for a in align) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def fmt_pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.{digits}f}"


def fmt_ci(lo: float, hi: float, digits: int = 1) -> str:
    return f"[{lo * 100:.{digits}f}, {hi * 100:.{digits}f}]"


@dataclass(frozen=True)
class Cell:
    """One reported proportion with its two honest intervals."""

    run_id: str
    policy: str
    delay: int | None
    mean: float
    k_probes: int
    n_probes: int
    k_chains: int
    n_chains: int

    @property
    def probe_ci(self) -> tuple[float, float]:
        return clopper_pearson(self.k_probes, self.n_probes)

    @property
    def chain_ci(self) -> tuple[float, float]:
        return clopper_pearson(self.k_chains, self.n_chains)

    #: Figures use the chain-level interval, because the chain is the independent unit.
    @property
    def lo(self) -> float:
        return self.chain_ci[0]

    @property
    def hi(self) -> float:
        return self.chain_ci[1]

    @property
    def label(self) -> str:
        return f"{fmt_pct(self.mean)} ({self.k_chains}/{self.n_chains} chains)"


def cell(run_id: str, policy: str, delay: int | None = None) -> Cell:
    """Pool a run's batches into a single proportion with exact intervals.

    Both denominators are reported: the probes actually issued, and the chains that
    actually vary.  When the verdict is constant across delays and seeds (the normal
    case here) ``k_chains`` is just ``round(mean * n_chains)``, because each chain
    contributes the same verdict at every repeat.
    """
    spec = manifest.load_runs()[run_id]
    rates = manifest.batch_rates(run_id, policy, "stale", delay)
    if not rates:
        raise KeyError(f"no rows for {run_id}/{policy}/delay={delay}")
    k, n = pooled_rate(rates, spec.chains)
    mean = k / n
    k_chains = min(spec.chains, max(0, round(mean * spec.chains)))
    return Cell(run_id, policy, delay, mean, k, n, k_chains, spec.chains)


def rate(run_id: str, policy: str = "none", delay: int | None = None) -> float:
    return cell(run_id, policy, delay).mean


# --------------------------------------------------------------------------- #
# Table 1 -- the template grid
# --------------------------------------------------------------------------- #
TABLE1_ROWS: tuple[tuple[str, str], ...] = (
    ("Absolute dates, newest first", "out_live_date"),
    ("Absolute dates, oldest first", "out_live_date_rev"),
    ("Relative notation (“day N”)", "out_live"),
    ("No timestamp, newest first", "out_live_bare"),
    ("No timestamp, oldest first", "out_live_bare_rev"),
)


def table1() -> str:
    """Stale rate (%) on the template corpus, deepseek-chat, 40 chains."""
    headers = ["Condition"] + [f"{POLICY_INFO[p]['name_en']}" for p in POLICIES]
    rows = []
    for label, run_id in TABLE1_ROWS:
        row = [label]
        for policy in POLICIES:
            spec = manifest.load_runs()[run_id]
            if policy not in ("none",) and spec.policies == "none":
                row.append("—")
                continue
            row.append(fmt_pct(maybe_rate(run_id, policy)))
        rows.append(row)
    return md_table(headers, rows)


def maybe_rate(run_id: str, policy: str, delay: int | None = None) -> float | None:
    try:
        return rate(run_id, policy, delay)
    except KeyError:
        return None


def table1_uncertainty() -> str:
    """The no-review column again, with both intervals made explicit."""
    headers = ["Condition", "Stale (%)", "Probes", "95% CI over probes",
               "95% CI over chains"]
    rows = []
    for label, run_id in TABLE1_ROWS:
        c = cell(run_id, "none")
        rows.append([label, fmt_pct(c.mean), f"{c.k_probes}/{c.n_probes}",
                     fmt_ci(*c.probe_ci), fmt_ci(*c.chain_ci)])
    note = (
        "The probe interval treats each of the 480 queries as independent; the chain "
        "interval treats the 40 chains as the unit. The chain interval is the honest "
        "one, because a chain returns the same verdict at all four delays and all "
        "three seeds (see `AUDIT.md` section 3). Read the two columns together: a cell "
        "of 0.2% from one probe is compatible with anything from zero to three of the "
        "forty chains."
    )
    return md_table(headers, rows) + "\n\n" + note


# --------------------------------------------------------------------------- #
# Table 2 -- cross-model
# --------------------------------------------------------------------------- #
TABLE2_ROWS: tuple[tuple[str, str | None, str | None, str | None], ...] = (
    ("deepseek-chat", "out_live_bare", "out_live_bare_rev", "out_live_date"),
    ("deepseek-reasoner", "out_rsn_bare_new", None, "out_rsn_date_new"),
    ("glm-4-flash", "out_glm_bare_new", "out_glm_bare_old", "out_glm_date_new"),
    ("glm-4-plus", "out_glmplus_bare_new", "out_glmplus_bare_old", "out_glmplus_date_new"),
    ("deepseek-chat, real logs", "out_real_bare_new", "out_real_bare_old", "out_real_date_new"),
)


def table2() -> str:
    headers = ["Model / corpus", "Update first", "Update last", "With dates"]
    rows = []
    for label, first, last, dated in TABLE2_ROWS:
        rows.append([label,
                     _cell_with_n(first),
                     _cell_with_n(last),
                     _cell_with_n(dated)])
    return md_table(headers, rows)


def _cell_with_n(run_id: str | None) -> str:
    if run_id is None:
        return "not run"
    c = cell(run_id, "none")
    return f"{fmt_pct(c.mean)} ({c.k_chains}/{c.n_chains})"


# --------------------------------------------------------------------------- #
# Table 3 -- wording decomposition
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class WordingRow:
    label: str
    deepseek_run: str | None
    glm_run: str | None
    in_paper: bool = True


TABLE3_ROWS: tuple[WordingRow, ...] = (
    WordingRow("Uniform template (baseline)", "out_uni_bare_new", "out_glm_bare_new"),
    WordingRow("Only the source label varies", "out_var_source", "out_glm_var_source"),
    WordingRow("Only the sentence form varies", "out_var_struct", "out_glm_var_struct"),
    WordingRow("Only the value position varies", "out_var_number", "out_glm_var_number"),
    WordingRow("All three mixed", "out_nat_bare_new", None),
    WordingRow("All three mixed + dates", "out_nat_date_new", None, in_paper=False),
)


def table3() -> str:
    headers = ["Wording variant", "deepseek-chat", "glm-4-flash", "In paper"]
    rows = []
    for row in TABLE3_ROWS:
        rows.append([
            row.label,
            _cell_with_n(row.deepseek_run),
            _cell_with_n(row.glm_run) if row.glm_run else "not run",
            "yes" if row.in_paper else "**no**",
        ])
    return md_table(headers, rows)


def table_interaction() -> str:
    """The 2x2 the paper needs: wording uniformity x timestamp presence."""
    headers = ["Wording", "No timestamp", "Absolute dates", "Effect of dates"]
    combos = [
        ("Uniform template", "out_uni_bare_new", "out_uni_date_new"),
        ("Mixed natural sentences", "out_nat_bare_new", "out_nat_date_new"),
    ]
    rows = []
    for label, bare_run, date_run in combos:
        bare, dated = rate(bare_run), rate(date_run)
        rows.append([label, fmt_pct(bare), fmt_pct(dated),
                     f"{fmt_pct(bare - dated)} pt"])
    return md_table(headers, rows)


# --------------------------------------------------------------------------- #
# Table 4 -- archive accounting
# --------------------------------------------------------------------------- #
def table4(run_id: str = "out_live_bare") -> str:
    spec = manifest.load_runs()[run_id]
    random_hit = random_selection_hit_rate(spec.chains)
    headers = ["Policy", "Reviewed", "Archived", "Coverage", "Stale rate",
               "Conflict-hit rate", "Random reference"]
    rows = []
    for policy in POLICIES:
        reviewed = manifest.count_mean(run_id, policy, "reviewed") or 0.0
        archived = manifest.count_mean(run_id, policy, "archived") or 0.0
        coverage = archived / spec.chains
        hit = archived / reviewed if reviewed else 0.0
        rows.append([
            POLICY_INFO[policy]["name_en"],
            f"{reviewed:.1f}",
            f"{archived:.1f}",
            fmt_pct(coverage),
            fmt_pct(rate(run_id, policy)),
            fmt_pct(hit) if reviewed else "—",
            fmt_pct(random_hit) if policy != "none" else "—",
        ])
    return md_table(headers, rows)


# --------------------------------------------------------------------------- #
# Table 5 -- end to end
# --------------------------------------------------------------------------- #
def table5() -> str:
    import csv

    from .. import paths

    path = paths.data_dir() / "daml" / "pilot_results.csv"
    with path.open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    designs = ["naive_newest_first", "naive_oldest_first", "timestamped", "daml"]
    headers = ["Design", "Exact", "95% CI", "Field acc.", "Stale fields"]
    out = []
    for design in designs:
        subset = [r for r in rows if r["design"] == design]
        n = len(subset)
        exact = sum(int(r["exact"]) for r in subset)
        fields_ok = sum(int(r["correct_fields"]) for r in subset)
        fields_stale = sum(int(r["stale_fields"]) for r in subset)
        lo, hi = clopper_pearson(exact, n)
        out.append([
            design, f"{exact / n * 100:.1f} ({exact}/{n})", fmt_ci(lo, hi),
            f"{fields_ok / (n * 10) * 100:.1f}", f"{fields_stale / (n * 10) * 100:.1f}",
        ])
    return md_table(headers, out)


# --------------------------------------------------------------------------- #
# Manifest overview
# --------------------------------------------------------------------------- #
def inventory() -> str:
    runs = manifest.load_runs()
    headers = ["Run", "Model", "Chains", "Seeds", "Time", "Order", "Style",
               "Policies", "Probes"]
    rows = []
    for run_id, spec in runs.items():
        rows.append([run_id, spec.model, spec.chains, spec.seeds, spec.time_format,
                     spec.ctx_order, spec.text_style, spec.policies, spec.probes])
    return md_table(headers, rows)


def all_tables() -> dict[str, str]:
    return {
        "table1_main_grid": table1(),
        "table1_uncertainty": table1_uncertainty(),
        "table2_cross_model": table2(),
        "table3_wording": table3(),
        "table_missing_interaction": table_interaction(),
        "table4_archive": table4(),
        "table5_end_to_end": table5(),
        "table_proposed_controls": table_proposed_controls(),
    }


# --------------------------------------------------------------------------- #
# The controls the roadmap proposes -- computed from the design, no model calls
# --------------------------------------------------------------------------- #
def _simulate_coverage(policy: str, chains: int = 40, seeds: int = 3,
                       delays: tuple[int, ...] = (1, 7, 30, 90),
                       **store_kwargs) -> tuple[float, float]:
    """Mean reviewed/archived counts over the same grid the shipped runs used.

    Review is deterministic, so archive coverage can be computed without calling a
    model at all.  That is the point of the proposed controls: the decisive numbers
    cost nothing to obtain.
    """
    import random

    from ..policies import apply_review, review_budget, select_review
    from ..prompts import RenderCfg
    from ..store import build_store

    cfg = RenderCfg("none", "template")
    reviewed: list[int] = []
    archived: list[int] = []
    for delay in delays:
        for seed in range(seeds):
            store = build_store(seed, chains, delay, **store_kwargs)
            budget = review_budget(store, cfg)
            rng = random.Random(f"{seed}-{delay}-{policy}")
            picked = select_review(store, budget, policy, cfg, rng=rng)
            reviewed.append(len(picked))
            archived.append(apply_review(picked))
    return sum(reviewed) / len(reviewed), sum(archived) / len(archived)


def table_proposed_controls() -> str:
    """Coverage and conflict-hit rate for the controls proposed in the roadmap.

    These are properties of the review design, not measurements of any model, and they
    are therefore exact up to the seed schedule.  They exist to show the experiments are
    worth running before anyone spends an API budget on them.
    """
    random_hit = random_selection_hit_rate(40)
    scenarios = [
        ("Shipped: no review", "none", {}),
        ("Shipped: recency", "recent", {}),
        ("Shipped: importance", "importance", {}),
        ("Shipped: decay", "decay", {}),
        ("Proposed: random (E1)", "random", {}),
        ("Proposed: recency, 25% late writes (E2)", "recent", {"late_duplicates": 0.25}),
        ("Proposed: recency, 50% late writes (E2)", "recent", {"late_duplicates": 0.50}),
    ]
    for rho in (0.0, 0.25, 0.5, 0.75, 1.0):
        scenarios.append((
            f"Proposed: importance, signal {rho:.2f} (E3)",
            "importance",
            {"importance_mode": "signal", "importance_signal": rho},
        ))

    headers = ["Scenario", "Reviewed", "Archived", "Coverage", "Conflict-hit rate",
               "vs random"]
    rows = []
    for label, policy, kwargs in scenarios:
        reviewed, archived = _simulate_coverage(policy, **kwargs)
        coverage = archived / 40
        hit = archived / reviewed if reviewed else 0.0
        delta = "—" if policy == "none" else f"{(hit - random_hit) * 100:+.1f} pt"
        rows.append([label, f"{reviewed:.1f}", f"{archived:.1f}", fmt_pct(coverage),
                     fmt_pct(hit) if reviewed else "—", delta])
    note = (
        "Every number above is computed from the review design alone; no model is "
        "called, because archiving is deterministic. The `random` row is the baseline "
        f"the paper lacks, and its theoretical hit rate is {random_hit * 100:.1f}% "
        "(40 superseded records among 104). The last five rows separate an importance "
        "*policy* from an importance *signal*: coverage rises with the correlation "
        "between importance and supersession, which is the only channel through which "
        "importance can help."
    )
    return md_table(headers, rows) + "\n\n" + note


def describe(spec: RunSpec) -> str:
    return (f"{spec.run_id}: {spec.model}, {spec.chains} chains, "
            f"{spec.time_format}/{spec.ctx_order}/{spec.text_style}")
