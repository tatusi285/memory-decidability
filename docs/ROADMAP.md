# Improvement roadmap

*Companion to [`REVIEW.md`](REVIEW.md). That document says what is wrong; this one says
what to do, in what order, for how much, and how to tell whether it worked.*

---

## 0. How to read this

The plan is staged by **cost per unit of reviewer risk removed**, not by importance. The
first stage costs one working day and no API budget, and it removes the three blockers.
That ordering is deliberate: a paper with a defensible claim and a corrected statistics
section is reviewable; a paper with a beautiful new experiment and `stale = 1 − coverage`
in the abstract is not.

Two facts make the plan much cheaper than it looks:

1. **Archive coverage is model-free.** Review is deterministic reconciliation, so every
   quantity in the maintenance section can be computed without calling a model. The key
   numbers in stage 1 already exist in
   [`tables/table_proposed_controls.md`](tables/table_proposed_controls.md).
2. **The data you already have supports the reframing.** The 2×2 interaction that should
   be the headline (wording × timestamps) is already in `data/runs/out_nat_date_new`. It
   needs a table and a paragraph, not a run.

Where a stage does need model calls, the cost is estimated from the original run's
throughput (6-way concurrency, quota) and rounded up.

---

## 1. Stage 0 — rescope and repair

**Cost:** one working day, 0 CNY, no new data.
**Removes:** blockers B1, B2 (statement), B3 (statement), major M2, M3, M4 (partly), and
all six minor issues.

### 0.1 Replace the central claim

| Where | Now | Replace with |
|---|---|---|
| Abstract | "the stale rate equals one minus archive coverage" | "because archiving removes the only competing record, staleness is fixed by how much of the conflict a policy removes; we therefore measure how well each policy *finds* conflicts against a random baseline" |
| 4.4 | "The relationship is exact: stale rate = 1 − archive coverage." | "The relationship is an identity (Proposition 3), not an empirical result. It holds to machine precision in all 48 cells of this condition. What varies across policies is the conflict-hit rate: 0.0% for recency, 38.5% for random selection, 43.5% for importance, 50.6% for decay." |
| 4.4 | "The decay signal is therefore not doing any work of its own" | "Decay beats random selection by 12.1 points of conflict-hit rate. Whether that is a property of the forgetting curve or of its correlation with record age is not identified here; see the importance sweep in §5." |
| Conclusion | "Maintenance policies matter only as conflict removal" | "Maintenance policies can only act by removing conflicts. Their differences reduce to how reliably they find them, which is measurable and is not implied by their ranking signal." |

### 0.2 Add the 2×2 that should be the headline

Table 1 currently reports template wording only, and the abstract generalises from it. Add
[`tables/table_missing_interaction.md`](tables/table_missing_interaction.md): uniform
template 100.0 → 0.0 with dates; mixed natural wording 65.0 → **21.0** with dates, rising to
**29.2** at a 90-day delay.

Then rewrite:

| Where | Now | Replace with |
|---|---|---|
| Abstract | "With reliable timestamps, staleness is essentially eliminated (at most 0.2%)" | "With comparable timestamps *and* uniform rendering, staleness disappears (0.0%); with timestamps alone and mixed wording it falls only to 21.0%" |
| 4.1 | "The ceiling is not an artifact of easy questions; it is what dates are for." | "The ceiling requires both a comparable timestamp and a uniform rendering: identical dates with mixed wording still leave 21.0% of answers stale, and the rate grows with the update delay." |
| Contributions | "We show that timestamps dominate" | "We show that decidability is a conjunction: a time cue without format uniformity is not sufficient, and format uniformity without a time cue is worse." |

This is the single highest-value edit in the whole plan. It converts the paper's biggest
vulnerability into its most interesting result, and it needs no new data.

### 0.3 Fix the statistics section

- State the unit of analysis: 40 chains (13 for real logs), not 480 queries.
- Report exact intervals over chains (`tables/table1_uncertainty.md` has both columns).
- Delete every `± 0.0` on a saturated cell; a 40/40 cell is [91.2, 100.0].
- Delete the "t = 2.776" constant and the two tables it produced on its own; report the
  corrected intervals.
- Replace "40 chains × 4 delays × 3 seeds = 1,920 queries" with the effective-n framing.
- Say plainly that seeds resample nuisance variables, not chains.

### 0.4 Fix the four arithmetic and wording errors

- Delete the additivity sentence or report the interaction (9.6 + 14.4 + 29.8 predicts
  46.2%; observed 65.0%).
- Delete or re-run the shuffled cell (M5).
- Describe the filler curve as non-monotone (M6), or drop the mechanism paragraph.
- State that importance is randomly assigned and that the decay half-life is a function
  of it (B3).
- State that the real-log timestamps are generated and that the corpus is one template
  (m2, m3).
- Replace the original package's README with this repository's `README.md`: the original
  claims 23 runs carry a `run_meta.json` (none do) and treats 62/62 as reproducibility
  rather than consistency.

### 0.5 Acceptance criteria for stage 0

- [ ] No sentence in the manuscript asserts an identity as an empirical result.
- [ ] The abstract's timestamp claim is qualified by wording, and the 21.0% cell appears
      in a table.
- [ ] Every proportion carries a chain-level interval or an explicit note that it is a
      census of 40 chains.
- [ ] `python -m memdec verify` still reports 62/62 (the published values are unchanged;
      only their interpretation is).
- [ ] A reader can find, in one place, the list of things this study does not establish.

---

## 2. Stage 1 — the cheap controls

**Cost:** about half a day; **0 CNY** for the decisive part, under 3 CNY to confirm the
stale-rate mapping. **Removes:** blockers B2 and B3, and closes M5 and M6.

Read [`tables/table_proposed_controls.md`](tables/table_proposed_controls.md) first: the
coverage numbers for every experiment below are already computed, because review is
deterministic. The runs in this stage exist to confirm that the stale rate tracks coverage
under the positional rule — one condition each is enough.

### E1. Random-selection baseline

The paper has no baseline, so "decay archives 55.4%" has nothing to be compared with.
Uniform random selection hits a conflict 38.5% of the time on this store.

```bash
python -m memdec run --time-format none --ctx-order newest_first --policies random \
    --chains 40 --seeds 3 --delays 1,7,30,90 --out out/e1_random
```

Predicted: reviewed 41.0, archived 15.4, coverage 38.5%, stale ≈ 61.5%.
Confirms: recency is *below* random (0.0 vs 38.5), importance is at random (37.1–44.6),
decay is above it (50.6). That ordering is the new Table 4.

### E2. Break the recency/conflict correlation

```bash
python -m memdec run --time-format none --ctx-order newest_first --policies recent,decay \
    --chains 40 --seeds 3 --delays 1,7,30,90 --late-duplicates 0.5 --out out/e2_late
```

`--late-duplicates 0.5` makes half the outdated records arrive *after* the update — a
mirror or a second agent replaying old state. Predicted: recency coverage rises from 0% to
**47.7%** (hit rate 46.4%), beating random by 7.9 points. Confirms: recency's zero was a
property of the store, not of recency. Reports as: "recency is anti-correlated with
conflict when recency and supersession are positively correlated; the sign reverses when
that correlation is broken."

Note: with late writes the newest record is no longer always the current one, so the
positional rule flips for those chains. Report coverage and hit rate, not stale rate, for
this condition.

### E3. Give importance a signal, and sweep it

```bash
for rho in 0 0.25 0.5 0.75 1; do
  python -m memdec run --time-format none --ctx-order newest_first --policies importance \
      --chains 40 --seeds 3 --delays 1,7,30,90 \
      --importance-mode signal --importance-signal $rho --out out/e3_importance_$rho
done
```

Predicted coverage: 37.1 / 70.8 / 79.8 / 87.5 / **95.8**. Hit rate: 36.0 → 93.5.

This is the experiment that replaces the negative result about decay with a positive one:
**coverage is a function of the correlation between a ranking signal and conflict status,
and of nothing else.** It is a five-point monotone curve, it costs nothing to obtain at the
coverage level, and it explains the original Table 4 in one figure: importance-as-random
sits at the random baseline, decay sits a little above it because age correlates mildly
with supersession.

### E4. Prefix-filler control

```bash
for k in 1 2 8 16; do
  python -m memdec run --time-format none --text-style uniform --ctx-order newest_first \
      --policies none --chains 40 --seeds 3 --delays 1,7,30,90 --filler-k $k \
      --filler-mode prefix --out out/e4_prefix_$k
done
```

The existing filler experiment only appends text after the records, so "the cue is anchored
at the end" is confounded with "more text before the question is worse". If the prefix
condition is inert, the anchor claim survives; if it degrades in proportion to k, the claim
is wrong and the effect is general context dilution. Four conditions, about 1 CNY.

### E5. Shuffled order, matched wording

```bash
python -m memdec run --time-format none --text-style uniform --ctx-order random \
    --policies none --chains 40 --seeds 3 --delays 1,7,30,90 --out out/e5_shuffle_uniform
```

One condition, about 0.3 CNY. Under a pure positional rule this should be about 50%; the
existing mixed-wording cell is 34.8%, which is significantly below 50% and therefore
already suggests the rule is not the whole story. Either way the paper gets a row it can
defend.

### 2.1 Acceptance criteria for stage 1

- [ ] Table 4 has a random baseline column, and every policy is reported against it.
- [ ] Recency's zero is reported together with its cap and with the late-write reversal.
- [ ] Importance coverage is reported as a function of signal strength, with the random
      (ρ = 0) end point at the baseline.
- [ ] The filler section either has a prefix control or has no mechanism claim.
- [ ] The shuffled row is either matched or absent.

---

## 3. Stage 2 — robustness

**Cost:** about one day, roughly 8–15 CNY. **Removes:** the remaining generality objections.

### R1. More model families

Four configurations from two providers cannot support "the direction is a property of the
model". Add at least three more families from at least two more providers (Qwen, Llama,
Mistral, or a local model). One condition each:

```bash
python -m memdec run --model <model> --base-url <endpoint> --time-format none \
    --ctx-order newest_first --policies none --chains 30 --seeds 2 \
    --delays 1,7,30,90 --out out/r1_<model>
```

The claim to test is not "DeepSeek reads last" — that is a fact about DeepSeek — but
**whether the direction is a stable, measurable property that can be surveyed**. With seven
to ten families the paper can report a distribution instead of two anecdotes, and the
practical advice in P3 ("measure the placement per model") becomes actionable.

### R2. Retrieval competition (M1)

The current context is one or two records. Add a condition where the slot has 4–8 records,
some distractors share the entity, and the retrieval budget forces truncation. This is the
only change that makes the "retrieval budget" language in section 5.2 true, and it tests
whether the positional rule survives competition for a slot in the context.

```bash
python -m memdec run --time-format none --ctx-order newest_first --policies none \
    --chains 40 --seeds 3 --ctx-budget 60 --out out/r2_competition
```

(`--ctx-budget 60` forces truncation; the exact value needs one exploratory pass.)

### R3. Three-plus record chains

Two records is the minimal conflict. Three or four records, with two supersession events,
tests whether the rule composes. Cheap and directly addresses "longer conflict chains" in
the limitations.

### 3.1 Acceptance criteria for stage 2

- [ ] The direction finding is reported over at least six families, as a distribution.
- [ ] Either the retrieval-budget language is removed, or R2 supports it.
- [ ] The limitations section says which of these was done and which was not.

---

## 4. Stage 3 — optional extensions

Only after stages 0–2. These are the ones that would make the paper interesting to a
systems audience rather than an evaluation audience, and each is a project in itself.

- **A token-matched end-to-end comparison.** The current pilot cannot separate DAML from a
  timestamped baseline. Fix by giving the baseline the same 10-record budget, and by adding
  a task where archiving helps but truncation hurts (multi-hop, or a budget small enough
  that truncation drops needed slots).
- **LLM-based review.** The paper's review is deterministic reconciliation, which the
  limitations acknowledge. Replacing it with an LLM that rewrites or merges records
  introduces the cost and failure modes that matter in deployment.
- **A benchmark contribution.** Turn the 2×2 into a small diagnostic suite — presentation
  conditions crossed with conflict depth — and release it. That is a different paper, and a
  more citable one.

---

## 5. Manuscript edit sheet

One row per sentence that has to change. Anything not listed keeps its current wording.

| § | Current | Replacement |
|---|---|---|
| Abstract | "With reliable timestamps, staleness is essentially eliminated (at most 0.2%)." | "With comparable timestamps and uniform rendering, staleness disappears (0.0% of 480 probes; 0 of 40 chains); with timestamps but mixed wording it falls only to 21.0%, and the rate grows with the update delay to 29.2% at 90 days." |
| Abstract | "The stale rate equals one minus archive coverage." | "Because archiving removes the only competing record, the stale rate is pinned to one minus archive coverage — an identity, not an effect. What separates policies is the conflict-hit rate of their selection: 0.0% (recency), 38.5% (random), 43.5% (importance), 50.6% (decay)." |
| Abstract | "a decidability-aware memory layer built from these rules reaches 100% exact answers ... where an append-only log reaches 0%" | add "and matches a one-line timestamped baseline, at 44% fewer records" |
| §4.2 | "a shuffled order falls between the extremes (34.8%, measured under mixed wording)" | "under mixed wording, where the matched baseline is 65.0%, a shuffled order falls to 34.8%" — or delete and use E5 |
| §4.3 | "The effects are roughly additive (9.6 + 14.4 + 29.8 ≈ 53 points), with some overlap when combined." | "The single-factor effects do not compose additively: summing them predicts 46.2%, while the combined condition is 65.0%. We report the interaction rather than a sum." |
| §4.4 | "all four policies review essentially the same number of records within the same budget (0, 41.3, 41.0 and 41.5), but they archive very different numbers" | keep, then add "Recency's zero is structural: the 40 updated records are the newest entries and nearly fill the budget, so recency cannot reach a conflict at this budget." |
| §4.6 | "The relation is not a smooth decay: appending text first weakens the cue slightly and then, past a threshold, degrades it substantially." | "The relation is not monotone: one filler reduces staleness to 83.1%, eight bring it back to 94.8% (trend z = +4.99 over k = 1..8), and sixteen collapse it to 62.3%. We report the shape without a mechanism claim, and test the anchor hypothesis with a prefix control." |
| §5.3 | "DAML matches the timestamped design on accuracy while emitting 10 of 18 records" | keep, and add "the two designs are not token-matched, so the reduction is a consequence of the manipulation rather than a measured cost benefit; a token-matched comparison is future work." |
| §3.5 | "Each condition is run with 40 chains, 4 delays and 3 random seeds" | "Each condition contains 40 chains measured at four delays and three seeds. Because a chain returns the same verdict at every repeat, the effective sample size is 40; intervals are exact binomial intervals over chains." |
| §2 | (no temporal-KB citations) | add a paragraph positioning conflict adjudication against temporal/bitemporal knowledge bases and 2024–2025 memory systems with edge invalidation |
| §3.1 | "the model receives the records retrieved for that entity" | "retrieval is per slot: the context contains that slot's one or two live records. Distractor records consume review budget but never appear in a queried context." |

---

## 6. Venue plan

| Track | Requirements | Timeline | Honest assessment |
|---|---|---|---|
| **Workshop** (agents/memory/evaluation workshops at ACL, NeurIPS, ICLR) | Stages 0–1 | 2–3 weeks | Achievable, and the right first target. The reframed claim is a good fit for a workshop that rewards negative and methodological results. |
| **arXiv preprint** | Stages 0–2 | 4–6 weeks | Worth doing once the blockers are gone. A preprint is how this work gets cited while a journal decision is pending. |
| **Chinese journal** (计算机应用 / 软件学报 / 中文信息学报) | Stages 0–2, plus more models and a Chinese-language task | 2–3 months | Plausible. The 2×2 interaction and the cross-family direction survey are the parts a Chinese reviewer will value. |
| **Top-tier main conference** (ACL/EMNLP/NeurIPS) | Not reachable with this design | — | The task is two records, four configurations and one synthetic corpus. A main-conference reviewer will ask for a benchmark-scale evaluation, which is Stage 3 and a different paper. Saying so now saves six months. |

The version you have today is not submittable anywhere, for one reason: `stale = 1 −
coverage` is in the abstract. After stage 0 it is submittable to a workshop. Stages 1–2
make it hard to reject on methodological grounds.

---

## 7. Four-week schedule

| Week | Work | Output |
|---|---|---|
| 1 | Stage 0: rewrite abstract and 4.4, add the 2×2, replace statistics, fix the four arithmetic/wording errors | Revised draft, no new data |
| 2 | Stage 1: run E1–E5, regenerate tables and figures with `python -m memdec build` | New Table 4, importance sweep figure, filler control |
| 3 | Stage 2: R1 (more families) and R2 (retrieval competition) | Direction survey, competition condition |
| 4 | Rewrite introduction and related work around P1–P3; internal review; submit | Workshop submission |

The work in week 1 is the one that matters. If only one week is available, do week 1.

---

## 8. Definition of done

A checklist for "this is ready to be a public artifact and a submitted paper".

**Data and code**

- [ ] `python -m memdec verify` reports 62/62 (or 62 plus whatever new claims were added).
- [ ] `python -m memdec build` regenerates every table and figure with no diff in `docs/`.
- [ ] `python -m unittest discover -s tests -t .` passes on a clean checkout.
- [ ] CI is green on all supported Python versions.
- [ ] Every new condition has a `run_meta.json` with the model, endpoint, prompt version,
      seed schedule and timestamps.
- [ ] No API key, absolute path or session transcript anywhere under `data/`.

**Manuscript**

- [ ] The abstract's quantitative claims each map to a table cell in the artifact.
- [ ] No identity is presented as an empirical result.
- [ ] Every proportion has an interval or an explicit census note.
- [ ] Limitations names the two-record context, the four-configuration model sample, the
      single-template real corpus, and the deterministic review.
- [ ] The related-work section cites temporal knowledge bases and 2024–2025 memory systems
      with conflict handling.

**Artifact release**

- [ ] `README.md` states what the artifact verifies and what it does not.
- [ ] `docs/REVIEW.md` and `docs/AUDIT.md` are committed and linked from the README.
- [ ] A tagged release (e.g. `v1.1.0`) with a DOI (Zenodo) if the venue asks for one.
- [ ] `CITATION.cff` has the final title and author list.
