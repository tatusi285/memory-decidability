"""Review policies.

Four selection functions spend an identical budget on an identical store; the only
thing that varies is *which records get reviewed*.  Review itself is deterministic
reconciliation (archive if superseded, else refresh the timestamp), which isolates
the selection question from the question of how an LLM would rewrite memory.

Three structural facts about this design deserve to be stated up front, because the
paper reports their consequences as empirical findings:

``recent`` cannot archive anything
    The newest record in each slot is by construction the one that supersedes the
    other, and it is written at day 199 -- the latest day in the store.  In the
    shipped 40-chain configuration the 40 updated records alone nearly exhaust the
    41-record review budget, so at most one of the reviewed records can be anything
    else.  Recency's coverage is therefore capped at roughly 1/40 and is zero in
    every shipped batch: the finding is structural, not measured.

``importance`` is noise
    ``build_store`` assigns importance uniformly at random, independently of which
    record is current.  "Importance-first" is therefore a random prior with a
    tie-break, and its coverage is a coin-flip artefact rather than a property of
    importance as a signal.

``decay`` is a function of ``importance``
    The half-life is chosen by importance band (30/12/6 days), so the two policies
    are not independent manipulations and cannot be contrasted as if they were.

The correct summary statistic for a selection function is the **conflict-hit rate**
``archived / reviewed`` -- the probability that a reviewed record is one of the
superseded ones -- and the natural reference point is uniform random selection,
which for this store has a hit rate of ``n_chains / (2 * n_chains + 24)``.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .prompts import NOW_DAY, RenderCfg
from .store import Entry, Store

POLICIES: tuple[str, ...] = ("none", "recent", "importance", "decay")

#: Policies that can be executed but are not part of the shipped four.  ``random`` is
#: the baseline the original design lacks: with 40 superseded records among 104 it hits
#: a conflict 38.5% of the time, which is the number every ranking signal has to beat.
SELECTABLE_POLICIES: tuple[str, ...] = POLICIES + ("random",)

POLICY_INFO: dict[str, dict[str, str]] = {
    "none": {
        "name_en": "No review",
        "name_zh": "不复习",
        "selects": "nothing",
    },
    "recent": {
        "name_en": "Recency first",
        "name_zh": "最近优先",
        "selects": "the newest records by write time",
    },
    "importance": {
        "name_en": "Importance first",
        "name_zh": "重要度优先",
        "selects": "the highest-importance records (importance is random in this design)",
    },
    "decay": {
        "name_en": "Decay first",
        "name_zh": "衰减复习",
        "selects": "the lowest retention w = exp(-dt/H), H in {30,12,6} by importance band",
    },
    "random": {
        "name_en": "Random",
        "name_zh": "随机复习",
        "selects": "a uniformly random subset of the live records",
    },
}


def half_life(importance: float) -> float:
    """Forgetting-curve half-life for an importance band, in days."""
    if importance >= 0.85:
        return 30.0
    if importance >= 0.60:
        return 12.0
    return 6.0


def retention(entry: Entry, now: float = NOW_DAY) -> float:
    """Remaining memory strength ``w = exp(-dt / H)``; lower means closer to forgotten."""
    return math.exp(-max(0.0, now - entry.day) / half_life(entry.importance))


def select_review(store: Store, budget_chars: int, policy: str, cfg: RenderCfg,
                  now: float = NOW_DAY, rng: random.Random | None = None) -> list[Entry]:
    """Spend ``budget_chars`` of review budget under ``policy``.

    Greedy fill: candidates are ordered by the policy's score, then taken in order
    while they fit.  Records that do not fit are skipped rather than terminating the
    scan, so the budget is filled to within one record's length.

    ``random`` exists for the roadmap's baseline: it samples uniformly, which is the
    only way to tell whether a ranking signal is doing anything at all.
    """
    if policy not in SELECTABLE_POLICIES:
        raise ValueError(f"unknown policy {policy!r}")
    if policy == "none":
        return []

    candidates = [e for e in store.entries if not e.archived]
    if policy == "recent":
        candidates.sort(key=lambda e: -e.day)
    elif policy == "importance":
        candidates.sort(key=lambda e: -e.importance)
    elif policy == "decay":
        candidates.sort(key=lambda e: retention(e, now))
    else:  # random
        if rng is None:
            raise ValueError("random selection needs an rng for reproducibility")
        rng.shuffle(candidates)

    picked: list[Entry] = []
    used = 0
    for entry in candidates:
        cost = len(entry.text(cfg))
        if used + cost > budget_chars:
            continue
        picked.append(entry)
        used += cost
        if used >= budget_chars:
            break
    return picked


def apply_review(selected: list[Entry], now: float = NOW_DAY) -> int:
    """Reconcile the reviewed records; return how many conflicts were archived."""
    archived = 0
    for entry in selected:
        if entry.superseded_by:
            entry.archived = True
            archived += 1
        else:
            entry.day = now
            entry.last_reviewed = now
    return archived


def review_budget(store: Store, cfg: RenderCfg, ratio: float = 0.4,
                  absolute: int = 0) -> int:
    """Budget in characters: a fraction of the store, or an absolute override."""
    if absolute:
        return absolute
    return max(1, int(store.total_chars(cfg) * ratio))


@dataclass(frozen=True)
class PolicyOutcome:
    """What a policy did to the store, in the units the paper reports."""

    policy: str
    reviewed: int
    archived: int
    review_chars: int
    n_chains: int

    @property
    def coverage(self) -> float:
        """Fraction of chains whose conflicting record was removed."""
        return self.archived / self.n_chains if self.n_chains else 0.0

    @property
    def conflict_hit_rate(self) -> float:
        """Share of reviewed records that turned out to be superseded."""
        return self.archived / self.reviewed if self.reviewed else 0.0


def random_selection_hit_rate(n_chains: int, n_decoys: int = 24) -> float:
    """Conflict-hit rate of uniform random selection on the synthetic store.

    Superseded records are ``n_chains`` of the ``2 * n_chains + n_decoys`` records,
    so a random review hits a conflict with this probability.  Comparing a policy's
    observed hit rate against this number is what turns "maintenance helps only by
    removing conflicts" from a tautology into a measurement.
    """
    return n_chains / (2 * n_chains + n_decoys)
