"""memdec — a reproducibility toolkit for the *Decidability Before Maintenance* study.

Two things live here, and it is important not to confuse them:

1. ``memdec.runner`` re-implements the measurement pipeline: it builds synthetic or
   real-log memory chains, applies one of four review policies, renders the records
   into a prompt, and asks a model for the current value.  With ``--offline`` it
   exercises the whole pipeline without touching the network.
2. ``memdec.analysis`` recomputes every number the paper reports from the shipped
   result files, and adds the diagnostics that the original analysis omitted
   (exact binomial intervals, effective sample size, the archive-coverage identity,
   the conflict-hit rate against a random-selection baseline).

The distinction between *consistency* and *replication* matters for how you read the
outputs: ``python -m memdec verify`` shows that the numbers in the paper follow from
the CSVs in ``data/``.  It cannot show that the CSVs follow from fresh model calls --
that requires an API key and the commands in ``docs/REPRODUCING.md``.
"""

__version__ = "1.0.0"
__all__ = ["__version__"]
