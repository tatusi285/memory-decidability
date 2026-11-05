---
name: Data discrepancy
about: A reported number does not reproduce from the shipped data
title: "[data] "
labels: ["data"]
---

## Which number

- Claim ID (from `docs/CLAIMS.md`, e.g. `T1.9`) or table cell:
- Run directory (e.g. `out_live_bare`):
- Value in the paper:
- Value you compute:

## How you computed it

```bash
# the command, or the few lines of Python
```

## Scope

- [ ] This is a discrepancy in the *manuscript* (the paper says X, the data says Y)
- [ ] This is a discrepancy in the *artifact* (`verify` fails, or a table differs)
- [ ] This is a disagreement about *interpretation* (the number is right, the claim is not)

The third category is welcome and does not need a bug report format — open it as a
discussion or an issue and state the argument. `docs/REVIEW.md` contains eight such
disputes already; see `docs/CLAIMS.md` §3.

## Please do not edit `data/`

Shipped result files are the evidence. If one is wrong, the correction goes in the
documentation plus a new run, never in the evidence itself.
