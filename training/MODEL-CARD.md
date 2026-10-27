# nafanya-1.7b — model card (draft)

nafanya is the model; kuzya is the agent that runs it. This card describes the current
best nafanya candidate.

## Base

- Base model: `Qwen/Qwen3-1.7B` (Apache-2.0).
- Training: MLX-LM BF16 LoRA, 8 last layers, rank 16, scale 16, dropout 0.05.
- 100 iterations, batch 1, max sequence 1280, `MLX_DISABLE_COMPILE=1`.
- Training data: `training/data/pilot-v5` (610 rows; 42% negatives).
- Prompt: compact system prompt + one-line tool descriptions, 1118 tokens
  (`system-prompt-compact.txt`, `tools-schema-compact2.json`).

## Evaluation

| Set | Correct tool | With args | Positives | Negatives |
|---|---|---|---|---|
| 26-query hard subset | 20/26 (77%) | 20/26 (77%) | — | — |
| 148 queries, MLX BF16 | 128/148 (86%) | 121/148 (82%) | 97/108 (90%) | 31/40 (78%) |
| 148 queries, GGUF Q4_K_M | **130/148 (88%)** | 124/148 (84%) | 97/108 (90%) | 33/40 (82%) |
| phone, 148 queries, Q4_K_M | **131/148 (88%)** | 125/148 (84%) | — | — |
| held-out 40 (fresh, never trained) | **34/40 (85%)** | 32/40 (80%) | — | — |

Phone: peak RAM **1.72 GB**, load **4 s**, battery 94 → 77% over 148 queries
(0.115%/query; warm chunks 0.04–0.06%/query), battery temperature peak 46.5 °C.
The 26-query subset is a training-hardened set and is no longer the primary signal;
use the held-out 40 for honest comparisons.

## Artifacts

- Adapter: `training/runs/pilot-1.7b/` (`adapters.safetensors`, `adapter_config.json`).
- GGUF Q4_K_M: `training/runs/pilot-1.7b/model-Q4_K_M.gguf` (1.0 GB).
- Convenience symlink: `training/models/nafanya-1.7b-Q4_K_M.gguf`.
- Phone file: `~/kuzya/models/nafanya-1.7b-Q4_K_M.gguf`.
- Held-out set: `training/data/heldout-40.json`.
- Evaluation logs: `logs/eval-1.7b-*`, `logs/eval-gguf-1.7b-*`, `logs/phone-eval-*`.

## Phone

| Model | Queries | Tool | Peak RAM | Load | Battery | Peak temp |
|---|---:|---:|---:|---:|---:|---:|
| nafanya-1.7b Q4_K_M (Python runner) | 148 | 131/148 (88%) | 1.72 GB | 4 s | 94 → 77% | 46.5 °C |
| nafanya-1.7b Q4_K_M (kuzya Go binary) | 148 | 131/148 (89%) | 1.71 GB | 5 s | 69 → 58% | 47.3 °C |
| nafanya-0.8b v2 Q4_K_M | 100 | 72/100 (72%) | 0.92 GB | 2 s | 77 → 69% | 43.5 °C |

Energy per query (30 frozen queries): **49.9 J** cold / **30.7 J** with a restored slot
cache for 1.7B; **23.7 J** cold / **15.9 J** warm for 0.8B v2, measured by integrating
`current_now` × `voltage_now` (`training/scripts/phone_energy_eval.sh`,
`phone_energy_warm.sh`). The 0.8B is about twice as cheap, mostly
because its prefill is 2–3× faster. The percentage gauge disagrees with the integration
and is treated as unreliable under sustained load.

Battery readings are 1%-step and were not brightness- or governor-controlled; treat
them as approximate. The 1.7B average is dominated by a cold-start chunk (12 points);
its warm chunks cost 0.04–0.06%/query. The 0.8B model is about twice as fast per token
but its two chunks each dropped 4 points (0.08%/query), so battery does not separate the
models in this setup. The 1.7B advantage is accuracy; the 0.8B advantage is RAM.

The Go binary `kuzya-eval` uses the production compact prompt and schema and scored the
same 131/148, so integration into the agent does not lose accuracy.

Other checkpoints: 1.7B v2 checkpoint 150 scored 22/26 on the hard subset in MLX BF16
but only 18/26 after GGUF export (F16 and Q4_K_M alike) and 32/40 on the held-out set,
so it is not an improvement over the 100-iteration adapter.

## Alternatives considered (2026-10-27)

| Model | Prompt | heldout-v2 | heldout-40 | 26 subset | Peak RAM | Warm energy |
|---|---|---|---:|---:|---:|---:|
| nafanya-1.7b v1 | compact | 33/40 | 34/40 | 20/26 | 1.71 GB | 30.7 J |
| nafanya-0.8b v2 | compact | 26/40 | 27/40 | 18/26 | 0.92 GB | 15.9 J |
| Qwen3.5-2B stock | full | 34/40 | 34/40 | 23/26 | 1.63 GB | not measured |

The 0.8B is about twice as cheap but falls to 65–68% on fresh phrasings; more LoRA layers
(3–4) diverged or scored worse. The stock 2B is equal or slightly better but needs the
full prompt and is slower. **nafanya-1.7b stays the production default**: 30.7 J per
query is about 0.056% of the battery, inside the ≤ 0.06% target, and it is the best
accuracy per joule among the stable options.

## Known limitations

- Relative vs absolute volume/brightness is still fragile: "потише", "поярче",
  "слишком громко" can be mapped to the absolute tools.
- `mute_set`/`nosleep_set` on/off is sometimes inverted.
- `service_logs` sometimes drops the `unit` argument or returns `services_running`.
- Negative requests such as "включи вайфай" and "покажи логи sshd" can still produce a
  tool call; the agent's allowlist/confirmation catches the dangerous ones.
