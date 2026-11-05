## What this changes

A one-line summary.

## Type

- [ ] Measurement code (`memdec/`)
- [ ] Analysis, table or figure (`memdec/analysis/`)
- [ ] Documentation
- [ ] Tests
- [ ] Data — *not accepted; see CONTRIBUTING.md*

## Checklist

- [ ] `python -m unittest discover -s tests -t .` passes
- [ ] `python -m memdec build` was run and the `docs/` diff is committed
- [ ] No new runtime dependency (the package is standard-library only)
- [ ] If a prompt rendering changed, `PROMPT_VERSION` was bumped and `CHANGELOG.md` updated
- [ ] If a finding was resolved, `docs/AUDIT.md` and the corresponding test were updated together
- [ ] No file under `data/` was modified

## Does this change a published number?

- [ ] No
- [ ] Yes — and `docs/CLAIMS.md` was regenerated, with the old and new values stated here:

| Claim | Was | Now | Why |
|---|---|---|---|
| | | | |
