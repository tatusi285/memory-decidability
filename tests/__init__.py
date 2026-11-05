"""Tests for memdec (stdlib unittest, no third-party dependencies).

Run from the repository root::

    python -m unittest discover -s tests -v

The suite is designed to fail loudly if the shipped data and the code drift apart:
it re-runs the deterministic half of the pipeline and compares the result with the
files in ``data/``, and it pins the statistics against published critical values.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


if __name__ == "__main__":
    unittest.main(verbosity=2)
