"""The measurement loop.

One *condition* is a full factorial cell: a store builder, a delay, a seed and a
policy.  For each chain the runner assembles the retrieved context, renders it into
a prompt, asks the model, and classifies the answer.

Two properties of the resulting data are worth knowing before you read any table:

1. **Retrieval is per-slot.** ``build_context`` filters on ``entity`` (or on
   ``scope`` for the real corpus), so the context for a query contains *only* that
   slot's records -- one or two of them.  The 24 distractor records never appear in
   any queried context; they exist to consume review budget.  The paper's framing of
   "retrieval under a budget" therefore applies to review, not to querying.
2. **The outcome is a function of the context, not of difficulty.** For a context
   with one record there is one possible value; with two records the model applies a
   positional rule.  ``memdec.analysis.audit`` shows that this predicts 1,920 of
   1,920 probes in the core grid.
"""

from __future__ import annotations

import csv
import datetime
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__, prompts
from .client import ChatClient, RuleSimulator
from .manifest import RESULT_COLUMNS, SUMMARY_ENTITY
from .policies import POLICIES, PolicyOutcome, apply_review, review_budget, select_review
from .prompts import NOW_DAY, RenderCfg
from .scoring import classify
from .store import Chain, Store, build_store, build_store_real, load_real_chains


@dataclass
class RunConfig:
    """Everything that defines a run; serialised into ``run_meta.json``."""

    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com/v1"
    chains: int = 40
    delays: tuple[float, ...] = (1, 7, 30, 90)
    seeds: int = 3
    policies: tuple[str, ...] = POLICIES
    review_ratio: float = 0.4
    review_budget_chars: int = 0
    ctx_budget: int = 1200
    time_format: str = "date"
    text_style: str = "template"
    ctx_order: str = "newest_first"
    filler_k: int = 0
    filler_mode: str = "tail"
    corpus: str = "synthetic"
    corpus_file: Path | None = None
    importance_mode: str = "random"
    importance_signal: float = 0.0
    late_duplicates: float = 0.0
    max_tokens: int = 24
    concurrency: int = 6
    offline: bool = False
    out: Path = Path("out")

    def render_cfg(self) -> RenderCfg:
        return RenderCfg(self.time_format, self.text_style)  # type: ignore[arg-type]


@dataclass
class RunResult:
    rows: list[dict] = field(default_factory=list)
    outcomes: list[PolicyOutcome] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


def build_context(store: Store, chain: Chain, budget: int, order: str, cfg: RenderCfg,
                  rng: random.Random | None = None) -> list:
    """Retrieve the live records for one slot, ordered, within a character budget."""
    if chain.scope:
        candidates = [e for e in store.entries if e.scope == chain.scope and not e.archived]
    else:
        candidates = [e for e in store.entries if e.entity == chain.entity and not e.archived]

    if order == "random":
        if rng is not None:
            rng.shuffle(candidates)
    elif order == "newest_first":
        candidates.sort(key=lambda e: -e.day)
    else:
        candidates.sort(key=lambda e: e.day)

    picked, used = [], 0
    for entry in candidates:
        cost = len(entry.text(cfg)) + 1
        if used + cost > budget:
            continue
        picked.append(entry)
        used += cost
    return picked


def _make_store(cfg: RunConfig, seed: int, delay: float) -> Store:
    if cfg.corpus == "real":
        if cfg.corpus_file is None:
            raise ValueError("corpus='real' needs corpus_file")
        return build_store_real(seed, load_real_chains(cfg.corpus_file), delay)
    return build_store(seed, cfg.chains, delay,
                       importance_mode=cfg.importance_mode,
                       importance_signal=cfg.importance_signal,
                       late_duplicates=cfg.late_duplicates)


def run(cfg: RunConfig, api_key: str = "", key_env: str = "") -> RunResult:
    """Execute a condition grid and return rows plus the policy accounting."""
    render_cfg = cfg.render_cfg()
    responder = RuleSimulator() if cfg.offline else ChatClient(
        model=cfg.model, base_url=cfg.base_url, api_key=api_key,
        max_tokens=cfg.max_tokens,
    )
    rows: list[dict] = []
    outcomes: list[PolicyOutcome] = []
    started = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    clock = time.perf_counter()

    for delay in cfg.delays:
        for seed in range(cfg.seeds):
            for policy in cfg.policies:
                store = _make_store(cfg, seed, delay)
                rng = random.Random(f"{seed}-{delay}-{policy}")
                budget = review_budget(store, render_cfg, cfg.review_ratio,
                                       cfg.review_budget_chars)
                selected = select_review(store, budget, policy, render_cfg, NOW_DAY, rng)
                archived = apply_review(selected, NOW_DAY)
                review_chars = sum(len(e.text(render_cfg)) for e in selected)

                contexts = [
                    build_context(store, chain, cfg.ctx_budget, cfg.ctx_order, render_cfg,
                                  rng, )
                    for chain in store.chains
                ]
                prompt_texts = [
                    prompts.build_prompt([e.text(render_cfg) for e in ctx], chain.entity,
                                         chain.attr, cfg.time_format, cfg.filler_k,
                                         cfg.filler_mode)
                    for ctx, chain in zip(contexts, store.chains, strict=False)
                ]

                if cfg.concurrency > 1 and len(prompt_texts) > 1:
                    with ThreadPoolExecutor(max_workers=cfg.concurrency) as pool:
                        responses = list(pool.map(lambda p: responder.ask(p), prompt_texts))
                else:
                    responses = [responder.ask(p) for p in prompt_texts]

                counts = {"correct": 0, "stale": 0, "unknown": 0}
                ctx_chars = 0
                for ctx, chain, (answer, _meta) in zip(contexts, store.chains, responses, strict=False):
                    verdict = classify(answer, chain)
                    counts[verdict.label] += 1
                    ctx_chars += sum(len(e.text(render_cfg)) for e in ctx)
                    rows.append({
                        "delay": int(delay), "seed": seed, "policy": policy,
                        "entity": chain.entity, "verdict": verdict.label,
                        "answer": answer, "ctx_entries": len(ctx),
                    })

                n = len(store.chains)
                rows.append({
                    "delay": int(delay), "seed": seed, "policy": policy,
                    "entity": SUMMARY_ENTITY, "verdict": "", "answer": "",
                    "ctx_entries": 0,
                    "correct": counts["correct"] / n,
                    "stale": counts["stale"] / n,
                    "unknown": counts["unknown"] / n,
                    "reviewed": len(selected), "archived": archived,
                    "review_chars": review_chars,
                    "ctx_chars_avg": round(ctx_chars / n, 1),
                })
                outcomes.append(PolicyOutcome(policy, len(selected), archived,
                                              review_chars, n))

    meta = {
        "memdec_version": __version__,
        "prompt_version": prompts.PROMPT_VERSION,
        "simulated": cfg.offline,
        "responder": getattr(responder, "name", cfg.model),
        "started_at": started,
        "wall_seconds": round(time.perf_counter() - clock, 2),
        "api_key_env": key_env,
        "config": {
            "model": cfg.model, "base_url": cfg.base_url, "chains": cfg.chains,
            "delays": list(cfg.delays), "seeds": cfg.seeds,
            "policies": list(cfg.policies), "review_ratio": cfg.review_ratio,
            "review_budget_chars": cfg.review_budget_chars, "ctx_budget": cfg.ctx_budget,
            "time_format": cfg.time_format, "text_style": cfg.text_style,
            "ctx_order": cfg.ctx_order, "filler_k": cfg.filler_k,
            "filler_mode": cfg.filler_mode, "corpus": cfg.corpus,
            "importance_mode": cfg.importance_mode,
            "importance_signal": cfg.importance_signal,
            "late_duplicates": cfg.late_duplicates,
            "max_tokens": cfg.max_tokens, "concurrency": cfg.concurrency,
        },
    }
    return RunResult(rows=rows, outcomes=outcomes, meta=meta)


def write_results(rows: list[dict], out: Path) -> Path:
    """Write ``results.csv`` in the schema the shipped files use."""
    out.mkdir(parents=True, exist_ok=True)
    path = out / "results.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(RESULT_COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in RESULT_COLUMNS})
    return path


def write_meta(meta: dict, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    path = out / "run_meta.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
