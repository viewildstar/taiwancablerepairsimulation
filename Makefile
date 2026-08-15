REPS ?= 30

.PHONY: run test clean

run:
	python3 scripts/run_experiments.py $(REPS)

test:
	python3 -m unittest discover -s tests

clean:
	rm -rf results figures
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	find . -name '*.pyc' -delete
