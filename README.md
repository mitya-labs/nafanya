# nafanya

Model workspace for **nafanya**, the model used by the **kuzya** agent: teacher-generated
data, LoRA fine-tuning, GGUF export and on-device evaluation.

## Naming

- **nafanya** — the tuned model produced in this repository.
- **kuzya** — the offline agent in `../kuzya` that uses nafanya on the phone.
- **Qwen3.5 / Qwen3** — the base models nafanya is trained from.

The agent, its tools and its tests stay in `../kuzya`. This repository is intentionally
separate so that datasets, adapters and model weights do not pollute the agent repo.

## Layout

| Path | Purpose |
|---|---|
| `PLAN.md` | Detailed task breakdown, gates and decision rule (working copy of `../kuzya/docs/TRAINING.md`) |
| `training/data/` | Seeds, generated datasets, provenance and reports |
| `training/scripts/` | Data generation, validation, training and export scripts |
| `training/runs/` | Training configs, logs and checkpoints (large files are gitignored) |
| `training/MODEL-CARD.md` | nafanya model card, evaluation and limitations |
| `logs/` | Run logs for long jobs |
| `docs/` | Notes and compatibility matrices |

## Status

2026-10-27: **nafanya-1.7b is the chosen model** (Qwen3-1.7B + LoRA, Q4_K_M). On the phone
it scores **131/148 (89%)** correct tool calls, 125/148 (84%) with arguments, peak RAM
**1.71 GB**, load 5 s. It is integrated into `../kuzya`: the compact prompt and compact
tool schema are the agent default. The memory-first fallback is nafanya-0.8b v2
(72/100, 72%, 0.92 GB). Details: `training/RESULTS.md`, `training/MODEL-CARD.md`.

Next: targeted training against the stable misses (line count vs `unit`, `nosleep`
inversion, step vs absolute volume, `wifi_status` phrasing) and a precise battery
comparison using current/voltage integration instead of 1% battery steps.

## Publishing to Hugging Face

Prepared but not uploaded (no account yet). After `python3 -m pip install -U huggingface_hub`
and `hf auth login`:

```sh
training/scripts/upload_hf.sh 1.7b <user>/nafanya-1.7b --public
training/scripts/upload_hf.sh 0.8b <user>/nafanya-0.8b --public
```

The script stages the PEFT adapter, the GGUF Q4_K_M, the model card
(`training/hf/README-*.md`) and the Apache-2.0 licence. The card separates model-only
numbers from the numbers with the agent's rules layer, and marks the training data as
AI-generated.

## Ground rules

- Do not modify `../kuzya` from this repository without an explicit task; if a tool or
  prompt changes there, run its tests and record the rate.
- Never commit API keys, phone data, model weights or generated datasets whose licence is
  unclear.
- Training text from the teacher model is used under the DeepSeek Open Platform Terms of
  Service, §4.2(3); record the revision and label the data as AI-generated if it is
  published. See `training/data/SOURCES.md`.
- The agent test sets in `../kuzya/tests/cases*.json` are frozen. No training example may
  overlap with them.
