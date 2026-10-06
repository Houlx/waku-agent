# Career Agent command shortcuts.
#
# Make is not a framework — it's a 45-year-old command shortcut tool that
# ships with every Mac/Linux. Each target below is just the shell command
# you'd otherwise type. `make run` = "run the python below", nothing more.
#
# PY picks the project venv automatically so you never need to remember
# `source .venv/bin/activate` — both work, this is just fewer steps.
PY := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python)

# Maintainers work on the repo's own .waku, never on the ~/.waku a person's
# real assistant uses (spec 002). An explicit WAKU_HOME still wins.
export WAKU_HOME ?= $(CURDIR)/.waku

.PHONY: run dashboard trace eval eval-judge gate lint

run:            ## launch Career Agent at http://localhost:7777/#overview
	$(PY) -m waku

# Restart the Career server after changing Python routes or imported modules.
dashboard:      ## launch Career Agent (restart after a backend pull)
	$(PY) -m waku career

trace:          ## deep trace waterfalls (Phoenix) at http://localhost:6006
	$(PY) -m phoenix.server.main serve

eval:           ## deterministic evals (0/1, no judge involved)
	$(PY) -m pytest -q evals/deterministic

eval-judge:     ## LLM-as-judge evals (scored %, needs an API key)
	$(PY) -m pytest -q evals/judge

gate:           ## the release gate: deterministic must pass, judge must clear threshold
	$(PY) -m waku.ops.release_gate

lint:
	$(PY) -m ruff check waku evals scripts
