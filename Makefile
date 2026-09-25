PY ?= .venv/bin/python
PORT ?= 8000

-include .env
export

.PHONY: setup test cov demo demo-net report params bench serve shots data archive locations scarcity radar-live feeds vintages warn warn-live events

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

archive:          ## download ERCOT's yearly RT/DAM/AS price archives 2018-2025 to data/archive (git-ignored, ~120 MB raw)
	$(PY) scripts/fetch_archive.py

locations:        ## perfect-foresight bound + fair schedule per zone/hub and year (needs make archive; ~2 min)
	$(PY) scripts/locations.py

scarcity:         ## fit the Scarcity Radar on 2019-2023, backtest 2024-2025 (needs make archive; ~2 min)
	$(PY) scripts/scarcity.py

radar-live:       ## score tomorrow from the DAM ERCOT posted today (network)
	$(PY) -m wattgap.scarcity

vintages:         ## the load/wind/solar forecasts ERCOT had posted by 10:00 CT the day before, for the days MIS still keeps
	$(PY) scripts/fetch_vintages.py

feeds:            ## download every RTD / adder / lambda / settled-price file MIS still keeps (~5-7 days, network)
	$(PY) scripts/fetch_feeds.py

warn:             ## backtest the Signals early warning on the downloaded feeds (needs make feeds)
	$(PY) -m wattgap.warn

events:           ## UT home-game Saturdays vs other fall Saturdays, Austin prices 2023-2025 (needs make archive)
	$(PY) -m wattgap.events

warn-live:        ## poll ERCOT every 5 minutes and print HOLD / PRE-CHARGE / DISCHARGE-NOW per zone
	$(PY) -m wattgap.warn --live
