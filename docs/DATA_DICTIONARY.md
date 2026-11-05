# Data dictionary

Everything shipped under `data/` is either an input or an output of the measurement
pipeline. Nothing here is derived from a model call at analysis time: the analysis reads
these files and computes.

```
data/
  runs.csv                 normalised manifest, one row per shipped run
  CHECKSUMS.sha256         SHA-256 of every shipped CSV
  runs/out_*/results.csv   one file per condition, 37 directories
  daml/pilot_results.csv   the end-to-end pilot
  corpus/real_chains.json  the 13 real-log chains
  source/                  the author's original Chinese manifest and summary, verbatim
```

---

## 1. `data/runs.csv`

The normalised manifest. The original is preserved at
`data/source/run_manifest_zh.csv`; `runs.csv` is the same information with English column
names and enumerated values, so the analysis does not depend on Chinese header strings.

| Column | Type | Meaning |
|---|---|---|
| `run_id` | str | directory name under `data/runs/` |
| `model` | str | provider model identifier |
| `provider` | `deepseek` \| `zhipu` | vendor |
| `endpoint` | str | base URL used |
| `chains` | int | fact chains per batch (40 synthetic, 13 real-log) |
| `seeds` | int | number of seeds (2 or 3) |
| `delays` | str | comma-separated update delays in days |
| `time_format` | `date` \| `day` \| `none` | timestamp rendering |
| `ctx_order` | `newest_first` \| `oldest_first` \| `random` | record order in the prompt |
| `text_style` | `template` \| `uniform` \| `natural` \| `vary_*` | record rendering |
| `policies` | `all` \| `none` | four review policies, or only the no-review baseline |
| `filler` | str | filler condition (`无` = none, else tail/gap label) |
| `corpus` | `synthetic` \| `real-log` | store builder |
| `probes` | int | model calls in the run |
| `note` | str | the author's note (which table the run supports) |

`probes` is the ground truth for run size: `chains × len(delays) × seeds × n_policies`.
`tests/test_data_integrity.py` checks that it equals the number of non-summary rows.

---

## 2. `data/runs/out_*/results.csv`

UTF-8 with a BOM, so Excel on Windows opens it correctly. Two row types share one schema:

- **probe rows** — one model call. `entity` is the chain's entity name.
- **summary rows** — one batch (delay × seed × policy). `entity` is `__summary__`, and the
  aggregate columns are populated.

One summary row follows each batch of probe rows. A run therefore has
`chains × delays × seeds × policies` probe rows and `delays × seeds × policies` summary
rows.

| Column | Row type | Type | Meaning |
|---|---|---|---|
| `delay` | both | int | days between the update and the query (1, 7, 30, 90) |
| `seed` | both | int | seed index; resamples nuisance variables only |
| `policy` | both | enum | `none` / `recent` / `importance` / `decay` |
| `entity` | both | str | chain entity, or `__summary__` |
| `verdict` | probe | enum | `correct` / `stale` / `unknown` |
| `answer` | probe | str | the model's raw reply, stripped |
| `ctx_entries` | probe | int | records in the queried context (1 or 2 in every shipped run) |
| `correct` | summary | float | fraction of the batch answered with the updated value |
| `stale` | summary | float | fraction answered with the outdated value — the primary metric |
| `unknown` | summary | float | fraction unparsed or errored |
| `reviewed` | summary | int | records selected for review in this batch |
| `archived` | summary | int | records archived (i.e. conflicts removed) |
| `review_chars` | summary | int | characters spent of the review budget |
| `ctx_chars_avg` | summary | float | mean characters per queried context |

On the summary rows, `correct + stale + unknown = 1` exactly. Across all 50,832 probes the
mix is 35,286 correct / 15,414 stale / 132 unknown, so `unknown` is 0.26%.

**A note on `answer`.** It is the raw reply, so a response of `8000` and one of
`端口是 8000。` are both stored and both score `stale`. An answer containing *both* values
scores `correct`, because the updated value is tested first; that affects 331 probes
(0.65%) and is documented in `memdec.scoring`.

---

## 3. `data/daml/pilot_results.csv`

The end-to-end pilot: four memory designs, 40 instances each.

| Column | Type | Meaning |
|---|---|---|
| `design` | enum | `naive_newest_first` / `naive_oldest_first` / `timestamped` / `daml` |
| `seed` | int | scenario seed |
| `scenario` | int | scenario index within the seed |
| `exact` | 0/1 | all 10 manifest fields correct |
| `correct_fields` | int | 0–10 |
| `stale_fields` | int | 0–10; a field carrying a superseded value |
| `raw` | str | first 200 characters of the reply |

`timestamped` and `daml` both score 40/40. With 40 instances the exact interval for each is
[91.2, 100.0], so the two are not distinguishable.

---

## 4. `data/corpus/real_chains.json`

Thirteen update chains extracted from the author's agent session logs.

| Field | Meaning |
|---|---|
| `entity` | `Web GUI` for all 13 chains |
| `attr` | `端口` for all 13 chains |
| `old_value` / `new_value` | five-digit port numbers |
| `old_text` / `new_text` | the log line, verbatim |
| `old_date` / `new_date` | the dates observed in the logs |

Two properties matter for interpreting the paper's real-log row:

1. **One template.** After masking the port number, all 26 record texts are identical. The
   corpus varies a number, not a wording.
2. **The rendered dates are not these dates.** `build_store_real` assigns
   `new_day = 200 − delay` and `old_day = new_day − (2 + i mod 5)`, so the rendered
   timestamp is generated. Five of the thirteen chains have `old_date == new_date`, so the
   logs would not have supported a strict order either.

---

## 5. `data/source/`

The author's original manifest (`run_manifest_zh.csv`) and condition summary
(`all_conditions_zh.md`), unchanged. They are the provenance record for `runs.csv`, and
`tests/test_data_integrity.py` checks that the row counts agree.

---

## 6. `data/CHECKSUMS.sha256`

`sha256  relative/path` per line, covering every CSV under `data/`. A test verifies it, so
an accidental edit to a shipped result file fails CI rather than silently changing a table.

**Four groups of files share a hash.** This is expected, not corruption: when every answer
in a condition is saturated, the per-probe file is fully determined by the chain values, so
two conditions with the same chains serialise identically. See `docs/AUDIT.md` §11 for the
list and the interpretation.

---

## 7. What is *not* here

- **`run_meta.json`.** The original README says 23 runs carry one; none of the 37 do. The
  manifest is the only record of run provenance.
- **Raw HTTP responses.** Only the parsed `answer` string survives, so response ids,
  timestamps and token counts are unrecoverable. New runs written by `memdec` record all of
  this in `run_meta.json`.
- **Prompt text per probe.** Reconstructed deterministically by `memdec.prompts`, which is
  versioned (`PROMPT_VERSION`). A change to the rendering is a data-format change.
