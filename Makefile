SEED ?= 2026
PORT ?= 8000

install:
	pip install -r requirements.txt

world:            ## generate the Afterglow Labs world (+ answer key)
	python -m jarvis.world.generator --seed $(SEED)

up:               ## run the API + Synapse Trace UI on http://localhost:$(PORT)
	python -m jarvis.api.server --seed $(SEED) --port $(PORT)

fresh:            ## same, starting from a fresh work.db
	python -m jarvis.api.server --seed $(SEED) --port $(PORT) --fresh

demo-cli:         ## full autonomous run in the terminal (no UI)
	python -m jarvis.cli --seed $(SEED)

eval:             ## score Jarvis vs the answer key and the rules baseline on 4 seeds
	python -m jarvis.evals.run --seeds 2026 1 2 3 11 42

test:
	python -m pytest -q tests

keys:             ## mint per-role Elastic API keys from the master key in .env
	python -m jarvis.search.mint_keys
