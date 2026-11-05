# Review and methodological assessment

*This document is the narrative companion to [`AUDIT.md`](AUDIT.md), which contains the
machine-generated evidence. Read the audit for numbers; read this for what to do about
them. Every figure quoted here can be regenerated with `python -m memdec build`.*

---

## 1. Verdict

The measurement is real, the effect is real, and the paper currently draws the wrong
conclusion from it. That is a fixable situation, and a good one: most papers with this
problem have no data at all.

What is strong: the central phenomenon is large, clean and reproducible. Adding dates
takes staleness from 100% to 0.2%. Reversing the order of two records flips it from 100%
to 0%. Removing the timestamp and keeping everything else identical produces that flip.
An effect that large, obtained by changing one thing, is the kind of result that survives
review — if it is described accurately.

What is weak: the paper's *theoretical* claim is not what its data shows, three of its
four "maintenance policies" cannot work in principle, its statistics contain a concrete
error, and its quantitative headline (`stale = 1 − coverage`) is an algebraic identity
that the paper reports as a law. A referee in the memory-evaluation area will find the
identity in about ten minutes, because Table 4 states the mechanism and then states the
result as if the mechanism had not been stated.

The good news is that the fix is a reframing plus about two days of cheap experiments,
not a new study. Section 7 gives the reframing; [`ROADMAP.md`](ROADMAP.md) gives the
sequence.

| Current state | Realistic target |
|---|---|
| A workshop paper with a large effect, undermined by an identity claim | A workshop paper that is hard to attack, or an arXiv preprint with a defensible contribution |
| No venue will accept `stale = 1 − coverage` as a finding | The conflict-hit rate framing is publishable and genuinely new |
| Nine model-policy cells that cannot separate | Three cheap cells that can (random, oracle, prefix-filler) |

---

## 2. The three blockers

### B1. The central quantity is an identity in the condition it is reported for

**What the paper says.** Section 4.4 and the abstract: "the stale rate equals one minus
archive coverage", presented as the discovery that maintenance helps only by removing
conflicts.

**What the data says.** In the no-timestamp, updated-record-first, uniform-wording
condition, the equality holds to machine precision in **all 48 batch cells** — maximum
absolute deviation `5.55e-17`. It is exact in exactly four of the 29 four-policy runs,
and those four are precisely the runs where the model obeys the positional rule
(`out_live_bare`, `out_uni_bare_new`, `out_rsn_bare_new`, `out_glm_bare_old`).

**Why it must be exact.** Three facts compose: archiving a record removes the outdated
value from the context; a context with one record admits one answer, which is the updated
value; and a context with two records triggers the position rule, which for this ordering
returns the outdated value. Given those three, `stale = 1 − coverage` is arithmetic. The
paper states all three in section 4.4, two paragraphs before reporting the result.

**Why this is a blocker rather than a wording problem.** It is the paper's advertised
contribution. A referee who checks will conclude either that the author does not see it
(the worse reading) or that it is deliberately dressed up (the other worse reading).
Neither is recoverable by revision of the prose.

**Fix.** Do not delete the result; demote it to a design property and replace it with the
measurement it implies. If `stale = 1 − coverage` is forced, then the only free quantity
is **which records a policy selects** — the conflict-hit rate. That is measurable, it is
not forced, and it separates the policies for the first time. Section 7 has the framing;
`docs/tables/table4_archive.md` has the numbers (recency 0.0%, random 38.5%, importance
43.5%, decay 50.6%).

### B2. The recency baseline cannot reach a conflict

**What the paper says.** Recency-first reviews 41.3 records and archives 0.0, and this is
reported as evidence that recency does not help.

**What the design guarantees.** The updated record of each slot is written at day 199, the
latest day in the store. All 40 updated records are therefore at the top of any
recency-ordered queue, and they alone nearly fill the 41-record budget. At most one
reviewed record can be anything else. Recency's coverage is capped near 1/40 before any
model is called, and it is zero in every one of the twelve batches.

**Why it matters.** The paper's central comparison is between four policies, and one of
them is a straw man manufactured by the store layout. A referee who notices will discount
the whole maintenance section. Worse, the *correct* conclusion is more interesting than
the reported one: recency is **worse than random** (0.0% versus 38.5% conflict-hit rate),
because it preferentially spends its budget on records that cannot be superseded. That is
a substantive claim about a popular heuristic, and it is currently hidden inside a number
the paper presents as uninformative.

**Fix.** Report the cap, report the random baseline, and restate the finding as "recency
is anti-correlated with conflict in a store where recency and supersession are
positively correlated". Then either decorrelate them (see experiment E2 in the roadmap)
or state the confound in the limitations.

### B3. Importance is random, so importance-first is noise

**What the paper says.** Importance-first archives 17.8 conflicts (44.5% coverage) and
decay-first archives 21.0 (52.5%), and the paper reads the ordering as a property of the
ranking signals.

**What the design does.** `build_store` draws each record's importance uniformly from
`{0.9, 0.7, 0.55, 0.35}` (outdated) and `{0.9, 0.7, 0.5, 0.35}` (updated),
*independently of which record is current*. An importance-ordered policy is therefore a
random prior with a tie-break. Whatever coverage it achieves is a property of the tie
breaking, not of importance as a signal.

There is a second problem on top of the first: the decay half-life is chosen by importance
band (30/12/6 days), so the "decay" and "importance" policies are monotone functions of
the same variable. They are not two independent manipulations, and the paper contrasts
them as if they were — including in the sentence "the decay signal is not doing any work
of its own: importance-first, which ignores decay entirely, lands on the same line".

**Why it matters.** The negative result about decay is one of the paper's selling points,
and it is currently untested. It may well be true — decay's 50.6% hit rate against a 38.5%
random baseline suggests it is doing *something* — but the experiment as run cannot
distinguish a forgetting curve from a random tie-break from a mild recency prior.

**Fix.** Give importance a meaning that is independent of conflict status (e.g. draw it
from a slot-level latent trait, or set it from an external notion of salience), and add a
random-selection control. Both are cheap; see experiment E1.

---

## 3. The seven major issues

### M1. The queried context is always one or two records

`build_context` filters on `entity`, so a query about `服务07` retrieves exactly the two
records for `服务07`. The 24 distractor records never appear in any queried context; they
exist only to consume review budget. Confirmed on 50,832 probes: every `ctx_entries` value
is 1 or 2.

The paper describes the task as retrieval under a budget ("truncating by relevance when
the budget is exceeded", `render(budget, model)`). In the measurement, the budget never
binds on retrieval and always binds on review. The task is a two-record ordering
judgement, which is why the answer is deterministic — and that determinism is what makes
B1 true.

**Fix.** Say so in section 3.1. Better, add a condition in which retrieval genuinely
competes: 4–8 records per slot, distractors that share the entity, and a budget that
forces truncation. That single change simultaneously removes the degeneracy and makes
the "retrieval budget" language true.

### M2. Every interval is about 3.5× too narrow

Each condition measures 40 chains at 4 delays × 3 seeds. The verdict is constant across
those twelve repeats for 40 of 40 chains in the core grid, and for 28 of 29 runs overall
the within-chain variation is at or near zero. The 480 probes are therefore not 480
independent observations; they are 40 observations, repeated.

A binomial interval computed over 480 probes is narrower than the honest one by
`sqrt(480/40) = 3.46`. The paper reports 100.0% for a cell whose exact interval, at the
chain level, is **[91.2, 100.0]**. Every `±` in `summary.md` and every error bar in
Figure 1 inherits this.

The `unknown` bucket does not rescue the accuracy metric either: it is 132 probes out of
50,832 (0.26%), and in every main-grid cell `correct + stale = 1` exactly.

**Fix.** Report chain-level intervals (`memdec.analysis.tables.cell(...).chain_ci`), state
the effective sample size, and cluster by chain if any model is fitted. `docs/tables/`
already contains both columns side by side.

### M3. One hard-coded t value for every sample size

`_ci` in the original script is `t = 2.776`, the 95% critical value for `df = 4`. Per-delay
cells have `n = seeds`, i.e. 2 or 3 (correct multipliers 4.303 and 12.706 for df 1); the
pooled table has `n = 12` (correct multiplier 2.201). The result is that the per-delay
tables in each `summary.md` are about **1.6× too narrow** and `all_conditions.md` is about
**1.3× too wide**.

This is a small bug with a large diagnostic value: it is visible by comparing the two
tables, and it suggests the intervals were never checked against each other.

**Fix.** `memdec.stats.mean_ci` now takes `n`; the corrected numbers are in
`docs/tables/table1_uncertainty.md`.

### M4. "Timestamps eliminate staleness" is contradicted by a shipped cell

The abstract says staleness is "essentially eliminated (at most 0.2%)" with reliable
timestamps, and section 4.1 says "adding dates returns all four configurations to 0%".

There is a condition in the shipped data — absolute dates with mixed natural wording,
`data/runs/out_nat_date_new` — where the stale rate is **21.0%**, rising from 13.3% at a
one-day delay to **29.2%** at ninety days. The 0.2% figure holds only for uniform
template wording. This condition is not in the paper, and it is not in the author's own
62-item checker.

This is simultaneously the paper's biggest exposure and its biggest opportunity. It is
exposure because the abstract is falsified by the authors' own data. It is opportunity
because it converts the thesis from "add timestamps" (which is a truism, and which the
paper cannot claim as a contribution) into **"decidability requires a time cue *and*
format uniformity, and neither alone is sufficient"** — a claim with a 2×2 table behind it
and a non-obvious practical implication.

**Fix.** Report the 2×2 (`docs/tables/table_missing_interaction.md`), rewrite the abstract
accordingly, and treat the wording × timestamp interaction as a result rather than an
inconvenience. It also gives the paper a real answer to "so why not just add dates?".

### M5. The shuffled-order row is not comparable

Section 4.2 says a shuffled order "falls between the extremes (34.8%, measured under mixed
wording), consistent with order being the operative cue".

The parenthetical undoes the sentence. The 0% and 100% extremes are uniform-template
conditions; the shuffled cell is mixed-wording, whose matched baseline is 65.0%, not 100%.
Under a pure positional rule, a random order predicts *about 50%* — and the observed value
is significantly **below** 50%. If anything, 34.8% is evidence that order is not the sole
operative cue under non-uniform wording.

**Fix.** Either run the shuffled condition with uniform wording (one condition, about 23
minutes), or drop the row. Do not keep the current sentence.

### M6. The filler curve is not a decay curve

The reported path is 100.0 → 83.1 → 91.0 → 89.4 → 94.8 → 62.3. The text reads it as
"first weakens the cue slightly and then, past a threshold, degrades it substantially".
The actual shape is a 17-point drop at one filler, a significant *recovery* to 94.8 at
eight fillers (Cochran–Armitage z = +4.99 over k = 1, 2, 4, 8), then a 32-point collapse at
sixteen.

Neither "continuous strength" nor "a threshold" describes that. All the neighbouring
points differ by more than their intervals, so it is not noise either; it is an
unexplained non-monotonicity, and the mechanism story ("the cue is anchored at the end of
the context") does not predict it.

There is also a missing control. All the filler conditions contribute text *after* the
records, so "the anchor is at the end" is confounded with "more text before the question
is worse". Prepending the same fillers before the records separates the two.

**Fix.** Run the prefix control (k = 1, 2, 8, 16; under 1 CNY), report the curve as
non-monotone, and either drop the mechanism claim or replace it with the one the control
supports.

### M7. The end-to-end table cannot separate the proposal from a baseline

`timestamped` and `daml` both score 40/40 exact, 100% field accuracy, 0% stale fields.
With 40 instances each, the exact intervals are [91.2, 100.0] for both. There is no
condition in which the two can differ, because a deterministic rule that deletes the
superseded value makes a saturated score tautological.

The only claimed separation is a 44% token reduction — and that comparison is not
token-matched: the baseline is given 18 records and the proposal 10, so the reduction is
a consequence of the manipulation. A token-matched baseline (timestamped, truncated to 10
records) is required to attribute it.

**Fix.** Three options, in order of cost: (a) re-label the pilot honestly as a sanity
check and move the contribution to the analysis sections; (b) add a token-matched
baseline; (c) add a harder task where archiving and truncation differ (multi-hop, or
budgets small enough that truncation removes needed facts). Option (b) is one afternoon
and turns a null result into an efficiency claim.

---

## 4. The minor issues

**m1. The additivity sentence does not add up.** Section 4.3: "roughly additive (9.6 +
14.4 + 29.8 = 53 points), with some overlap when combined". The sum predicts 46.2% from a
100% baseline; the observed combination is 65.0%. The discrepancy is 18.8 points in the
direction that the sentence's own hedging does not cover. Delete the arithmetic or report
the interaction.

**m2. The real-log corpus is one sentence form.** All 13 chains share the entity
`Web GUI`, the attribute `端口`, and a single template
`运行环境提示：Current DeepSeek Harness Web GUI URL: "http://127.0.0.1:NNNNN"。` with a
different five-digit number. There is no wording heterogeneity to average over. The paper
also says the value was observed 25 times; the shipped corpus contains 14 distinct values
in 13 chains, so the 25 is not reproducible from the artifact.

**m3. The real-log dates are synthetic.** `build_store_real` sets
`new_day = 200 − delay` and `old_day = new_day − (2 + i mod 5)`, then renders those
generated dates. The logs' own dates are never rendered — and in 5 of 13 chains the two
source timestamps are equal, so the logs would not have supported a strict order anyway.
The "with dates: 0.0%" row for real logs therefore tests generated dates, not logged ones.

**m4. Documentation does not match the artifact.** The package's original README states
that the later 23 run directories carry a `run_meta.json`; none of the 37 do. It also
presents "62/62" as evidence of reproducibility, which it is not: the checker recomputes the
paper's numbers from the paper's own CSVs. That is a consistency check, and it is a
useful one — it just is not the thing the sentence implies.

**m5. Byte-identical result files.** Ten runs fall into four identical-SHA-256 groups, and
one group joins `out_live_date_rev` (DeepSeek), `out_uni_bare_old` (DeepSeek) and
`out_glmplus_date_new` (GLM-4-Plus). This is *expected* under the paper's own hypothesis:
when every answer is saturated, the per-probe file is fully determined by the chain
values. Which is the point — two different providers produce identical bytes because the
file records no per-model variation beyond a verdict that the design already fixed. It
also means the artifact cannot independently attest that those conditions were executed
separately. Log response ids and timestamps to fix that.

**m6. The metric argument is unmotivated.** Section 3.1 argues for a stale rate over an
accuracy because "unknown" would dilute the signal. `unknown` is 0.26% of probes and zero
in the main grid, where `correct + stale = 1` exactly. The metric choice is fine; the
justification is not supported by the data. Keep the metric, drop the argument, or report
the accuracy alongside it.

**m7, in the paper's favour.** The position rule is *stronger* than the paper claims. The
paper says all 480 queries of each no-review condition agree with it; in fact the whole
1,920-probe core grid does, under a single binary predictor: was the stale record archived
or not. That is a clean, checkable, striking statement — and it is the right place to put
the emphasis that B1 currently occupies.

---

## 5. Statistics: what to change in the methods section

1. **State the unit of analysis.** It is the chain (40 synthetic, 13 real-log). Every
   proportion should carry an interval over that unit, and any model should include a
   chain-level random effect or use a cluster-robust variance.
2. **Stop reporting `±` on saturation.** A cell at 40/40 has an interval of [91.2, 100.0].
   Reporting "100.0 ± 0.0%" is wrong in a way that a referee will notice immediately.
3. **Fix the t value** (see M3) and use exact intervals at n = 40 rather than Wald
   intervals at n = 480.
4. **Correct for multiplicity, or stop making marginal claims.** There are 37 conditions;
   the large contrasts (0 vs 100) do not need a test, but the mid-sized ones (44.6 vs 52.5
   coverage) do. `memdec.stats.holm` is there if you want it.
5. **Do not describe 2 or 3 seeds as independent replications.** The seeds resample
   nuisance variables (old-record age, importance draws), not chains or model behaviour.
   They cannot support a claim about sampling variability.
6. **Report the exceptions.** The real-log rule fails on a handful of the thirteen chains,
   and the two timestamped conditions each have exactly one violating probe. Those are the
   most interesting data points in the study and the paper does not mention them.

---

## 6. Positioning and related work

The paper cites the right ancestors (MemGPT, Generative Agents, MemoryBank, Lost in the
Middle, LoCoMo, LongMemEval, spaced repetition) and is missing the immediate neighbours a
referee will expect:

- **Temporal and bitemporal knowledge bases.** The question "which of two records is
  current" is a solved problem in that literature (valid time vs transaction time,
  supersession, tombstones). Not citing it makes the contribution look novel when it is a
  rediscovery of a well-understood problem in a new setting — which is fine, but it must be
  framed as such.
- **Memory systems with explicit conflict handling** (2024–2025): Mem0, Zep/Graphiti
  (temporal knowledge graph with edge invalidation), Letta. Several of these already
  invalidate superseded edges, which is exactly P2 of the proposed design.
- **Stale-fact and conflicting-evidence work in RAG**, and the "knowledge conflict"
  literature, which studies what a model does when retrieved context contradicts its
  parametric knowledge — closely related to the two-record conflict studied here.
- **Format and order sensitivity** beyond Lost in the Middle: multiple-choice option-order
  bias, prompt-format sensitivity, and the "positional prior" literature in in-context
  learning. The finding that the direction differs by model family has precedent.

Two framing consequences. First, "add timestamps and archive conflicts" cannot be the
contribution, because other systems already do it; the contribution has to be the
*measurement* — that presentation factors dominate policy factors, and by how much.
Second, the decidability vocabulary has to be defined before it is used; see section 7.

---

## 7. The reframing that saves the paper

The paper wants "decidability" to be a first-class property of a memory store. At present
it is a metaphor, used in several slightly different senses. Making it precise costs about
a page and fixes most of the conceptual problems at once.

**Definition.** Fix a store `S`, a query `q`, and a presentation function `π` that renders
`S` into a prompt. Call the pair `(S, π)` *decidable for q* if, for every admissible model
`M`, the answer `M(π(S), q)` is the true current value. Decidability is a property of the
presentation, not of the model.

Three propositions follow, and they are the paper's results in the right order:

- **P1 (dates decide).** If every live record for the slot carries a total-order timestamp
  that the model can compare, `(S, π)` is decidable. Empirically this holds for uniform
  templates (0/480 violations at the chain level, 1/480 at the probe level) and **fails
  for mixed wording** (21.0%). The empirical qualifier is the interesting part.
- **P2 (position does not decide).** Without a timestamp, the answer is a function of
  position, and the function's direction is model-specific: DeepSeek reads the last
  record, GLM-4-Flash the first, GLM-4-Plus a per-chain content rule (39 of 40 chains give
  the same answer at every delay and seed). Presentation is therefore not decidable; it is
  *predictable given the model*, which is a different and weaker property.
- **P3 (maintenance is coverage).** Under P2, `stale = 1 − coverage` exactly. The
  maintenance question therefore reduces to a selection question, and the only meaningful
  policy metric is the conflict-hit rate of the selection function.

That sequence is a paper. It has a definition, three claims, one of which is a theorem and
two of which are measurements, and a negative result with a mechanism. It also converts
every one of the blockers above from an embarrassment into a component:

- B1 becomes P3, stated as a proposition rather than discovered as an identity.
- B2 becomes "recency is anti-correlated with conflict" — a claim about a heuristic, with
  a random baseline (0.0% vs 38.5%).
- B3 becomes "a randomly assigned importance signal cannot beat random selection", which
  is a cautionary result about how these policies are usually evaluated, and which is
  exactly the kind of methodological point a workshop audience rewards.

And the abstract changes from a truism plus an identity to something like:

> Whether an agent answers with the current value is decided by the *presentation* of its
> memory, not by how that memory is maintained. With comparable timestamps and uniform
> wording, staleness disappears; with either alone it does not. Without timestamps, a
> positional rule whose direction is model-specific decides the answer, and it decides it
> deterministically: 1,920 of 1,920 probes in our core grid. Consequently, maintenance
> policies can only help by removing contradicting records, and their apparent differences
> reduce to how well they find them — a quantity we measure against a random baseline.

That abstract is defensible, and every clause in it is already supported by the shipped
data once the 2×2 in M4 is included.

---

## 8. What a referee will ask

| Question | Current answer | After the roadmap |
|---|---|---|
| Isn't `stale = 1 − coverage` trivially true? | "Once a conflict has been removed, the answer is necessarily correct" — the paper concedes it, then reports it as a law | It is Proposition P3; the measured quantity is the conflict-hit rate |
| Why does recency remove nothing? | Not addressed | Structural: the 40 updated records fill the budget (B2) |
| What does "importance" mean here? | Not stated that it is random | Either a real signal or an explicit null result about random signals (B3) |
| You claim dates fix it, but your own data has a 21% cell | Not in the paper | The 2×2 is the headline (M4) |
| 480 queries, or 40 chains? | Implied 480 | Effective n stated, chain-level intervals everywhere (M2) |
| Why is the error bar on 100% zero? | `± 0.0` | Exact interval [91.2, 100.0] (M2) |
| Four model configurations from two providers — how general is the direction finding? | Acknowledged | Kept as a limitation, and strengthened with a per-chain invariance result |
| Why does DAML beat a one-line timestamp baseline? | It does not; only on tokens | Token-matched baseline, or the pilot is demoted (M7) |
| Is the real-log corpus real? | "Verbatim log lines" | Verbatim text, generated timestamps, one template — stated plainly (m2, m3) |

---

## 9. What is genuinely good, and should be kept

- **The core manipulation.** One factor at a time, identical store, identical prompt
  scaffold. When the effect is 0 vs 100, this design is exactly right.
- **The direction-differs-by-model finding.** It is the most surprising thing in the
  study, it replicates across both providers, and it has a clean per-chain structure
  (39 of 40 chains are delay-invariant for GLM-4-Plus).
- **The relative-notation gradient.** 0.0 → 0.8 → 11.7 → 50.8 across delays 1/7/30/90 is
  the cleanest monotone result in the study, and the paper spends one sentence on it. It
  says something practical and non-obvious: a "day N" notation is not a timestamp, because
  using it requires arithmetic the model does not reliably do.
- **The honesty of the limitations section.** It already says the task is minimal, the
  corpus is small, and the population of models is not covered. That is the right instinct;
  the roadmap mostly extends it.
- **The engineering.** Deterministic stores, reproducible seeds, error-tolerant scoring, a
  manifest. This is why the audit could be done at all, and why the replay passes exactly.

---

## 10. Reading order

1. `docs/AUDIT.md` — the evidence, regenerated from `data/`.
2. `docs/tables/table_missing_interaction.md` — the 2×2 that should be the headline.
3. `docs/tables/table4_archive.md` — the conflict-hit rates against a random baseline.
4. `docs/ROADMAP.md` — what to run, in what order, for how much.
5. `docs/PROTOCOL.md` — the pre-registration template for the new conditions.
6. `docs/REPRODUCING.md` — how to re-run anything, including the claims check.
