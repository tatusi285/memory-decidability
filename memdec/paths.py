"""Repository layout discovery.

The analysis code is meant to run straight from a checkout, without an install
step, so paths are derived from this file rather than from the working directory.
Set ``MEMDEC_ROOT`` to point at a different checkout.
"""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Return the repository root (the directory that holds ``data/``)."""
    env = os.environ.get("MEMDEC_ROOT")
    if env:
        root = Path(env).expanduser().resolve()
        if not (root / "data").is_dir():
            raise RuntimeError(f"MEMDEC_ROOT={root} does not contain a data/ directory")
        return root
    for parent in Path(__file__).resolve().parents:
        if (parent / "data" / "runs.csv").is_file():
            return parent
    raise RuntimeError(
        "could not locate the repository root; set MEMDEC_ROOT to the checkout directory"
    )


def data_dir() -> Path:
    return repo_root() / "data"


def runs_dir() -> Path:
    return data_dir() / "runs"


def docs_dir() -> Path:
    """Where generated tables, figures and reports are committed.

    They live under ``docs/`` rather than a scratch directory so that a reader on
    GitHub can see every table and figure without running anything, and so that CI
    can fail when regenerating them changes a byte.
    """
    path = Path(os.environ.get("MEMDEC_DOCS", repo_root() / "docs"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def out_dir() -> Path:
    """Scratch directory for local runs (git-ignored)."""
    path = Path(os.environ.get("MEMDEC_OUT", repo_root() / "analysis_out"))
    path.mkdir(parents=True, exist_ok=True)
    return path
