"""Answer classification.

The task asks for one value and the prompt says "只输出值本身" (emit the value only),
so classification is a substring test.  Two properties of that rule matter:

* it is *lenient*: if an answer contains both values ("原来是 8000，现在是 9000")
  it is scored ``correct``, because the updated value is tested first;
* it is *stripping* non-alphanumerics, so punctuation and spacing never matter.

:func:`classify` returns the published verdict plus an ``ambiguous`` flag, so the
analysis can report how often the leniency could have mattered instead of leaving
the reader to wonder.
"""

from __future__ import annotations

from dataclasses import dataclass

from .store import Chain

CORRECT = "correct"
STALE = "stale"
UNKNOWN = "unknown"


@dataclass(frozen=True)
class Verdict:
    label: str
    matched: str | None = None
    ambiguous: bool = False

    def __str__(self) -> str:  # convenience for CLI output
        return self.label


def classify(answer: str, chain: Chain) -> Verdict:
    """Classify one answer against the chain's two values."""
    text = answer or ""
    normalised = "".join(ch for ch in text if ch.isalnum())
    lowered = text.lower()
    if not normalised or "error" in lowered or "unknown" in lowered:
        return Verdict(UNKNOWN)

    has_new = chain.new_value in normalised
    has_old = chain.old_value in normalised
    if has_new and has_old:
        return Verdict(CORRECT, matched="new", ambiguous=True)
    if has_new:
        return Verdict(CORRECT, matched="new")
    if has_old:
        return Verdict(STALE, matched="old")
    return Verdict(UNKNOWN)


def score_answer(answer: str, chain: Chain) -> str:
    """Published verdict: ``correct`` / ``stale`` / ``unknown``."""
    return classify(answer, chain).label


def is_ambiguous(answer: str, chain: Chain) -> bool:
    """True when the answer names both the updated and the outdated value."""
    return classify(answer, chain).ambiguous
