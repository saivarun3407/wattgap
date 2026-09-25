PY ?= .venv/bin/python
PORT ?= 8000

-include .env
export

.PHONY: setup test cov demo demo-net report params bench serve shots data

setup:            ## create .venv and install dependencies
	python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt

test:             ## run the test suite
	$(PY) -m pytest -q

cov:              ## test suite with line coverage
	$(PY) -m pytest -q --cov=wattgap --cov-report=term

demo:             ## the scripted story end to end (writes out/)
	$(PY) -m wattgap.demo

demo-net:         ## 400 batteries as 40 OS processes over localhost TCP, with a real kill -9
	$(PY) -m wattgap.netdemo

report:           ## economics on the real ERCOT days
	$(PY) -m wattgap.report

params:           ## re-run the planner parameter search on the Jul-Aug selection days (writes docs/PARAMS.md)
	$(PY) scripts/select_params.py

bench:            ## tick latency and throughput, 1k to 10M units (takes a few minutes)
	$(PY) -m wattgap.bench

serve:            ## web UI on http://localhost:$(PORT)
	$(PY) -m uvicorn wattgap.server:app --port $(PORT)

shots:            ## screenshots of a running UI (needs playwright): make serve & make shots
	$(PY) scripts/screenshots.py http://localhost:$(PORT) docs/shots

data:             ## re-download the ERCOT prices and load profiles (needs pandas, openpyxl, requests)
	$(PY) scripts/fetch_ercot.py
