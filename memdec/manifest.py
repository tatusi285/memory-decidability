"""Manifest and result-file access.

``data/runs.csv`` is the normalised manifest: one row per shipped run, with the
sample size, model, endpoint and the five design switches.  ``data/source/`` keeps
the author's original Chinese manifest untouched so the normalisation can be
audited.

The shipped ``results.csv`` files follow one schema (below).  Per-probe rows have
``entity`` = the chain entity; every batch (delay x seed x policy) is followed by a
single summary row with ``entity == "__summary__"`` that carries the batch rates and
the review counts.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import paths

SUMMARY_ENTITY = "__summary__"

RESULT_COLUMNS: tuple[str, ...] = (
    "delay", "seed", "policy", "entity", "verdict", "answer", "ctx_entries",
    "correct", "stale", "unknown", "reviewed", "archived", "review_chars",
    "ctx_chars_avg",
)


@dataclass(frozen=True)
class RunSpec:
    """One row of the manifest."""

    run_id: str
    model: str
    provider: str
    endpoint: str
    chains: int
    seeds: int
    delays: str
    time_format: str
    ctx_order: str
    text_style: str
    policies: str
    filler: str
    corpus: str
    probes: int
    note: str

    @property
    def delay_list(self) -> list[int]:
        return [int(x) for x in self.delays.split(",") if x.strip()]

    @property
    def is_filler_run(self) -> bool:
        return self.filler != "无"

    @property
    def uses_timestamp(self) -> bool:
        return self.time_format != "none"


@lru_cache(maxsize=1)
def load_runs() -> dict[str, RunSpec]:
    """All shipped runs, keyed by run id, in manifest order."""
    path = paths.data_dir() / "runs.csv"
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    specs: dict[str, RunSpec] = {}
    for row in rows:
        spec = RunSpec(
            run_id=row["run_id"], model=row["model"], provider=row["provider"],
            endpoint=row["endpoint"], chains=int(row["chains"]), seeds=int(row["seeds"]),
            delays=row["delays"], time_format=row["time_format"],
            ctx_order=row["ctx_order"], text_style=row["text_style"],
            policies=row["policies"], filler=row["filler"], corpus=row["corpus"],
            probes=int(row["probes"]), note=row["note"],
        )
        specs[spec.run_id] = spec
    return specs


def result_path(run_id: str) -> Path:
    return paths.runs_dir() / run_id / "results.csv"


def read_rows(run_id: str) -> list[dict]:
    """Every row of one run's ``results.csv`` (probe rows and summary rows)."""
    path = result_path(run_id)
    if not path.is_file():
        raise FileNotFoundError(f"no results.csv for run {run_id!r} at {path}")
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def summary_rows(run_id: str) -> list[dict]:
    return [r for r in read_rows(run_id) if r["entity"] == SUMMARY_ENTITY]


def probe_rows(run_id: str) -> list[dict]:
    return [r for r in read_rows(run_id) if r["entity"] != SUMMARY_ENTITY]


def batch_rates(run_id: str, policy: str = "none", column: str = "stale",
                delay: int | None = None) -> list[float]:
    """Per-batch rates (one value per delay x seed) as fractions in [0, 1]."""
    rows = summary_rows(run_id)
    if delay is not None:
        rows = [r for r in rows if int(r["delay"]) == delay]
    values = []
    for row in rows:
        if row["policy"] != policy:
            continue
        raw = row.get(column, "")
        if raw in ("", None):
            continue
        values.append(float(raw))
    return values


def mean_rate(run_id: str, policy: str = "none", column: str = "stale",
              delay: int | None = None) -> float | None:
    values = batch_rates(run_id, policy, column, delay)
    return sum(values) / len(values) if values else None


def count_mean(run_id: str, policy: str, column: str) -> float | None:
    """Mean of a per-batch count such as ``reviewed`` or ``archived``."""
    rows = [r for r in summary_rows(run_id) if r["policy"] == policy]
    values = [float(r[column]) for r in rows if r.get(column) not in ("", None)]
    return sum(values) / len(values) if values else None


def probes_in(run_id: str) -> int:
    return len(probe_rows(run_id))


def run_meta(run_id: str) -> dict | None:
    path = paths.runs_dir() / run_id / "run_meta.json"
    if not path.is_file():
        return None
    import json
    return json.loads(path.read_text(encoding="utf-8"))
