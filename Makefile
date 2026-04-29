.PHONY: env env-update sync test test-all run notify smoke

CONDA ?= /root/miniconda3/bin/conda
ENV_NAME ?= paperclaw
CONDA_PYTHON ?= /root/miniconda3/envs/$(ENV_NAME)/bin/python

env:
	$(CONDA) env create -f environment.yml
	$(CONDA) run -n $(ENV_NAME) python -m pip install -U pip uv

env-update:
	$(CONDA) env update -f environment.yml --prune
	$(CONDA) run -n $(ENV_NAME) python -m pip install -U pip uv

sync:
	$(CONDA) run -n $(ENV_NAME) uv sync --python $(CONDA_PYTHON) --extra dev

test:
	$(CONDA) run -n $(ENV_NAME) uv run pytest -q

test-all:
	$(CONDA) run -n $(ENV_NAME) uv run pytest tests/ -q

run:
	$(CONDA) run -n $(ENV_NAME) uv run python run_once.py

notify:
	$(CONDA) run -n $(ENV_NAME) uv run python run_notify_once.py

smoke:
	$(CONDA) run -n $(ENV_NAME) uv run python scripts/send_test_feishu_message.py
