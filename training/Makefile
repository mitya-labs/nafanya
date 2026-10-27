# Common commands for the Nafanya model workspace.

PY := training/.venv/bin/python
PYC := training/.venv-convert/bin/python
LLAMA := training/vendor/llama.cpp-6050b46
ADAPTER ?= training/runs/pilot-01
RUN ?= pilot-01

.PHONY: help env data validate smoke pilot eval export clean

help:
	@echo "make env       - create Python 3.12 venvs (already done)"
	@echo "make data      - build the pilot split from seeds"
	@echo "make validate  - validate seeds and check leakage"
	@echo "make smoke     - build the smoke dataset"
	@echo "make pilot     - train the pilot QLoRA adapter"
	@echo "make eval      - evaluate an adapter on the 26-query subset"
	@echo "make export    - export an adapter to merged Q4_K_M GGUF"

env:
	python3.12 -m venv training/.venv
	training/.venv/bin/python -m pip install -U pip mlx-lm
	python3.12 -m venv training/.venv-convert
	training/.venv-convert/bin/python -m pip install -U pip
	training/.venv-convert/bin/python -m pip install torch==2.11.0 --extra-index-url https://download.pytorch.org/whl/cpu
	training/.venv-convert/bin/python -m pip install 'transformers==4.57.6' 'numpy==2.2.6' 'gguf>=0.1.0' 'sentencepiece>=0.1.98,<0.3.0' 'protobuf>=4.21.0,<5.0.0'

data:
	$(PY) training/scripts/build_dataset.py --seeds training/data/seeds-teacher-v0.jsonl --out training/data/pilot

validate:
	$(PY) training/scripts/validate_data.py training/data/seeds-teacher-v0.jsonl

smoke:
	$(PY) training/scripts/make_smoke.py

pilot:
	MLX_DISABLE_COMPILE=1 $(PY) -m mlx_lm lora -c training/configs/pilot-qlora.yaml

eval:
	$(PY) training/scripts/eval_adapter.py --adapter $(ADAPTER) --cases ../kuzya/tests/cases-subset.json --out logs/eval-$(RUN).jsonl

export:
	./training/scripts/export_adapter.sh $(ADAPTER) $(RUN)

clean:
	rm -rf training/runs/*
	touch training/runs/.gitkeep
