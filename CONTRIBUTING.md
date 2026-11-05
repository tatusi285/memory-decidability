# Contributing

This repository is a research artifact, so the bar for a change is reproducibility rather
than features. A pull request is welcome if it makes a number easier to check, a claim
easier to falsify, or a run easier to reproduce.

## Before you start

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -t . -v
python -m memdec build
```

All three should pass on a clean checkout without network access.

## The rules that matter

1. **Never edit a file under `data/`.** Those files are the evidence. If a number is wrong,
   say so in an issue with the computation; do not adjust the input. Changing a shipped
   result file breaks `data/CHECKSUMS.sha256`, and that is intentional.
2. **Generated files under `docs/` are committed.** Run `python -m memdec build` and commit
   the diff. A table that no longer matches the data is a bug.
3. **No new runtime dependencies.** Measurements and analysis use the standard library.
   A plotting library, a statistics package or a dataframe would make the artifact harder
   to run on a locked-down machine, which is the one thing it must not be.
4. **A prompt change is a data-format change.** Bump `memdec.prompts.PROMPT_VERSION` and say
   so in `CHANGELOG.md`, because results produced under different versions are not
   comparable.
5. **Do not weaken a test to make it pass.** Several tests pin defects in the shipped
   artifact on purpose (the byte-identical files, the missing `run_meta.json`). If a
   finding is resolved, update the test and `docs/AUDIT.md` together.

## Good first contributions

- Add a model family to the direction survey (`ROADMAP.md` R1) and commit the run directory
  with its `run_meta.json`.
- Port the figures to a second renderer (e.g. matplotlib) behind an optional extra, keeping
  the SVG output as the committed one.
- Add an English-language prompt condition, so the cross-lingual limitation can be tested
  rather than declared.
- Improve the scoring rule with a documented strict mode that treats "both values" as
  ambiguous rather than correct.

## Reporting a problem

Open an issue with:

- the command you ran,
- `python -m memdec info` output,
- what you expected and what happened.

If the problem is a number that does not reproduce, include the recomputation.
`python -m memdec verify` output is ideal.

## Style

- Python 3.10+, type hints on public functions, docstrings that explain *why*.
- `ruff check memdec tests` must pass; the config is in `pyproject.toml`.
- Prose: prefer a measured statement over a confident one. This artifact exists because a
  confident statement was wrong.
