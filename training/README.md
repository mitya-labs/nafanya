# Training workspace

This directory holds the model side of **nafanya**, the model used by the **kuzya**
agent: data generation, LoRA training, export and evaluation.

## Layout

| Path | Purpose |
|---|---|
| `data/` | Seeds, generated train/dev/test JSONL, reports and provenance |
| `scripts/` | Python/Go scripts for generation, validation, training and export |
| `runs/` | Per-run configs, logs and checkpoints (large files gitignored) |

## Environment

- Python 3.12 via `uv`; do not use the system Python 3.14.
- `mlx-lm`, `huggingface_hub`, `transformers`, `datasets`, `sentencepiece`, `torch`.
- A clone of `llama.cpp` at commit `6050b46` for `convert_hf_to_gguf.py` and
  `llama-quantize`; the phone binaries are built from the same commit.
- The final evaluation runs on the phone through `../kuzya` scripts; Mac results are only
  for iteration.

## Compatibility (2026-10-27)

| Model | HF / licence | MLX-LM | LoRA | GGUF | Notes |
|---|---|---|---|---|---|
| Qwen3.5-0.8B | `Qwen/Qwen3.5-0.8B`, Apache-2.0 | text model loads with `mlx-lm 0.32.2` | BF16 LoRA, 2 layers, rank 16, compact prompt at 1024 OK | `convert_hf_to_gguf.py` at `6050b46` supports `qwen35` | 4+ layers OOM/watchdog; MLX 4-bit quantization collapses quality — never use it for training or eval; inference stays on GGUF Q4_K_M |
| Qwen3-1.7B | not downloaded yet | fallback | not tested | not tested | safe fallback if `qwen3_5` training is unstable |
| Gemma 4 E2B | reference only | not needed | not needed | not needed | memory/battery reference, not a training target |

Working export path for `qwen3_5`:

1. Train a QLoRA adapter with `mlx_lm lora` and `MLX_DISABLE_COMPILE=1`.
2. `scripts/mlx_adapter_to_peft.py` converts the MLX adapter to PEFT layout
   (transposes A/B, sets `alpha = scale * rank`).
3. `convert_lora_to_gguf.py --base ...` produces a GGUF LoRA.
4. `llama-export-lora` merges it into the original base `Q4_K_M` GGUF.
5. Quantize or serve with `llama-server --jinja`.

Do not use `mlx_lm.fuse --export-gguf` for `qwen3_5` (unsupported), and do not convert
fused MLX weights into HF layout: the GatedDeltaNet tensor layout is MLX-specific and the
result is garbage.

## Training recipe (2026-10-27)

- Model: `Qwen/Qwen3.5-0.8B` BF16 (do not use the MLX 4-bit copy; its quality collapses).
- LoRA: 2 last layers, rank 16, scale 16, dropout 0.05, keys
  `self_attn.q_proj`, `self_attn.v_proj`, `mlp.gate_proj`, `mlp.up_proj`,
  `mlp.down_proj`.
- Data: compact prompt with 889 tokens per example
  (`tools-schema-min.json` + `system-prompt-min.txt`), max sequence 1024.
- Batch 4–8, lr 5e-5, `mask_prompt`, `grad_checkpoint`,
  `clear_cache_threshold: 1`, `MLX_DISABLE_COMPILE=1`.
- Disable intermediate validation (`steps_per_eval` > iters); evaluate the saved adapter
  separately. A validation pass can trigger the macOS GPU watchdog.

## Data rules

- Teacher: DeepSeek V4.1 Flash via the Open Platform API, under the terms recorded in
  `data/SOURCES.md`. Local Qwen3 under Apache-2.0 is the fallback.
- Every example carries `id`, `q`, `tool`, `args`, `category`, `split`, `source` and
  `terms`. A negative has `"tool": null`.
- No example may overlap with `../kuzya/tests/cases*.json`; run the leakage check before
  every training run.
- Keep generated datasets in `data/generated/` (gitignored); commit only seeds, scripts,
  reports and hashes unless the licence clearly allows redistribution.

## Status

Scaffold only. The first step is the teacher seed pilot (T2.1), followed by the schema
validator and the leakage check. See `../PLAN.md`.
