# Reproducing the results

Two different things can be reproduced here, and they have different requirements.

| What | Needs | Time | Command |
|---|---|---|---|
| **Consistency** — the manuscript's numbers follow from `data/` | Python 3.10+ only | 2 s | `python -m memdec verify` |
| **Replay** — `data/` follows from the design | Python 3.10+ only | 5 s | `python -m unittest tests.test_replay` |
| **Replication** — the verdicts follow from fresh model calls | an API key and quota | 4 h / ~20 CNY | see §4 |
| **New conditions** — the roadmap experiments | an API key | 1.5 h / ~5 CNY | see [`ROADMAP.md`](ROADMAP.md) |

No third-party Python package is required for the first two. That is deliberate: a reviewer
on a locked-down machine should be able to check the arithmetic.

---

## 1. Consistency check

```bash
python -m memdec verify
```

Recomputes all 62 published values from `data/runs/` and `data/daml/`, prints a pass/fail
table, writes `docs/CLAIMS.md`, and exits non-zero if anything disagrees. It also prints the
values that are in the data but not in the paper, and the claims the audit disputes.

**What a pass means:** the manuscript is internally consistent with its own results.
**What it does not mean:** that the results are correct or that the experiments were run.
The author's original checker did the same thing; this one just says so.

---

## 2. Deterministic replay

```bash
python -m unittest tests.test_replay -v
```

This is the stronger check. It rebuilds every store from the manifest, re-applies each
review policy, re-assembles the retrieved context, and compares against the shipped
`results.csv`:

- `reviewed` and `archived` match **exactly** for all 4 policies × 4 delays × 3 seeds in
  each core condition;
- all **1,920** verdicts in `out_live_bare` and `out_live_bare_rev` are predicted by a
  single rule — a one-record context yields that record, a two-record context yields the
  last one.

If either fails, the shipped data and the published description of the pipeline have
diverged.

### The trap that this test exists to catch

The store's RNG is seeded from the string `f"{seed}-{delay}"`. Passing `1` instead of `1.0`
produces a completely different store. The original runner always passed a float, because
it parsed delays with `float(...)`. `memdec.store.build_store` now coerces the delay, so
both spellings agree — but if you re-implement the pipeline, this is the line that will
cost you a day.

---

## 3. Regenerating tables and figures

```bash
python -m memdec build        # verify + audit + tables + figures
```

Everything is written under `docs/`, not a scratch directory, so that the generated
material is visible on GitHub and so that CI can fail when a regeneration changes a byte.
The generated files are committed; a stale table is a bug.

| Output | Contents |
|---|---|
| `docs/AUDIT.md` | the design audit |
| `docs/CLAIMS.md` | the claim-verification table |
| `docs/tables/*.md` | every table, plus both uncertainty columns |
| `docs/figures/*.svg` | three figures, no plotting library |

`MEMDEC_DOCS` and `MEMDEC_OUT` override the output locations.

---

## 4. Replicating a measurement

```bash
export MEMDEC_API_KEY="..."      # or DEEPSEEK_API_KEY / OPENAI_API_KEY
```

The core condition, which the paper calls "no timestamp, newest first":

```bash
python -m memdec run \
    --model deepseek-chat --base-url https://api.deepseek.com/v1 \
    --time-format none --ctx-order newest_first --text-style template \
    --chains 40 --seeds 3 --delays 1,7,30,90 \
    --policies none,recent,importance,decay \
    --concurrency 6 --out out/recheck_bare
```

Expected: `reviewed` 0 / 41.3 / 41.0 / 41.5, `archived` 0 / 0 / 17.8 / 21.0, stale rate
100.0 / 100.0 / 55.4 / 47.5. The review counts are deterministic and must match to the
decimal; the stale rates may drift by 1–3 points because `temperature = 0` is not
bit-reproducible on the provider side.

The condition that contradicts the abstract, and which the paper should add:

```bash
python -m memdec run --time-format date --text-style natural \
    --chains 40 --seeds 3 --delays 1,7,30,90 --policies none --out out/recheck_date_natural
```

Expected: 21.0% overall (13.3 / 19.2 / 22.5 / 29.2 by delay). If you get 0%, your run is
not reproducing the one in `data/runs/out_nat_date_new`.

### Cost

| Grid | Calls | Wall clock (6-way) | Cost |
|---|---|---|---|
| One core condition, 4 policies | 1 920 | ~25 min | ~1.5 CNY |
| All 29 main conditions | ~47 000 | ~4 h | ~15 CNY |
| The five roadmap conditions | ~6 200 | ~1.5 h | ~5 CNY |

Review accounting is model-free, so the coverage and conflict-hit numbers in
[`tables/table_proposed_controls.md`](tables/table_proposed_controls.md) cost nothing at
all.

---

## 5. Checking without a key

```bash
python -m memdec run --offline --chains 12 --seeds 1 --delays 1 --out out/smoke
```

`--offline` replaces the model with a deterministic rule simulator (answer = last visible
record). It exercises prompt assembly, scoring, aggregation and file writing. The run
records `"simulated": true` in `run_meta.json` and the CLI prints a warning; those numbers
are a plumbing test and must never be reported.

---

## 6. Environment details

| Item | Value |
|---|---|
| Python | 3.10 – 3.13, standard library only |
| Runtime dependencies | none |
| Optional | `pytest`, `ruff` (dev extras) |
| OS | anything; CI runs Ubuntu on four Python versions |
| Network | only for `memdec run` without `--offline` |

The original measurements were produced on Windows with Python 3.12, using
`urllib.request` with `Connection: close` and four retries with exponential backoff.
`memdec.client.ChatClient` reproduces that behaviour, including treating a failed call as
`unknown` rather than aborting the run.

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `could not locate the repository root` | running from outside the checkout | `cd` to the repo, or set `MEMDEC_ROOT` |
| Replay counts differ by a few records | delay passed as `int`, not `float` | the builder coerces; check any re-implementation |
| `--live needs an API key` (from an older script) | no key in the environment | set `MEMDEC_API_KEY`; `--offline` needs none |
| Stale rates differ by 1–3 points | provider-side non-determinism | expected; the review counts are the exact part |
| A table renders as a wall of text | a pipe character in a cell | values are ASCII; check for `|` in a note |
| CI fails on `git diff --exit-code docs/` | `docs/` is stale | run `python -m memdec build` and commit |
