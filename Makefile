# Convenience targets. Everything here is a thin wrapper over `python -m memdec`.
# On Windows without make, use `.\tasks.ps1 <target>` instead.

PY ?= python

.PHONY: help test verify audit tables figures build clean lint install

help:
	@echo "make test     - run the unit test suite"
	@echo "make verify   - recompute the paper's 62 published values from data/"
	@echo "make audit    - run the design audit, write analysis_out/AUDIT.md"
	@echo "make tables   - regenerate every table as Markdown"
	@echo "make figures  - regenerate every figure as SVG"
	@echo "make build    - verify + audit + tables + figures"
	@echo "make lint     - ruff check"
	@echo "make clean    - remove analysis_out/"

test:
	$(PY) -m unittest discover -s tests -t . -v

verify:
	$(PY) -m memdec verify

audit:
	$(PY) -m memdec audit

tables:
	$(PY) -m memdec tables

figures:
	$(PY) -m memdec figures

build:
	$(PY) -m memdec build

lint:
	$(PY) -m ruff check memdec tests

install:
	$(PY) -m pip install -e ".[dev]"

clean:
	rm -rf analysis_out
