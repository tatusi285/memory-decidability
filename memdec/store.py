"""The memory store and the two corpora.

A store is a flat list of :class:`Entry` records plus the :class:`Chain` objects
that say which pair of records conflicts.  Two builders exist:

``build_store``
    Synthetic.  40 chains (``服务00``..``服务39``), each with an outdated and an
    updated value, plus 24 distractor records that only ever consume review budget.
``build_store_real``
    Thirteen chains mined from the author's agent session logs.  The record *text*
    is verbatim from the log lines; the timestamps are synthetic (see the note in
    :func:`build_store_real`).

Both builders are deterministic given ``seed`` and ``delay``, which is what makes
the offline replay in ``tests/test_replay.py`` possible.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from .prompts import NOW_DAY, RenderCfg, record_text

#: Distractor count is fixed at 24 in both the synthetic store and the original run.
N_DECOYS = 24


def _clip01(value: float) -> float:
    return min(1.0, max(0.0, value))


@dataclass
class Entry:
    """One memory record."""

    eid: str
    entity: str
    attr: str
    value: str
    day: float
    importance: float
    superseded_by: str | None = None
    archived: bool = False
    last_reviewed: float | None = None
    raw_text: str | None = None
    scope: str = ""
    chain_id: str = ""

    def text(self, cfg: RenderCfg) -> str:
        return record_text(
            self.entity, self.attr, self.value, self.day, self.eid,
            cfg.text_style, cfg.time_format, self.raw_text,
        )

    def render(self, cfg: RenderCfg) -> str:
        return self.text(cfg)


@dataclass
class Chain:
    """A (slot, outdated record, updated record) triple under test."""

    entity: str
    attr: str
    old_value: str
    new_value: str
    old_id: str
    new_id: str
    chain_id: str = ""
    scope: str = ""

    def __post_init__(self) -> None:
        if self.old_value == self.new_value:
            raise ValueError("a chain needs two distinct values")


@dataclass
class Store:
    entries: list[Entry] = field(default_factory=list)
    chains: list[Chain] = field(default_factory=list)

    def by_id(self, eid: str) -> Entry:
        for entry in self.entries:
            if entry.eid == eid:
                return entry
        raise KeyError(eid)

    def live(self) -> list[Entry]:
        return [e for e in self.entries if not e.archived]

    def total_chars(self, cfg: RenderCfg) -> int:
        return sum(len(e.text(cfg)) for e in self.entries)


def build_store(seed: int, n_chains: int, delay: float, n_decoys: int = N_DECOYS,
                importance_mode: str = "random",
                importance_signal: float = 0.0,
                late_duplicates: float = 0.0) -> Store:
    """Synthetic store.

    Values are ``8000 + 7i`` (outdated) and ``9000 + 7i`` (updated), so every chain
    has two distinct, equally plausible four-digit values.

    ``delay`` is coerced to ``float`` before seeding.  The store's RNG is seeded from
    the string ``f"{seed}-{delay}"``, so passing ``1`` instead of ``1.0`` silently
    produces a *different* store; the original runner always passed a float.  This
    single character is the difference between a replay that matches the shipped data
    and one that does not.

    Three optional manipulations exist for the experiments in ``docs/ROADMAP.md``.  All
    are off by default and, when off, consume no random numbers, so the shipped
    conditions replay exactly.

    ``importance_mode`` / ``importance_signal``
        ``"random"`` is the shipped design: importance is drawn from a small uniform
        set, independently of which record is current, so an importance-ordered policy
        is a random prior with a tie-break.  ``"signal"`` makes importance correlate
        with supersession at strength ``importance_signal`` in [0, 1]: the outdated
        record tends high, the updated record tends low.  The modelling assumption is
        that a record is important because slots that matter get reconfigured, so the
        superseded value is more likely to be the salient one -- which is the only
        reason reviewing old records can help at all.  Sweeping the strength separates
        "importance helps" from "importance is a useful proxy for conflict".

    ``late_duplicates``
        Fraction of chains for which the outdated record is written *after* the update
        -- a late write of a stale value, as happens when a mirror, a cache or a second
        agent replays old state.  The shipped design sets this to 0, which is what makes
        the updated record the newest entry and leaves recency unable to reach a
        conflict.  Setting it above 0 breaks that correlation (blocker B2).
    """
    if importance_mode not in ("random", "signal"):
        raise ValueError(f"unknown importance_mode {importance_mode!r}")
    if not 0.0 <= importance_signal <= 1.0:
        raise ValueError("importance_signal must be in [0, 1]")
    delay = float(delay)
    rng = random.Random(f"{seed}-{delay}")
    entries: list[Entry] = []
    chains: list[Chain] = []

    for i in range(n_chains):
        entity = f"服务{i:02d}"
        attr = "端口"
        old_val = f"{8000 + i * 7}"
        new_val = f"{9000 + i * 7}"
        new_day = NOW_DAY - delay
        old_day = new_day - rng.uniform(8, 45)
        if late_duplicates > 0.0 and rng.random() < late_duplicates:
            # The stale value arrives late; it is newer in write time but not current.
            old_day = new_day + rng.uniform(2, 10)
        if importance_mode == "signal":
            shift = 0.45 * importance_signal
            imp_old = _clip01(0.5 + shift + rng.uniform(-0.15, 0.15))
            imp_new = _clip01(0.5 - shift + rng.uniform(-0.15, 0.15))
        else:
            imp_new = rng.choice([0.9, 0.7, 0.55, 0.35])
            imp_old = rng.choice([0.9, 0.7, 0.5, 0.35])
        old = Entry(f"o{i}", entity, attr, old_val, old_day, imp_old, chain_id=f"c{i}")
        new = Entry(f"n{i}", entity, attr, new_val, new_day, imp_new, chain_id=f"c{i}")
        old.superseded_by = new.eid
        entries += [old, new]
        chains.append(Chain(entity, attr, old_val, new_val, old.eid, new.eid,
                            chain_id=f"c{i}"))

    for j in range(n_decoys):
        entity = f"杂项{j:02d}"
        attr = rng.choice(["负责人", "位置", "备注", "别名"])
        entries.append(Entry(
            f"d{j}", entity, attr,
            rng.choice(["张三", "机柜A", "已迁移", "内部系统"]),
            NOW_DAY - rng.uniform(1, 110),
            rng.uniform(0.2, 0.9),
        ))
    return Store(entries, chains)


def load_real_chains(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_store_real(seed: int, chains_json: list[dict], delay: float) -> Store:
    """Real-log store.

    The record text is the original log line, verbatim.  Two documented departures
    from "verbatim" that the paper should state explicitly:

    * the rendered record carries a *synthetic* ``[YYYY-MM-DD]`` prefix, because
      ``old_day = new_day - gap`` and ``new_day = 200 - delay``; the logs' own dates
      are never rendered;
    * several chains have ``old_date == new_date`` in the source logs, so the
      corpus does not actually satisfy the strict ordering the task assumes.

    All 13 chains share the entity name ``Web GUI`` and the attribute ``端口``, and
    the templated log line is identical apart from the port number.  The corpus
    therefore tests one sentence form, not a distribution of forms.
    """
    delay = float(delay)
    rng = random.Random(f"{seed}-{delay}-real")
    entries: list[Entry] = []
    chains: list[Chain] = []

    for i, c in enumerate(chains_json):
        gap = 2 + (i % 5)
        new_day = NOW_DAY - delay
        old_day = new_day - gap
        imp = rng.choice([0.9, 0.7, 0.5])
        cid = f"c{i}"
        old = Entry(f"ro{i}", c["entity"], c["attr"], c["old_value"], old_day, imp,
                    raw_text=c["old_text"], scope=cid, chain_id=cid)
        new = Entry(f"rn{i}", c["entity"], c["attr"], c["new_value"], new_day, imp,
                    raw_text=c["new_text"], scope=cid, chain_id=cid)
        old.superseded_by = new.eid
        entries += [old, new]
        chains.append(Chain(c["entity"], c["attr"], c["old_value"], c["new_value"],
                            old.eid, new.eid, chain_id=cid, scope=cid))
    return Store(entries, chains)
