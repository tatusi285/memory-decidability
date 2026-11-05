# Limitations

The manuscript already has a limitations section. This one is for the artifact, and it is
written to be useful rather than diplomatic: it lists what the data can support, what it
cannot, and which of the two a given claim needs.

---

## What the artifact can establish

- **Internal consistency.** All 62 published values follow from `data/`. `python -m memdec
  verify` shows the mapping, cell by cell.
- **Deterministic replay.** The review accounting and all 1,920 verdicts of the core grid
  follow from the manifest alone. `tests/test_replay.py` demonstrates it.
- **Design properties.** Context size, the archive-coverage identity, the conflict-hit
  rates, the recency cap, the effective sample size. These are facts about the experiment,
  computed from the experiment, and they do not depend on any model.
- **Effect sizes as measured.** The contrasts are large enough (0 vs 100 percentage points)
  that the ±1–3 point provider drift cannot reorder them.

## What it cannot establish

- **Replication.** No model was called to build this artifact. Whether a fresh run
  reproduces the verdicts is an open question, and the answer will include 1–3 points of
  noise that the shipped files do not contain.
- **Generality across models.** Four configurations from two providers. The direction of
  the positional rule varies across them, which is the finding; the *distribution* of that
  direction across model families is unknown and needs the survey in `ROADMAP.md` R1.
- **Generality across tasks.** Single-hop, one slot, two live records, short Chinese
  prompts, short answers. Multi-hop, aggregation, longer conflict chains and
  English-language prompts are all untested.
- **External validity of the corpus.** The synthetic store is generated. The "real" corpus
  is 13 chains of one attribute of one application, in one sentence form, from one user.
- **Deployment claims.** There is no cost, latency, or user-satisfaction measurement, and
  the maintenance budget is in characters rather than tokens or money.

## Threats to validity, by type

**Construct.** "Stale rate" measures the fraction of answers that echo the outdated value.
It is a clean operationalisation of "the agent used the wrong memory", but it says nothing
about whether the agent *acted* on it. The `unknown` bucket is 0.26% and concentrated in
the filler conditions, so it cannot be masking much — but it is a bucket, not a measurement.

**Internal.** The design has one confound that the paper does not currently state: the
updated record is always the newest entry, which is what makes recency unable to reach a
conflict. That is not an accident of the code; it is what "update" means. Any conclusion
about ranking policies has to be conditional on it, which is why `ROADMAP.md` E2 exists.

A second confound: importance is random, and the decay half-life is a function of
importance, so "importance-first" and "decay-first" are not independent treatments. The
paper contrasts them as if they were.

**Statistical.** The effective sample size is the chain count (40), not the probe count
(480). Intervals computed over probes are about 3.5× too narrow. Seeds resample nuisance
variables, not chains, and the original intervals used a single hard-coded `t = 2.776`
regardless of sample size. All three are corrected in `docs/tables/` and discussed in
`docs/REVIEW.md` §5. The original 3-seed schedule also means some conditions have `n = 2`
batches, which cannot support an interval at all.

**External.** See "generality" above. The one thing that does transfer is the *mechanism* —
a positional rule that is model-specific and deterministic — because it is visible in every
configuration tested and has a clean per-chain signature (39 of 40 chains are delay-invariant
for GLM-4-Plus).

## Known defects in the shipped artifact

These are documented rather than fixed, because fixing them would change the data that the
manuscript's numbers come from.

| Defect | Consequence | Where it matters |
|---|---|---|
| No `run_meta.json` in any of the 37 runs | run provenance rests on the hand-written manifest | provenance claims |
| Four hash-identical groups across models and conditions | the artifact cannot attest separate execution | independence of conditions |
| `out_fill2_gap_1` and `out_fill2_gap_8` are byte-identical to `out_fill2_tail_0` | the "gap is exactly inert" claim has no independent runs behind it | §4.6 |
| Real-log probes all carry `entity = "Web GUI"` | per-chain breakdown of the real-log row is impossible from `results.csv` | §4.5 |
| Rendered real-log timestamps are synthetic | the "with dates" row does not test the logs' dates | §4.5 |
| `answer` is stored without response metadata | no way to audit a parse after the fact | scoring |

## How to use this list

If a claim needs replication, run it. If it needs generality, run the survey. If it needs
only internal consistency, `verify` is sufficient and takes two seconds.

The failure mode to avoid is the one this artifact exists to catch: treating a property that
is fixed by the design as though it were a measurement of the world.
