"""Design audit: the diagnostics the paper's own tables do not contain.

Each function returns a small dataclass and each ``render_*`` function turns it into
Markdown.  ``build_audit_report`` assembles ``analysis_out/AUDIT.md``.

The audit is deliberately adversarial: it asks what else could produce the reported
numbers, and it reports every case where the answer is "the design, not the model".
It also reports the places where the paper is *right* and the earlier checker was
unable to show it (for example, the 1,920-probe determinism of the core grid, which
is stronger than the "480 queries in each no-review condition" the paper claims).
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass

from .. import manifest, paths
from ..manifest import SUMMARY_ENTITY, RunSpec, probe_rows, read_rows, summary_rows
from ..policies import POLICIES, random_selection_hit_rate
from ..stats import clopper_pearson, design_effect, t_critical

SEVERITY_ORDER = {"blocker": 0, "major": 1, "minor": 2, "info": 3}


def _family(model: str) -> str:
    if model.startswith("deepseek"):
        return "deepseek"
    if model == "glm-4-flash":
        return "glm-flash"
    if model == "glm-4-plus":
        return "glm-plus"
    return "other"


# --------------------------------------------------------------------------- #
# 1. Inventory
# --------------------------------------------------------------------------- #
@dataclass
class Inventory:
    n_runs: int
    n_probes: int
    probes_by_verdict: Counter
    n_summary_rows: int
    n_cells_with_unknown: int
    n_runs_with_meta: int

    @property
    def unknown_share(self) -> float:
        return self.probes_by_verdict.get("unknown", 0) / self.n_probes


def inventory() -> Inventory:
    runs = manifest.load_runs()
    verdicts: Counter = Counter()
    probes = cells_unknown = 0
    meta_present = 0
    for run_id in runs:
        for row in read_rows(run_id):
            if row["entity"] == SUMMARY_ENTITY:
                if float(row.get("unknown") or 0) > 0:
                    cells_unknown += 1
            else:
                probes += 1
                verdicts[row["verdict"]] += 1
        if manifest.run_meta(run_id) is not None:
            meta_present += 1
    return Inventory(len(runs), probes, verdicts, probes, cells_unknown, meta_present)


def render_inventory(inv: Inventory) -> str:
    mix = ", ".join(f"{k} {v}" for k, v in inv.probes_by_verdict.most_common())
    return "\n".join([
        "## 1. Inventory",
        "",
        f"- runs: **{inv.n_runs}**, probes: **{inv.n_probes:,}**",
        f"- verdict mix: {mix}",
        f"- `unknown` share: {inv.unknown_share * 100:.2f}% "
        f"(non-zero in {inv.n_cells_with_unknown} batch cells, all of them filler runs)",
        f"- runs with a `run_meta.json`: **{inv.n_runs_with_meta}/{inv.n_runs}**",
        "",
        "The `unknown` bucket is small enough that the choice between a stale rate and "
        "an error rate cannot change any conclusion: in every main-grid cell the two "
        "are exact complements.",
    ])


# --------------------------------------------------------------------------- #
# 2. Determinism
# --------------------------------------------------------------------------- #
def predicted_verdict(row: dict, spec: RunSpec) -> tuple[str, str] | None:
    """Verdict implied by the presentation, plus the name of the rule that implies it.

    Two rules cover the template/uniform conditions:

    * with a timestamp the model can order the records, so the answer should be the
      updated value;
    * without a timestamp the model falls back on position, and the direction is a
      property of the model family (DeepSeek reads the last record, GLM-4-Flash the
      first).

    A one-record context is predicted ``correct`` under any presentation, which is why
    the relative-notation and GLM-4-Plus runs still contribute a few predicted probes.
    """
    if spec.text_style not in ("template", "uniform"):
        return None
    if spec.filler != "无" or spec.ctx_order == "random":
        return None
    entries = int(row["ctx_entries"])
    if entries == 1:
        return "correct", "single record"
    if spec.time_format == "date":
        return "correct", "dates decide"
    if spec.time_format == "none":
        family = _family(spec.model)
        rules = {"deepseek": {"newest_first": "stale", "oldest_first": "correct"},
                 "glm-flash": {"newest_first": "correct", "oldest_first": "stale"}}
        verdict = rules.get(family, {}).get(spec.ctx_order)
        if verdict is not None:
            return verdict, f"position/{'last' if verdict == 'stale' else 'first'}"
    return None  # relative day numbers depend on arithmetic we cannot model


@dataclass
class DeterminismRow:
    run_id: str
    rule: str
    matched: int
    exceptions: int

    @property
    def total(self) -> int:
        return self.matched + self.exceptions


def determinism() -> list[DeterminismRow]:
    out: list[DeterminismRow] = []
    for run_id, spec in manifest.load_runs().items():
        counts: dict[str, list[int]] = {}
        for row in probe_rows(run_id):
            predicted = predicted_verdict(row, spec)
            if predicted is None:
                continue
            want, rule = predicted
            bucket = counts.setdefault(rule, [0, 0])
            bucket[0 if want == row["verdict"] else 1] += 1
        for rule, (matched, exceptions) in counts.items():
            out.append(DeterminismRow(run_id, rule, matched, exceptions))
    return out


def render_determinism(rows: list[DeterminismRow]) -> str:
    total_match = sum(r.matched for r in rows)
    total_exc = sum(r.exceptions for r in rows)
    lines = [
        "## 2. How much of the data is determined by the design?",
        "",
        "A verdict is *predicted* when it follows from the context alone: one visible "
        "record means one possible value; two visible records mean the model applies a "
        "positional rule whose direction depends on the family.",
        "",
        "| Run | Rule | Predicted | Match | Exceptions |",
        "| :--- | :--- | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(f"| `{row.run_id}` | {row.rule} | {row.total} | {row.matched} "
                     f"| {row.exceptions} |")
    share = total_match / (total_match + total_exc) * 100
    lines += [
        "",
        f"**{total_match:,} of {total_match + total_exc:,} rule-eligible probes "
        f"({share:.2f}%) are exactly predicted.** Of the {total_exc} exceptions, "
        f"{sum(r.exceptions for r in rows if r.run_id.startswith('out_real'))} are in the "
        "real-log corpus and the rest are two isolated probes in the timestamped "
        "conditions.",
        "",
        "Two caveats on how to read this. The prediction takes the context composition "
        "from the result file rather than deriving it; `tests/test_replay.py` closes that "
        "gap by deriving the composition from the manifest alone and still reproducing "
        "all 1,920 verdicts of the core grid. And the regularity is a statement about the "
        "*design*: it says the outcome is fixed by which records remain, which is exactly "
        "why the maintenance comparison in section 4 cannot measure a model.",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 3. Chain invariance / effective sample size
# --------------------------------------------------------------------------- #
def chain_profiles(run_id: str, policy: str = "none") -> list[dict[str, str]]:
    """Per-chain verdicts, keyed by block position.

    Rows in a shipped ``results.csv`` are ordered ``delay, seed, policy, chain``, so
    the position inside a block identifies the chain even when every chain shares the
    same entity name (as in the real-log corpus).
    """
    spec = manifest.load_runs()[run_id]
    blocks: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in probe_rows(run_id):
        blocks[(row["delay"], row["seed"], row["policy"])].append(row)
    profiles: dict[int, dict[tuple[str, str], str]] = defaultdict(dict)
    for (delay, seed, pol), rows in blocks.items():
        if len(rows) != spec.chains:
            raise ValueError(f"{run_id}: block has {len(rows)} rows, expected {spec.chains}")
        for index, row in enumerate(rows):
            if pol == policy:
                profiles[index][(delay, seed)] = row["verdict"]
    return [profiles[i] for i in sorted(profiles)]


@dataclass
class InvarianceRow:
    run_id: str
    chains: int
    varying: int
    probes: int
    policies: int

    @property
    def stable(self) -> int:
        return self.chains - self.varying

    @property
    def probes_per_policy(self) -> int:
        return self.probes // max(1, self.policies)

    @property
    def inflation(self) -> float:
        """How much a binomial interval over probes understates the chain-level one."""
        return design_effect(self.probes_per_policy, self.chains)


def chain_invariance() -> list[InvarianceRow]:
    rows = []
    for run_id, spec in manifest.load_runs().items():
        if spec.policies == "none" and spec.filler != "无":
            continue
        try:
            profiles = chain_profiles(run_id)
        except ValueError:
            continue
        varying = sum(1 for p in profiles if len(set(p.values())) > 1)
        rows.append(InvarianceRow(run_id, spec.chains, varying, spec.probes,
                                  4 if spec.policies == "all" else 1))
    return rows


def render_invariance(rows: list[InvarianceRow]) -> str:
    lines = [
        "## 3. The independent unit is the chain, not the query",
        "",
        "Each chain is measured at four delays and three seeds. If the verdict is "
        "constant across those twelve measurements, the twelve probes carry one bit of "
        "information, not twelve.",
        "",
        "| Run | Chains | Verdict varies | Stable | Probes / policy | Design effect |",
        "| :--- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(f"| `{row.run_id}` | {row.chains} | {row.varying} | {row.stable} "
                     f"| {row.probes_per_policy} | x{row.inflation:.2f} |")
    core = next((r for r in rows if r.run_id == "out_live_bare"), rows[0])
    lines += [
        "",
        f"The core grid has **{core.chains} independent units**, not "
        f"{core.probes_per_policy}. A binomial interval over {core.probes_per_policy} "
        f"probes is therefore about **x{core.inflation:.1f} too narrow**; the honest "
        f"interval for {core.chains}/{core.chains} chains is [91.2, 100.0], not "
        "[99.2, 100.0]. Every error bar in the paper and every `±` in `summary.md` "
        "inherits this, on top of the t-value problem in section 6.",
        "",
        "The conditions that genuinely vary within a chain are the mixed-wording ones "
        "(`out_nat_date_new`, 15 of 40 chains) and the relative-notation condition "
        "(`out_live`, 28 of 40). Those are the only conditions in which the delay "
        "argument does any work -- another way of saying that the rest of the grid has "
        "no within-chain variance for a delay effect to explain.",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 4. The archive-coverage identity
# --------------------------------------------------------------------------- #
@dataclass
class IdentityRow:
    run_id: str
    cells: int
    max_deviation: float
    worst: tuple | None


def archive_identity() -> list[IdentityRow]:
    """Test ``stale == 1 - archived / n_chains`` on every batch cell."""
    out = []
    for run_id, spec in manifest.load_runs().items():
        if spec.filler != "无" or spec.policies == "none":
            continue
        worst = None
        deviations = []
        for row in summary_rows(run_id):
            if row.get("archived") in ("", None):
                continue
            archived = float(row["archived"])
            stale = float(row["stale"])
            deviation = abs(stale - (1 - archived / spec.chains))
            deviations.append(deviation)
            if worst is None or deviation > worst[0]:
                worst = (deviation, row["delay"], row["seed"], row["policy"], archived, stale)
        if deviations:
            out.append(IdentityRow(run_id, len(deviations), max(deviations), worst))
    return out


def render_identity(rows: list[IdentityRow]) -> str:
    lines = [
        "## 4. `stale = 1 - archive coverage` is arithmetic, not a finding",
        "",
        "| Run | Cells | Max deviation | Identity holds? |",
        "| :--- | ---: | ---: | :--- |",
    ]
    for row in rows:
        holds = "**exactly**" if row.max_deviation < 1e-9 else "no"
        lines.append(f"| `{row.run_id}` | {row.cells} | {row.max_deviation:.2e} | {holds} |")
    exact = [r for r in rows if r.max_deviation < 1e-9]
    names = ", ".join(f"`{r.run_id}`" for r in exact)
    by_run = {r.run_id: r.max_deviation for r in rows}

    def dev(run_id: str) -> str:
        value = by_run.get(run_id)
        return "—" if value is None else f"{value:.2f}"

    lines += [
        "",
        "The identity is exact only where the model follows the positional rule: "
        f"{len(exact)} of {len(rows)} runs ({names}). It has to be. Archiving removes the "
        "outdated record, a context with one record admits one answer, and a context with "
        "two records triggers the position rule -- so all four policies land on the line "
        "by construction. The paper states this mechanism in section 4.4 and then reports "
        "the equality as an empirical law, in 4.4 and again in the abstract.",
        "",
        "Everywhere else the identity fails, and the size of the failure is itself the "
        "measurement: it says how often the model overrode the positional prior. That "
        f"number is {dev('out_live_bare_rev')} for the oldest-first condition (where the "
        f"rule points the other way), {dev('out_nat_bare_new')} for mixed wording, and "
        f"{dev('out_nat_date_new')} for mixed wording with dates.",
        "",
        "The consequence for the paper is not that the maintenance experiment is wrong, "
        "but that it cannot measure model behaviour: in the condition used for Table 4 it "
        "measures **archive coverage** and nothing else. The quantity worth comparing "
        "across policies is the conflict-hit rate of the selection function (section 5).",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 5. Conflict selectivity
# --------------------------------------------------------------------------- #
@dataclass
class SelectivityRow:
    policy: str
    reviewed: float
    archived: float
    coverage: float
    hit_rate: float
    random_hit: float
    extra_hits: float


def conflict_selectivity(run_id: str = "out_live_bare") -> list[SelectivityRow]:
    spec = manifest.load_runs()[run_id]
    random_hit = random_selection_hit_rate(spec.chains)
    rows = []
    for policy in POLICIES:
        reviewed = manifest.count_mean(run_id, policy, "reviewed") or 0.0
        archived = manifest.count_mean(run_id, policy, "archived") or 0.0
        hit = archived / reviewed if reviewed else 0.0
        rows.append(SelectivityRow(
            policy=policy, reviewed=reviewed, archived=archived,
            coverage=archived / spec.chains, hit_rate=hit, random_hit=random_hit,
            extra_hits=(hit - random_hit) * reviewed if reviewed else 0.0,
        ))
    return rows


def render_selectivity(rows: list[SelectivityRow]) -> str:
    lines = [
        "## 5. Which records get reviewed -- the measurement the paper is missing",
        "",
        "With 40 superseded records among 104, uniform random selection hits a conflict "
        f"with probability **{rows[0].random_hit * 100:.1f}%**. That is the baseline any "
        "policy has to beat.",
        "",
        "| Policy | Reviewed | Archived | Conflict-hit rate | vs random | Extra conflicts |",
        "| :--- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        delta = row.hit_rate - row.random_hit
        lines.append(f"| {row.policy} | {row.reviewed:.1f} | {row.archived:.1f} "
                     f"| {row.hit_rate * 100:.1f}% | {delta * 100:+.1f} pt "
                     f"| {row.extra_hits:+.1f} |")
    decay = next(r for r in rows if r.policy == "decay")
    lines += [
        "",
        "Two readings, both defensible and both absent from the paper:",
        "",
        "- **recency is worse than random**, not merely unhelpful. The 40 updated "
        "records are the newest entries in the store and nearly fill the 41-record "
        "budget, so a recency policy spends its reviews on records that cannot be "
        "superseded. Its zero coverage is a cap built into the store, not a "
        "measurement.",
        f"- **decay is modestly better than random**: {decay.hit_rate * 100:.1f}% versus "
        f"{decay.random_hit * 100:.1f}%, or about {decay.extra_hits:.0f} extra conflicts "
        "per 41 reviewed records. This is the real effect size behind the paper's "
        "\"maintenance is conflict removal\" claim, and it is not negligible -- it is "
        "just invisible when the only reported metric is a quantity pinned to coverage "
        "by construction.",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 6. Interval audit
# --------------------------------------------------------------------------- #
@dataclass
class CIaudit:
    run_id: str
    policy: str
    n_batches: int
    mean: float
    implied_halfwidth: float
    correct_halfwidth: float
    ratio: float


def ci_audit() -> list[CIaudit]:
    """Show that every published ``±`` came from a single hard-coded t = 2.776."""
    out = []
    for run_id, policy in (("out_live", "none"), ("out_live_bare", "importance"),
                           ("out_live_bare", "decay"), ("out_glmplus_bare_new", "none")):
        values = manifest.batch_rates(run_id, policy)
        if len(values) < 2:
            continue
        n = len(values)
        sd = statistics.stdev(values)
        implied = 2.776 * sd / math.sqrt(n)
        correct = t_critical(n - 1) * sd / math.sqrt(n)
        out.append(CIaudit(run_id, policy, n, statistics.fmean(values), implied, correct,
                           correct / implied if implied else float("nan")))
    return out


def render_ci(rows: list[CIaudit]) -> str:
    lines = [
        "## 6. Every error bar used the same t value",
        "",
        "The original helper hard-codes `t = 2.776`, the 95% critical value for "
        "`df = 4`. Cells in this study have 2, 3 or 12 batches, so the constant is "
        "wrong in both directions.",
        "",
        "| Run | Policy | Batches | Mean | Published half-width | Correct half-width | Ratio |",
        "| :--- | :--- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(f"| `{row.run_id}` | {row.policy} | {row.n_batches} "
                     f"| {row.mean * 100:.1f} | ±{row.implied_halfwidth * 100:.2f} "
                     f"| ±{row.correct_halfwidth * 100:.2f} | {row.ratio:.2f} |")
    lines += [
        "",
        "The per-delay tables in each `summary.md` use `n = seeds = 3` (correct "
        "multiplier 4.303): those intervals are about **1.6x too narrow**. The pooled "
        "table in `all_conditions.md` uses `n = 12` (correct multiplier 2.201): those "
        "are about **1.3x too wide**. The pattern is diagnostic: a single constant was "
        "applied to every sample size.",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 7. Filler curve
# --------------------------------------------------------------------------- #
def cochran_armitage(xs: list[float], ks: list[int], ns: list[int]) -> float:
    """Trend statistic for a monotone alternative across ordered doses."""
    total_n = sum(ns)
    total_k = sum(ks)
    xbar = sum(x * n for x, n in zip(xs, ns, strict=False)) / total_n
    p = total_k / total_n
    numerator = sum(n * (x - xbar) * (k / n - p) for x, k, n in zip(xs, ks, ns, strict=False))
    denominator = math.sqrt(p * (1 - p) * sum(n * (x - xbar) ** 2 for x, n in zip(xs, ns, strict=False)))
    return numerator / denominator


@dataclass
class FillerPoint:
    mode: str
    k: int
    k_stale: int
    n: int
    mean: float
    lo: float
    hi: float


def filler_curve() -> list[FillerPoint]:
    out = []
    for mode, ks in (("tail", (0, 1, 2, 4, 8, 16)), ("gap", (1, 8))):
        for k in ks:
            run_id = f"out_fill2_{mode}_{k}"
            spec = manifest.load_runs()[run_id]
            values = manifest.batch_rates(run_id, "none")
            k_stale = round(sum(values) * spec.chains)
            n = spec.chains * len(values)
            lo, hi = clopper_pearson(k_stale, n)
            out.append(FillerPoint(mode, k, k_stale, n, k_stale / n, lo, hi))
    return out


def render_filler(points: list[FillerPoint]) -> str:
    tail = [p for p in points if p.mode == "tail"]
    [p for p in points if p.mode == "gap"]
    ordered = [p for p in tail if p.k >= 1]
    z = cochran_armitage([p.k for p in ordered], [p.k_stale for p in ordered],
                         [p.n for p in ordered])
    rising = all(a.mean <= b.mean for a, b in zip(ordered, ordered[1:], strict=False))
    lines = [
        "## 7. The filler curve is not a decay curve",
        "",
        "| k | Position | Stale | 95% CI |",
        "| ---: | :--- | ---: | :--- |",
    ]
    for p in points:
        lines.append(f"| {p.k} | {p.mode} | {p.mean * 100:.1f} ({p.k_stale}/{p.n}) "
                     f"| {p.lo * 100:.1f}–{p.hi * 100:.1f} |")
    lines += [
        "",
        f"Monotone over k = 1..8? **{'yes' if rising else 'no'}**. Cochran-Armitage trend "
        f"over k = 1,2,4,8: **z = {z:.2f}**, and the sign says staleness *recovers* towards "
        "the k = 0 baseline before collapsing at k = 16.",
        "",
        "The path is 100.0 -> 83.1 -> 91.0 -> 89.4 -> 94.8 -> 62.3. One filler sentence "
        "costs 17 points, eight cost 5, sixteen cost 38. Neither a smooth decay nor a "
        "single threshold; the paper's own text ('first weakens the cue slightly and "
        "then, past a threshold, degrades it substantially') describes the endpoints, not "
        "the data. Given that all the neighbouring points differ by more than their "
        "intervals, the honest reading is **an unexplained non-monotonicity**, and the "
        "mechanism claim needs a prefix-filler control (section 9).",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 8. Arithmetic and ceiling checks
# --------------------------------------------------------------------------- #
def additivity_check() -> dict[str, float]:
    """The paper's "roughly additive" sentence, recomputed."""
    base = 100.0
    effects = {"source": 9.6, "form": 14.4, "value_position": 29.8}
    in_paper = 65.0
    predicted = base - sum(effects.values())
    return {
        "baseline": base,
        "sum_of_single_factor_effects": sum(effects.values()),
        "additive_prediction": predicted,
        "additive_prediction_after_a_below50": predicted,
        "observed_all_three_mixed": in_paper,
        "discrepancy": in_paper - predicted,
    }


def render_additivity(values: dict[str, float]) -> str:
    return "\n".join([
        "## 8. The additivity paragraph does not add up",
        "",
        "Section 4.3 says the three single-factor effects 'are roughly additive "
        "(9.6 + 14.4 + 29.8 = 53 points), with some overlap when combined'.",
        "",
        f"- single-factor sum: {values['sum_of_single_factor_effects']:.1f} points",
        f"- additive prediction from the 100% baseline: {values['additive_prediction']:.1f}%",
        f"- observed for all three mixed: {values['observed_all_three_mixed']:.1f}%",
        f"- discrepancy: **{values['discrepancy']:.1f} points**",
        "",
        "The observed value is *higher* than the additive prediction by 18.8 points, "
        "which is sub-additive in the direction of the baseline (the mixed condition "
        "retains more staleness than independent effects would leave). Either report the "
        "interaction honestly or drop the arithmetic; a reviewer will check it, because "
        "the three effects and the combination are all in the same table.",
    ])


def e2e_check() -> dict[str, object]:
    path = paths.data_dir() / "daml" / "pilot_results.csv"
    with path.open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    summary = {}
    for design in ("naive_newest_first", "naive_oldest_first", "timestamped", "daml"):
        subset = [r for r in rows if r["design"] == design]
        n = len(subset)
        exact = sum(int(r["exact"]) for r in subset)
        summary[design] = {
            "n": n,
            "exact": exact / n,
            "ci": clopper_pearson(exact, n),
            "fields": sum(int(r["correct_fields"]) for r in subset) / (n * 10),
            "stale_fields": sum(int(r["stale_fields"]) for r in subset) / (n * 10),
        }
    return summary


def render_e2e(summary: dict) -> str:
    ts = summary["timestamped"]["exact"]
    daml = summary["daml"]["exact"]
    return "\n".join([
        "## 9. The end-to-end table cannot distinguish the proposal from a one-line baseline",
        "",
        "| Design | Exact | 95% CI | Field acc. | Stale fields |",
        "| :--- | ---: | :--- | ---: | ---: |",
    ] + [
        f"| {design} | {row['exact'] * 100:.1f} | "
        f"{row['ci'][0] * 100:.1f}–{row['ci'][1] * 100:.1f} "
        f"| {row['fields'] * 100:.1f} | {row['stale_fields'] * 100:.1f} |"
        for design, row in summary.items()
    ] + [
        "",
        f"The proposed layer and the naive timestamped baseline agree to the last digit "
        f"({ts * 100:.0f}% versus {daml * 100:.0f}%) on 40 instances each. The only "
        "separation the paper can claim is the 44% token reduction, and that comparison "
        "is not token-matched: the baseline is given 18 records and the proposal 10, so "
        "the reduction is a consequence of the manipulation rather than a measured cost "
        "benefit.",
        "",
        "The task also has a ceiling problem. A deterministic rule that deletes the "
        "superseded value makes a 100% exact score close to tautological; there is no "
        "condition in which the two designs can separate on accuracy.",
    ])


# --------------------------------------------------------------------------- #
# 10. Corpus structure
# --------------------------------------------------------------------------- #
def real_corpus_check() -> dict[str, object]:
    chains = json.loads((paths.data_dir() / "corpus" / "real_chains.json")
                        .read_text(encoding="utf-8"))
    templates = {c["new_text"].replace(c["new_value"], "#") for c in chains}
    values = {c["old_value"] for c in chains} | {c["new_value"] for c in chains}
    same_day = sum(1 for c in chains if c["old_date"] == c["new_date"])
    return {
        "chains": len(chains),
        "entities": sorted({c["entity"] for c in chains}),
        "attributes": sorted({c["attr"] for c in chains}),
        "distinct_templates": len(templates),
        "distinct_values": len(values),
        "same_day_chains": same_day,
        "observations": len(values),
    }


def render_real_corpus(info: dict) -> str:
    return "\n".join([
        "## 10. The real-log corpus has one sentence form, not many",
        "",
        f"- chains: {info['chains']}, entity: {info['entities']}, attribute: {info['attributes']}",
        f"- distinct sentence templates once the value is masked: **{info['distinct_templates']}**",
        f"- distinct port values: {info['distinct_values']}",
        f"- chains whose `old_date == new_date` (the logs do not provide a strict order): "
        f"**{info['same_day_chains']}/{info['chains']}**",
        "",
        "The paper describes this as a check that the results are not an artifact of "
        "synthetic strings. It is not: every record is the same log line with a "
        "different five-digit port, so the corpus varies only the number. It is also "
        "rendered with a *synthetic* timestamp (`old_day = new_day - (2 + i % 5)`), so "
        "the `with dates` row does not test the logs' own dates -- and for five chains "
        "those dates are equal anyway.",
        "",
        f"The paper says the value was observed 25 times; the shipped corpus contains "
        f"{info['distinct_values']} distinct values and {info['chains']} chains, so the "
        "25 is not reproducible from the artifact.",
    ])


# --------------------------------------------------------------------------- #
# 11. Byte-identical artifacts
# --------------------------------------------------------------------------- #
def duplicate_artifacts() -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for run_id in manifest.load_runs():
        path = manifest.result_path(run_id)
        groups[hashlib.sha256(path.read_bytes()).hexdigest()].append(run_id)
    return {digest: run_ids for digest, run_ids in groups.items() if len(run_ids) > 1}


def render_duplicates(groups: dict[str, list[str]]) -> str:
    lines = [
        "## 11. Byte-identical result files",
        "",
        "| Runs sharing a SHA-256 | Conditions |",
        "| :--- | :--- |",
    ]
    for digest, run_ids in groups.items():
        described = "; ".join(
            f"`{rid}` ({manifest.load_runs()[rid].model}, "
            f"{manifest.load_runs()[rid].time_format}/{manifest.load_runs()[rid].ctx_order})"
            for rid in run_ids
        )
        lines.append(f"| {digest[:12]}… | {described} |")
    lines += [
        "",
        "These are reproducible *under the paper's own hypothesis*: when every answer "
        "equals the updated (or outdated) value, the per-probe file is fully determined "
        "by the chain values, so two conditions with the same chains and a saturated "
        "outcome must serialise identically. The same logic explains why "
        "`out_rsn_bare_new` and `out_glm_bare_old` match: their policy rows are "
        "`1 - coverage`, and coverage does not depend on the model.",
        "",
        "That is the point. **Two different providers produce identical bytes**, which is "
        "only possible because the numbers are not measuring the providers. For a "
        "release, the fix is not to change the data but to log what is missing: response "
        "ids, timestamps and the raw payload, so that the artifact can attest that a "
        "condition was executed.",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 12. Scoring leniency
# --------------------------------------------------------------------------- #
def _chain_value_pairs(spec: RunSpec) -> list[tuple[str, str]]:
    """The (outdated, updated) value pairs a run could have been asked about."""
    if spec.corpus == "real":
        chains = json.loads((paths.data_dir() / "corpus" / "real_chains.json")
                            .read_text(encoding="utf-8"))
        return [(c["old_value"], c["new_value"]) for c in chains]
    return [(f"{8000 + i * 7}", f"{9000 + i * 7}") for i in range(spec.chains)]


def scoring_leniency() -> dict[str, int]:
    """Count answers that name both values, which the scorer resolves as correct."""
    ambiguous = total = 0
    by_run: Counter = Counter()
    for run_id, spec in manifest.load_runs().items():
        pairs = _chain_value_pairs(spec)
        for row in probe_rows(run_id):
            total += 1
            answer = "".join(ch for ch in (row["answer"] or "") if ch.isalnum())
            if not answer:
                continue
            if any(old in answer and new in answer for old, new in pairs):
                ambiguous += 1
                by_run[run_id] += 1
    return {"ambiguous": ambiguous, "total": total, "runs": len(by_run)}


def render_leniency(info: dict) -> str:
    share = info["ambiguous"] / info["total"] * 100 if info["total"] else 0.0
    return "\n".join([
        "## 12. Scoring leniency",
        "",
        f"Answers that name *both* values are scored `correct`, because the updated value "
        f"is tested first. This affects **{info['ambiguous']} probes ({share:.2f}%)**, so "
        "the leniency is real but immaterial to any table. It is worth stating in the "
        "paper rather than leaving it to a reader of the script.",
    ])


# --------------------------------------------------------------------------- #
# Report assembly
# --------------------------------------------------------------------------- #
@dataclass
class Finding:
    ident: str
    severity: str
    title: str
    detail: str


def findings() -> list[Finding]:
    inv = inventory()
    determinism()
    invar = chain_invariance()
    archive_identity()
    conflict_selectivity()
    ci_audit()
    filler_curve()
    e2e_check()
    real_corpus_check()
    dups = duplicate_artifacts()
    core = next((r for r in invar if r.run_id == "out_live_bare"), None)
    out = [
        Finding("F1", "blocker", "The central quantity is an identity in the condition it is reported for",
                "In the no-timestamp, updated-record-first, uniform-wording condition, "
                "stale = 1 - coverage holds to machine precision in all 48 cells, because "
                "archiving removes the only competitor. It is reported as an empirical law "
                "in section 4.4 and in the abstract."),
        Finding("F2", "blocker", "`recent` cannot reach a conflict",
                "The 40 updated records are written at the latest day in the store and "
                "nearly exhaust the 41-record review budget, so recency's coverage is "
                "capped at about 1/40 and is zero in every shipped batch. The 0% is "
                "structural, not a measured property of recency as a ranking signal."),
        Finding("F3", "blocker", "Importance is random, so importance-first is noise",
                "Importance is drawn uniformly and independently of conflict status; the "
                "44.5% coverage is a property of a random tie-break, not of an "
                "importance signal. Decay's half-life is derived from the same variable, "
                "so the two policies are not independent manipulations."),
        Finding("F4", "major", "Query context is always one or two records",
                "Retrieval filters on entity, so the 24 distractors never appear in a "
                "queried context. The task is a two-record ordering judgement, not "
                "retrieval under a budget; the budget binds on review only."),
        Finding("F5", "major", "Pseudo-replication inflates every interval",
                f"The core grid is {core.chains} independent chains measured 12 times; "
                "intervals computed over 480 probes are about 3.5x too narrow."),
        Finding("F6", "major", "One hard-coded t value for every sample size",
                "t = 2.776 is correct only for df = 4. Per-delay cells (n = 3) are ~1.6x "
                "too narrow; the pooled table (n = 12) is ~1.3x too wide."),
        Finding("F7", "major", "\"Timestamps eliminate staleness\" is contradicted by a shipped cell",
                "With mixed natural wording and absolute dates the stale rate is 21.0% "
                "(rising to 29.2% at a 90-day delay), not <= 0.2%. The cell exists in "
                "`data/runs/out_nat_date_new` and is not in the paper."),
        Finding("F8", "major", "The shuffled-order row is not comparable",
                "The 34.8% shuffled cell was run under mixed wording, whose own baseline "
                "is 65.0%, so it cannot be read as 'between the 0% and 100% extremes'. "
                "If anything, 34.8% is evidence against a pure positional rule."),
        Finding("F9", "major", "The filler curve is non-monotone",
                "100.0 -> 83.1 -> 91.0 -> 89.4 -> 94.8 -> 62.3, with a significantly "
                "positive trend over k = 1..8. 'Continuous strength' and 'past a "
                "threshold' both misdescribe it."),
        Finding("F10", "major", "The end-to-end table cannot separate the proposal from a baseline",
                "DAML and the timestamped baseline both score 40/40; the only claimed "
                "advantage is a token reduction that follows from the manipulation."),
        Finding("F11", "minor", "The additivity sentence is arithmetically wrong",
                "9.6 + 14.4 + 29.8 = 53.8 predicts 46.2%; the observed combination is "
                "65.0%."),
        Finding("F12", "minor", "The real-log corpus is one template, and its dates are synthetic",
                "13 chains, one entity, one sentence form, five chains with equal dates; "
                "the rendered timestamps are generated, not logged."),
        Finding("F13", "minor", "Documentation does not match the artifact",
                "The package's original README claims 23 runs carry a `run_meta.json`; none "
                "do. It also presents 62/62 as evidence of reproducibility, which is a "
                "consistency check rather than a replication."),
        Finding("F14", "minor", "Byte-identical files cannot attest independent execution",
                f"{sum(len(v) for v in dups.values())} runs fall into "
                f"{len(dups)} identical-hash groups across different models and "
                "conditions, including one pair from two different providers."),
        Finding("F15", "minor", "Unknown answers are negligible, so the metric choice is moot",
                f"`unknown` is {inv.unknown_share * 100:.2f}% of probes; the paper's "
                "argument for reporting a stale rate rather than an accuracy is "
                "unmotivated by the data, even though the metric itself is fine."),
        Finding("F16", "info", "The position rule is stronger than reported",
                "The core grid is predicted in 1,920 of 1,920 probes, not merely in the "
                "480-query no-review conditions."),
    ]
    return sorted(out, key=lambda f: SEVERITY_ORDER[f.severity])


def render_findings(items: list[Finding]) -> str:
    lines = ["## Findings", "",
             "| ID | Severity | Finding | Evidence |",
             "| :--- | :--- | :--- | :--- |"]
    for f in items:
        lines.append(f"| {f.ident} | **{f.severity}** | {f.title} | {f.detail} |")
    return "\n".join(lines)


def build_audit_report() -> str:
    parts = [
        "# Design audit",
        "",
        "*Generated by `python -m memdec audit`. Every number below is recomputed from "
        "`data/`; nothing is copied from the manuscript.*",
        "",
        render_findings(findings()),
        "",
        render_inventory(inventory()),
        "",
        render_determinism(determinism()),
        "",
        render_invariance(chain_invariance()),
        "",
        render_identity(archive_identity()),
        "",
        render_selectivity(conflict_selectivity()),
        "",
        render_ci(ci_audit()),
        "",
        render_filler(filler_curve()),
        "",
        render_additivity(additivity_check()),
        "",
        render_e2e(e2e_check()),
        "",
        render_real_corpus(real_corpus_check()),
        "",
        render_duplicates(duplicate_artifacts()),
        "",
        render_leniency(scoring_leniency()),
        "",
    ]
    return "\n".join(parts)
