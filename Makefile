PY ?= .venv/bin/python
PORT ?= 8000

.PHONY: setup test demo report bench serve shots data

setup:            ## create .venv and install dependencies
	python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt

test:             ## run the test suite
	$(PY) -m pytest -q

demo:             ## the scripted story end to end (writes out/)
	$(PY) -m wattgap.demo

report:           ## economics on the real ERCOT days
	$(PY) -m wattgap.report

bench:            ## supervisor + worker throughput at 10k and 50k units
	$(PY) -m wattgap.bench 10000 50000

serve:            ## web UI on http://localhost:$(PORT)
	$(PY) -m uvicorn wattgap.server:app --port $(PORT)

shots:            ## screenshots of a running UI (needs playwright): make serve & make shots
	$(PY) scripts/screenshots.py http://localhost:$(PORT) docs/shots

data:             ## re-download the ERCOT prices (needs pandas, openpyxl, requests)
	$(PY) scripts/fetch_ercot.py
