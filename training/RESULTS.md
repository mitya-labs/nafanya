# Model results

All evaluations use temperature 0 and `enable_thinking=False`. **nafanya** is the tuned
model; **kuzya** is the agent that runs it. The 26-query subset is
`../kuzya/tests/cases-subset.json`; it deliberately contains hard relative-request cases.
The 148-query set is `../kuzya/tests/cases-all.json`.

| Run | Training data | Prompt | Model | 26 subset | 148 all | Notes |
|---|---|---|---|---|---|---|
| Base full | — | full 1639 tokens | Qwen3.5-0.8B BF16 | 11/26 (42%) | — | prompt-only reference |
| Base compact | — | compact 889 tokens | Qwen3.5-0.8B BF16 | 7/26 (27%) | — | no descriptions |
| nafanya-0.8b v0 | 60 seeds | compact 889 | BF16 LoRA 2L r16 | 16/26 (62%) | — | first signal |
| nafanya-0.8b v1 | 433 rows | compact 889 | BF16 LoRA 2L r16 | 16/26 (62%) | — | args improved |
| nafanya-0.8b v2 | 567 rows | compact 1118 | BF16 LoRA 2L r16 | **19/26 (73%)** | **109/148 (74%)** | positives 93/108 (86%), negatives 16/40 (40%) |
| nafanya-0.8b v2 GGUF | 567 rows | compact 1118 | merged GGUF | 18/26 (69%) | not run | export check; 543 MB file |
| nafanya-0.8b v3 | 625 rows | compact + unsupported list | BF16 LoRA 2L r16 | 11/26 (42%) | — | regression: too many step examples, absolute requests broke |
| nafanya-0.8b v2 r32 | 567 rows | compact 1118 | BF16 LoRA 2L r32 | 18/26 (69%) | — | more capacity did not help; brightness step broke |
| nafanya-0.8b v4 | 645 rows | compact + unsupported list | BF16 LoRA 2L r16 | 6/26 (23%) | — | over-refusal: hard negatives + unsupported list |
| nafanya-0.8b v5 | 610 rows | compact + unsupported list | BF16 LoRA 2L r16 | not run | — | v2 + balanced step/absolute, no hard negatives; used for 1.7B |
| nafanya-1.7b v1 | 610 rows | compact + unsupported list | Qwen3-1.7B LoRA 8L r16 | **20/26 (77%)** | **128/148 (86%)** | positives 97/108 (90%), negatives 31/40 (78%), args 121/148 (82%); ~0.23 epoch |
| nafanya-1.7b v1 GGUF F16 | 610 rows | compact + unsupported list | merged GGUF | — | 129/148 (87%) | export check |
| nafanya-1.7b v1 GGUF Q4_K_M | 610 rows | compact + unsupported list | merged + quantized | **20/26 (77%)** | **130/148 (88%)** | positives 97/108 (90%), negatives 33/40 (82%), args 124/148 (84%); 1.0 GB file |
| nafanya-1.7b v2 | 610 rows | compact + unsupported list | Qwen3-1.7B LoRA 8L r16 | 19/26 (73%) | not run | 250-iteration checkpoint; overfit, 300-iteration run crashed at 288 |
| nafanya-1.7b v2 ckpt150 | 610 rows | compact + unsupported list | Qwen3-1.7B LoRA 8L r16 | **22/26 (85%)** | not run | checkpoint 150 of the v2 run; best MLX subset score so far |
| nafanya-1.7b v6 | 637 rows | compact + unsupported list | Qwen3-1.7B LoRA 8L r16 | not run | not run | targeted v6 data; crashed at iteration 7 before a checkpoint |
| nafanya-1.7b v2 ckpt150 GGUF F16 | 610 rows | compact + unsupported list | merged GGUF | 18/26 (69%) | not run | MLX BF16 scored 22/26 on the same checkpoint: GGUF runtime differs |
| nafanya-1.7b v2 ckpt150 GGUF Q4_K_M | 610 rows | compact + unsupported list | merged + quantized | 18/26 (69%) | not run | held-out 32/40 (80%); quantization changed nothing vs F16 |
| nafanya-1.7b v7 | 831 rows (v5 + 221 targeted) | compact + unsupported list | Qwen3-1.7B LoRA 8L r16 | 35/40 dev MLX (88%), 34/40 dev GGUF (85%) | not run | ~90 iterations after a watchdog crash and resume; final held-out v2 32/40 (80%) vs 33/40 for v1 — gate not met |
| nafanya-1.7b v1 GGUF Q4 held-out | 610 rows | compact + unsupported list | merged + quantized | — | — | held-out 40: **34/40 (85%)**, args 32/40 (80%) |

## Observations

- MLX 4-bit quantization of Qwen3.5-0.8B collapses quality; all training/eval above use
  BF16.
- The compact prompt with one-line tool descriptions is the best trade-off so far:
  1118 tokens vs 1639 for the full prompt (32% shorter), and it beats the 889-token
  no-description prompt after tuning.
- Qwen3.5-0.8B supports only 2 LoRA layers at 1280 tokens on the 16 GB Mac;
  Qwen3-1.7B (standard transformer) trains 8 layers. Batch 1 is the stable setting;
  batch 4 triggers the macOS GPU watchdog, and long runs can crash even at batch 1.
- The remaining errors are refusal calibration and relative volume/brightness requests,
  not basic tool selection.

## kuzya integration

The compact prompt and schema are now the agent default (`agent.System`, `tools.Schemas()`;
full versions remain for base models). The real Go binary `kuzya-eval` on the phone with
nafanya-1.7b Q4_K_M: **131/148 (89%) tool, 125/148 (84%) args**, 0 request errors,
mean 6.2 s, load 5 s, peak RAM **1,707,144 KB**, battery 69 → 58% (0.074%/query),
battery temperature 37.3 → 47.3 °C. This matches the Python runner (131/148), so the
Go client and the compact schema do not lose accuracy. Production smoke test: the
`kuzya-server` wrapper warmed a 128 MB slot cache and `kuzya "какой заряд батареи?"`
answered with the battery state, exit 0.

## Held-out set

`training/data/heldout-40.json` — 40 fresh phrasings (28 positives, 12 negatives)
written after training; no exact duplicate against the training files or
`../kuzya/tests/cases*.json` (highest token Jaccard 0.83 on a negative paraphrase).

| Model | Tool | Args | Notes |
|---|---|---|---|
| nafanya-1.7b v1 Q4_K_M | **34/40 (85%)** | 32/40 (80%) | current phone model |
| nafanya-1.7b v2 ckpt150 Q4_K_M | 32/40 (80%) | 30/40 (75%) | worse than ckpt100 despite the MLX subset score |

Repeated misses on the held-out set (both models): `nosleep_set` on/off inversion,
`service_logs` unit/lines confusion, step vs absolute volume, and `wifi_status` for
"что с вайфаем / мощность сигнала". These are the same weaknesses as in the frozen set.

## Phone measurements

| Model | Queries | Tool | Peak RAM | Load | Battery | Temp |
|---|---:|---:|---:|---:|---:|---:|
| nafanya-1.7b Q4_K_M | 148 | 131/148 (88%) | 1.72 GB | 4 s | 94 → 77% (0.115%/query) | 30.5 → 46.5 °C |
| nafanya-1.7b Q4_K_M, first 100 | 100 | 91/100 (91%) | 1.72 GB | 4 s | 94 → 80% (cold start) | — |
| nafanya-0.8b v2 Q4_K_M | 100 | 72/100 (72%) | 0.92 GB | 2 s | 77 → 69% (0.08%/query) | 35.8 → 43.5 °C |

The 0.8B model generates about twice as fast (11–21 tok/s vs 5–8 tok/s for 1.7B) but
did not use less battery per query in this setup: both 50-query 0.8B chunks dropped
4 points. The battery counter has 1% granularity and screen/background state was not
controlled, so battery alone does not separate the two models; 1.7B wins on accuracy at
a 2× RAM cost.

Chunked battery readings are coarse (1% steps) and were not brightness- or
governor-controlled; treat them as approximate. The 1.7B cold-start chunk cost 12
points, while its warm chunks cost 0.04–0.06%/query.

## v7 targeted experiment (2026-10-27)

Goal: fix the stable misses without touching the frozen sets. 40 targeted seeds and 8
negative seeds were written by the teacher, then expanded with 164 + 43 paraphrases;
after filtering rows with token Jaccard ≥ 0.8 against `cases*.json`, `heldout-40` and
`heldout-v2`, the merged dataset has 831 rows (38% negatives).

Training was unstable again: the macOS GPU watchdog killed the run at iteration 50, and
a resumed run at iteration 40 more (~90 total). Results, GGUF Q4_K_M, same runtime:

| Model | heldout-v2 (final) | heldout-40 (dev) |
|---|---|---|
| nafanya-1.7b v1 | **33/40 (82%)**, args 32/40 (80%) | 34/40 (85%), args 32/40 (80%) |
| nafanya-1.7b v7 | 32/40 (80%), args 31/40 (78%) | 34/40 (85%), args 33/40 (82%) |

The gate (+2 points on the dev set) was not met, and v7 is one case worse on the final
set. The targeted data did not change the semantic confusions: `mute_set` and
`nosleep_set` on/off inversion, step vs absolute volume, and `wifi_status` on colloquial
phrasings remain. Decision: keep **nafanya-1.7b v1**; v7 stays as an archived experiment
(`training/runs/pilot-1.7b-v7`, `pilot-1.7b-v7b`).

The final test set `heldout-v2.json` was written independently and never used for
training or checkpoint selection.

## Energy per query (2026-10-27)

Protocol: `training/scripts/phone_energy_eval.sh`, 30 queries (`cases30.json`, the first
30 frozen cases), screen idle, no slot cache — every run pays the cold prompt prefill.
Power is sampled at 1 Hz from `current_now` × `voltage_now` and integrated over the
active window; the idle baseline is about 0.67 W.

| Model | Wall time | J per query (total) | J per query (above idle) | Accuracy on 30 |
|---|---:|---:|---:|---:|
| nafanya-1.7b Q4_K_M | 275 s | **49.9** | 43.9 | 29/30 (97%) |
| nafanya-0.8b v2 Q4_K_M | 130 s | **23.7** | — | 27/30 (90%) |

The 0.8B model costs about half the energy per query, mostly because its prompt prefill
and generation are 2–3× faster. The cold prefill dominates a 30-query batch: on the
phone the 1100-token prompt takes about 2.5 min on 1.7B. Production restores the slot
cache, so steady-state cost per query is lower than these numbers.

Caveat: the battery percentage gauge disagrees with the integration (it dropped 13
points in 4.6 min during the 1.7B run, which would imply about 25 W — impossible for
this phone). The gauge is treated as unreliable under sustained load; use joules.
