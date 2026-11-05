# Changelog

All notable changes to this artifact are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

A change to `memdec.prompts.PROMPT_VERSION` is a data-format change: results produced
under different prompt versions are not comparable.

## [1.0.0] - 2026-11-04

First release accompanying the manuscript *Decidability Before Maintenance*.

### Added

- `memdec` package: store builders, four review policies, prompt rendering, the
  measurement runner, an OpenAI-compatible client with retries, and a deterministic
  offline rule simulator for pipeline tests.
- `python -m memdec verify`: recomputes the 62 values the manuscript reports and
  prints a pass/fail table. All 62 reproduce.
- `python -m memdec audit`: a design audit covering determinism, effective sample
  size, the archive-coverage identity, conflict selectivity against a random baseline,
  the interval audit, the filler curve, the end-to-end ceiling and artifact integrity.
- `python -m memdec tables` / `figures`: every table as Markdown and every figure as
  SVG, generated from `data/` with no third-party dependency.
- 109 unit tests, including a replay that reproduces the shipped review counts and all
  1,920 verdicts of the core grid from the manifest alone.
- `data/CHECKSUMS.sha256` and a test that verifies it.
- Documentation: review, roadmap, pre-registration protocol, reproduction guide, data
  dictionary, and limitations.

### Fixed relative to the original package

- The review-budget accounting now replays exactly. The original store's RNG is seeded
  from the string `f"{seed}-{delay}"`, so passing `1` instead of `1.0` silently builds
  a different store; the builder now coerces the delay to `float`.
- The end-to-end script no longer hard-codes an absolute Windows output path.
- Confidence intervals use the correct Student-t critical value for each sample size
  instead of a single hard-coded `t = 2.776`.
- `results.csv` keeps the original 14-column schema, so old and new runs remain
  interchangeable.

### Known limitations

- `run_meta.json` is absent for all 37 shipped runs, although the original README
  states that 23 have one. The manifest is the only record of run provenance.
- Four groups of result files are byte-identical. This is expected when every answer
  is saturated, but it means the artifact cannot independently attest that those
  conditions were executed separately.
