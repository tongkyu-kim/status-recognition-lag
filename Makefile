# Thin wrapper around tasks.py (single source of truth for commands).
# On systems without make: python tasks.py <target>

PYTHON ?= python
TASK = $(PYTHON) tasks.py

.PHONY: help setup test lint sources register-raw verify-raw trade status text attention \
        recognition panel models figures pipeline clean-derived

help:
	@echo "Targets:"
	@echo "  setup          install package (+dev tools) and pre-commit hooks"
	@echo "  test           run unit tests"
	@echo "  lint           ruff lint"
	@echo "  sources        list configured data sources and raw-file counts"
	@echo "  register-raw   checksum newly deposited raw files into data/raw_manifest.csv"
	@echo "  verify-raw     verify raw files are unchanged since registration"
	@echo "  trade          02 clean trade data"
	@echo "  status         03 status, interdependence and overlap measures"
	@echo "  text           04-05 assemble corpus, segment, match entities"
	@echo "  attention      06 attention measures"
	@echo "  recognition    07 recognition measures"
	@echo "  panel          08 partner-year panel (+ recognition-lag variants)"
	@echo "  models         09 estimate specs marked ready"
	@echo "  figures        10 production figures"
	@echo "  pipeline       verify-raw -> figures in order"
	@echo "  clean-derived  delete derived data/outputs (never raw); requires CONFIRM=1"

setup test lint sources register-raw verify-raw trade status text attention recognition panel models figures pipeline:
	$(TASK) $@

clean-derived:
	$(TASK) clean-derived $(if $(CONFIRM),--yes,)
