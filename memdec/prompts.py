"""Record rendering and prompt construction.

This module is the single source of truth for *what the model was shown*.  The
original study scattered the same strings across a 750-line script, so a reader
could not tell which condition differed from which.  Here every condition is an
explicit argument and the assembled prompt is returned as a plain string that can
be hashed, logged and diffed.

Bumping ``PROMPT_VERSION`` is a data-format change: results produced under a
different version are not comparable, and ``results.csv`` records the version it
was produced with.
"""

from __future__ import annotations

import datetime
import hashlib
from dataclasses import dataclass
from typing import Literal

PROMPT_VERSION = "1.0.0"

#: The synthetic store is anchored at day 0 = 2026-01-01 and queried at day 200.
BASE_DATE = datetime.date(2026, 1, 1)
NOW_DAY = 200.0

#: Neutral filler with no digits, so it can never be mistaken for a candidate value.
FILLER = "巡检备注：机房温度正常，未发现异常情况。"

#: Three sentence forms used by the ``natural`` (mixed) condition.
NATURAL_TEMPLATES: tuple[str, ...] = (
    "运维笔记：{entity} 的{attr}记的是 {value}，当时没提到别的改动。",
    "群里聊过，{entity} 那台的{attr}用的是 {value}。",
    "值班记录：查了一下 {entity}，{attr}是 {value}，其余正常。",
)

TimeFormat = Literal["date", "day", "none"]
TextStyle = Literal[
    "template", "uniform", "natural", "vary_source", "vary_structure", "vary_number"
]
CtxOrder = Literal["newest_first", "oldest_first", "random"]
FillerMode = Literal["tail", "gap", "prefix"]

TIME_FORMATS: tuple[TimeFormat, ...] = ("date", "day", "none")
TEXT_STYLES: tuple[TextStyle, ...] = (
    "template", "uniform", "natural", "vary_source", "vary_structure", "vary_number",
)
CTX_ORDERS: tuple[CtxOrder, ...] = ("newest_first", "oldest_first", "random")
FILLER_MODES: tuple[FillerMode, ...] = ("tail", "gap", "prefix")


def day_to_date(day: float) -> datetime.date:
    """Map a day index onto the study's fixed calendar."""
    return BASE_DATE + datetime.timedelta(days=float(day))


def now_label(time_format: TimeFormat) -> str:
    """The ``现在是 ...`` prefix, or the empty string when there is no timestamp."""
    if time_format == "date":
        return f"{day_to_date(NOW_DAY):%Y-%m-%d}"
    return f"第{NOW_DAY:.0f}天"


def timestamp_prefix(day: float, time_format: TimeFormat) -> str:
    if time_format == "date":
        return f"[{day_to_date(day):%Y-%m-%d}] "
    return f"[第{day:.0f}天] "


def record_body(entity: str, attr: str, value: str, entry_id: str, style: TextStyle,
                raw_text: str | None = None) -> str:
    """Render the body of one memory record under ``style``.

    ``entry_id`` only feeds a deterministic rotation so that different records in a
    mixed-wording condition do not all receive the same sentence form.  It must not
    carry information about which record is newer: ``o3``/``n3`` differ in prefix,
    which is exactly why the rotation is keyed on ``sum(ord(c))`` rather than on
    order of appearance.
    """
    if raw_text:
        return raw_text
    idx = sum(ord(c) for c in entry_id)
    if style == "uniform":
        return f"记录：{entity} 的{attr}是 {value}，这条是当时的笔记。"
    if style == "natural":
        return NATURAL_TEMPLATES[idx % len(NATURAL_TEMPLATES)].format(
            entity=entity, attr=attr, value=value
        )
    if style == "vary_source":
        src = ("运维笔记", "群里聊过", "值班记录")[idx % 3]
        return f"{src}：{entity} 的{attr}是 {value}，这条是当时的笔记。"
    if style == "vary_structure":
        tpl = (
            "记录：{entity} 的{attr}是 {value}，这条是当时的笔记。",
            "记录：当时的笔记里写着，{entity} 的{attr}为 {value}。",
            "记录：{attr}这一项，{entity} 填的是 {value}（依据当时的笔记）。",
        )[idx % 3]
        return tpl.format(entity=entity, attr=attr, value=value)
    if style == "vary_number":
        tpl = (
            "记录：{entity} 的{attr}是 {value}，这条是当时的笔记。",
            "记录：这条是当时的笔记，{entity} 的{attr}是 {value}。",
            "记录：{value} 这个值对应 {entity} 的{attr}，这条是当时的笔记。",
        )[idx % 3]
        return tpl.format(entity=entity, attr=attr, value=value)
    return f"{entity}·{attr} = {value}"


def record_text(entity: str, attr: str, value: str, day: float, entry_id: str,
                style: TextStyle, time_format: TimeFormat,
                raw_text: str | None = None) -> str:
    """Full rendered record, including the timestamp prefix when applicable."""
    body = record_body(entity, attr, value, entry_id, style, raw_text)
    if time_format == "none":
        return body
    return timestamp_prefix(day, time_format) + body


def with_filler(lines: list[str], k: int, mode: FillerMode) -> list[str]:
    """Insert ``k`` digit-free filler sentences relative to the records.

    ``tail`` puts them after both records, ``gap`` between them, and ``prefix``
    before both.  The prefix condition is the control that separates "the cue sits at
    the end of the context" from "more text before the question makes the task
    harder"; only the former predicts an inert prefix.
    """
    if k <= 0 or not lines:
        return list(lines)
    if mode == "gap" and len(lines) >= 2:
        return [lines[0]] + [FILLER] * k + lines[1:]
    if mode == "prefix":
        return [FILLER] * k + list(lines)
    return list(lines) + [FILLER] * k


def build_prompt(record_lines: list[str], entity: str, attr: str,
                 time_format: TimeFormat, filler_k: int = 0,
                 filler_mode: FillerMode = "tail") -> str:
    """Assemble the exact user message sent to the model."""
    lines = with_filler(record_lines, filler_k, filler_mode)
    digest = "\n".join(lines) if lines else "（无相关记录）"
    if time_format == "none":
        head = f"你的长期记忆里与「{entity}」相关的记录如下："
    else:
        head = f"现在是 {now_label(time_format)}。你的长期记忆里与「{entity}」相关的记录如下："
    return f"{head}\n{digest}\n\n问题：{entity} 的{attr}现在是多少？只输出值本身，不要解释。"


def prompt_fingerprint(prompt: str) -> str:
    """Short stable hash, so a run can be matched against a prompt template."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class RenderCfg:
    """Everything that determines what a record looks like."""

    time_format: TimeFormat = "date"
    text_style: TextStyle = "template"

    def __post_init__(self) -> None:
        if self.time_format not in TIME_FORMATS:
            raise ValueError(f"unknown time_format {self.time_format!r}")
        if self.text_style not in TEXT_STYLES:
            raise ValueError(f"unknown text_style {self.text_style!r}")
