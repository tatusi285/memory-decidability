# Pre-registration protocol

*Template for the conditions proposed in [`ROADMAP.md`](ROADMAP.md). Fill it in and commit
it before running anything. The point is not ceremony: this study's central problem is that
a quantity pinned by the design was read as an empirical result, and a written prediction
is the cheapest protection against repeating that.*

---

## 1. Questions and predictions

State each prediction with its direction **and** a numeric range, before the data exists.
A prediction added afterwards is a description, not a test.

| ID | Question | Prediction | Range | Decides |
|---|---|---|---|---|
| Q1 | Is recency's zero a property of the store? | Recency coverage rises above zero when late writes are introduced | 30–55% at 50% late writes | B2 |
| Q2 | Does a random baseline separate the policies? | Random sits between recency and decay | hit rate 33–43% | Table 4 |
| Q3 | Is importance coverage a function of signal strength? | Coverage increases monotonically with ρ | 35% at ρ=0 to >85% at ρ=1 | B3 |
| Q4 | Is the positional cue anchored at the end of the context? | Prefix fillers are inert; tail fillers degrade | prefix within ±5 pt of k=0 | M6 |
| Q5 | Is the shuffled condition near 50% under matched wording? | Yes, if the rule is positional | 40–60% | M5 |
| Q6 | Does the direction of the positional rule vary across families? | More families show a bimodal split than a continuum | ≥4 of 7 at <10% or >90% | §4.2 |

**Falsifiers.** Write down now what would count as failure: for Q1, coverage staying at 0
under late writes (which would mean the budget, not the ordering, is the binding
constraint); for Q4, prefix fillers degrading as much as tail fillers (which would kill the
anchor claim and replace it with general context dilution).

---

## 2. Conditions

List every condition, its configuration, its seed schedule, and its expected probe count
before running. A condition not listed here does not enter any table.

| Condition | Model | Chains | Seeds | Delays | Order | Wording | Time | Extra flags | Probes |
|---|---|---|---|---|---|---|---|---|---|
| E1 random | deepseek-chat | 40 | 3 | 1,7,30,90 | newest_first | uniform | none | `--policies random` | 480 |
| E2 late | deepseek-chat | 40 | 3 | 1,7,30,90 | newest_first | uniform | none | `--late-duplicates 0.5` | 960 |
| E3 sweep | deepseek-chat | 40 | 3 | 1,7,30,90 | newest_first | uniform | none | `--importance-signal 0…1` | 2 400 |
| E4 prefix | deepseek-chat | 40 | 3 | 1,7,30,90 | newest_first | uniform | none | `--filler-mode prefix --filler-k 1,2,8,16` | 1 920 |
| E5 shuffle | deepseek-chat | 40 | 3 | 1,7,30,90 | random | uniform | none | `--policies none` | 480 |

Total: about 6,240 probes, roughly 1.5 hours at 6-way concurrency, under 5 CNY.

---

## 3. Analysis plan

Fix the analysis before looking at the data. Everything below is already implemented, so
"the analysis" means "run these commands and report these columns".

1. **Primary quantity.** Conflict-hit rate = `archived / reviewed`, with its exact binomial
   interval over chains. Coverage = `archived / 40`. These are model-free.
2. **Secondary quantity.** Stale rate, reported for confirmation only, with the chain-level
   interval. If the positional rule holds, stale ≈ 1 − coverage; a large deviation is
   itself a result and must be reported.
3. **Unit of analysis.** The chain (40). Never pool probes.
4. **Interval.** Clopper–Pearson at the chain level (`memdec.stats.clopper_pearson`).
5. **Multiplicity.** For the E3 sweep, report the monotone trend and its endpoints; do not
   test adjacent pairs. If pairwise claims are made, Holm-correct them
   (`memdec.stats.holm`).
6. **Exclusions.** A condition is excluded only if (a) more than 1% of probes failed with a
   transport error, or (b) the run's `run_meta.json` records an endpoint or model different
   from the plan. Exclusions must be listed with a reason in the paper.

---

## 4. Stopping rule

Run the planned number of seeds. Do not add seeds because a result is close to a threshold,
and do not stop early because it is not. If a condition fails the "expected probes" check,
it is a failed run, not a smaller-n result.

---

## 5. What counts as a result

| Status | Requires |
|---|---|
| Confirmed | Prediction direction correct **and** observed value inside the stated range |
| Directionally supported | Direction correct, value outside the range — report the range change explicitly |
| Falsified | Direction wrong, or the falsifier in §1 fired |
| Inconclusive | Interval spans the decision boundary; report as inconclusive rather than as a trend |

"Directionally supported" is the common outcome and the one most often written up as
"confirmed". Do not.

---

## 6. Deviations log

Append every departure from this document, with the date and the reason. A revision with a
clean deviations log is much easier to defend than one where a reviewer has to guess why a
condition was dropped.

| Date | Condition | Deviation | Reason |
|---|---|---|---|
| | | | |
