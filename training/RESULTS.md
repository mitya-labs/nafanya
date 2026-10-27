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
30 frozen cases), screen idle. Cold rows start the server without a cache, so they pay
the prompt prefill; slot rows restore the saved `kuzya-server` cache.
Power is sampled at 1 Hz from `current_now` × `voltage_now` and integrated over the
active window; the idle baseline is about 0.67 W.

| Model | Cache | Wall time | J per query | Above idle | Accuracy on 30 |
|---|---|---:|---:|---:|---:|
| nafanya-1.7b Q4_K_M | cold | 275 s | **49.9** | 43.9 | 29/30 (97%) |
| nafanya-1.7b Q4_K_M | slot | 166 s | **30.7** | 26.2 | 29/30 (97%) |
| nafanya-0.8b v2 Q4_K_M | cold | 130 s | **23.7** | — | 27/30 (90%) |
| nafanya-0.8b v2 Q4_K_M | slot | 86 s | **15.9** | 11.5 | 27/30 (90%) |
| nafanya-1.7b + rules | slot | 46 s | **8.9** | 7.2 | 30/30 (100%) |
| nafanya-0.8b v2 + rules | slot | 22 s | **4.4** | 3.7 | 27/30 (90%) |

The slot cache cuts about 40% of the energy per query: 49.9 → 30.7 J for 1.7B and
23.7 → 15.9 J for 0.8B. The 0.8B costs about half the energy of the 1.7B either way,
and is about twice as fast (2.9 s vs 5.5 s per query warm).

The 0.8B model costs about half the energy per query, mostly because its prompt prefill
and generation are 2–3× faster. The cold prefill dominates a 30-query batch: on the
phone the 1100-token prompt takes about 2.5 min on 1.7B. Production restores the slot
cache, so steady-state cost per query is lower than these numbers.

Caveat: the battery percentage gauge disagrees with the integration (it dropped 13
points in 4.6 min during the 1.7B run, which would imply about 25 W — impossible for
this phone). The gauge is treated as unreliable under sustained load; use joules.

## Baseline check: Qwen3.5-2B without tuning (2026-10-27)

The 2B model was the "upper bound" in the early plan but had never been measured on the
new held-out sets. Q4_K_M, llama-server, temperature 0:

| Prompt | heldout-v2 | heldout-40 | 26 subset |
|---|---|---|---|
| full 1639 tokens | **34/40 (85%)**, args 33/40 | **34/40 (85%)**, args 33/40 | **23/26 (88%)**, args 23/26 |
| compact 1118 tokens | 32/40 (80%), args 26/40 | 34/40 (85%), args 28/40 | 21/26 (81%), args 15/26 |

For comparison, nafanya-1.7b v1 on the compact prompt: 33/40, 34/40 and 20/26. The
untuned 2B with the full prompt is therefore equal or slightly better on all three sets,
and clearly better on arguments on the hard subset. It needs the full prompt: the
compact one costs 5–8 argument matches on the subset and the final set.

This does not meet the decision rule's spirit — the tuned 1.7B does not beat the
prompt-only larger baseline. The next step is a phone run of 2B + full prompt (peak RAM,
load, battery) before revisiting the model choice.

## Fresh-set comparison (2026-10-27)

All numbers are GGUF Q4_K_M with the prompt each model needs, temperature 0.

| Model | Prompt | heldout-v2 (final) | heldout-40 (dev) | 26 subset | Peak RAM | Warm energy |
|---|---|---|---:|---:|---:|---:|
| nafanya-1.7b v1 | compact | 33/40 (82%) | 34/40 (85%) | 20/26 (77%) | 1.71 GB | 30.7 J |
| nafanya-0.8b v2 | compact | 26/40 (65%) | 27/40 (68%) | 18/26 (69%) | **0.92 GB** | **15.9 J** |
| Qwen3.5-2B | full | **34/40 (85%)** | **34/40 (85%)** | **23/26 (88%)** | 1.63 GB | not measured |

The frozen 148-query set flatters the 0.8B (74%); on fresh phrasings it drops to 65–68%.
The 1.7B holds 82–85%, and the untuned 2B is equal or slightly better but needs the full
prompt and is slower per query.

## 0.8B capacity experiment (2026-10-27)

The 0.8B model was limited to 2 LoRA layers at 1280 tokens. Tried more capacity:

- 4 layers at 1024 tokens: loss went to NaN. Cause: every training example is 1108–1164
  tokens, so 1024 truncates all of them and removes the assistant target.
- 3 layers at 1280 tokens, lr 5e-5: trained, but the loss jumped 0.118 → 0.943 at
  iteration 40 and the run crashed on the GPU watchdog. Checkpoint 30 scored 26/40 on
  heldout-40 (65%), checkpoint 40 scored 17/40 (42%) — both worse than the 2-layer v2
  (27/40, 68%).

Conclusion: 2 layers is the stable maximum for this model on the 16 GB Mac; more capacity
hurts. The v2 adapter stays.

## Qwen3.5-2B phone check (partial, 2026-10-27)

Stopped early because it cannot win on the stated economy priority: 40 of 148 queries,
37 correct (92%), peak RAM 1,632,716 KB, load 4 s, battery 39 → 31% and 46 °C, with
6–13 s per query in the server log. The full prompt is 1639 tokens and the server is
slower than the 1.7B, so energy per query is expected to be higher, not lower.
The Mac numbers above are complete.

## Rules layer on top of the model (2026-10-27)

The model fails on the same semantic classes again and again: on/off inversion for
`mute_set`/`nosleep_set`, step vs absolute volume, a line count read as a service name,
refusals for ssh/sshd and "all services", and no call for colloquial `wifi_status`.
These are deterministic, so `../kuzya/internal/rules` handles them without the model:

- `Refusal` — hard negatives (wifi on/off, ssh/sshd, all services, stop, arithmetic)
  return a text refusal before any model call;
- `Preroute` — high-confidence commands (battery, volume/brightness get/set/step,
  mute/nosleep, service logs/restart, wifi status/connect, services) call the tool
  directly, with numbers recognised both as digits and as words;
- `Repair` — after the model, fixes the unit/lines of `service_logs`, mute/nosleep mode,
  and the step direction.

`kuzya-eval --rules` applies the same logic; the agent uses it by default.

| Set | Model only | Model + rules | Share served by rules |
|---|---:|---:|---:|
| 148 frozen (in-sample for the rules) | 131/148 (89%) | **148/148 (100%)** | 93/148 (63%) |
| heldout-40 (dev) | 34/40 (85%) | **40/40 (100%)** | 31/40 (78%) |
| heldout-v2 | 33/40 (82%) | **40/40 (100%)** | 33/40 (82%) |
| heldout-v3 (fresh, final) | 32/40 (80%), args 27/40 (68%) | **39/40 (98%), args 38/40 (95%)** | 31/40 (78%) |
| heldout-v2, nafanya-0.8b v2 | 26/40 (65%) | 35/40 (88%), args 35/40 | ~78% |
| heldout-v3, nafanya-0.8b v2 | 27/40 (68%) | 35/40 (88%), args 34/40 | ~78% |

The 148 and heldout-40 numbers are optimistic because the rules were written from those
failures. The honest estimate is **heldout-v3: 80% → 98%** (+7 tool matches, +11 argument
matches) with 78% of requests never reaching the model. On heldout-v3 one case remains
("активируй вайфай", fixed afterwards by adding the verb to the refusal list — that case
is now in-sample) and one is genuinely ambiguous ("выключи режим без звука": the model
sets mute on, the label says off).

Phone run with rules (2026-10-27, nafanya-1.7b Q4_K_M, 148 queries, charging): **148/148
(100%) tool and args**, mean **2.4 s** per query instead of 6.2 s, load 3 s, peak RAM
**1.71 GB**. Warm energy with rules, unplugged, 30 queries: **8.9 J** for 1.7B and
**4.4 J** for 0.8B — about 3.5× less than without rules, i.e. 0.016% and 0.008% of the
battery per query, far below the 0.06% target.

Because pre-routed requests do not touch the model, they cost almost no energy: with a
63–82% rules share the average model work per query drops by the same factor. A rough estimate from the measured 30.7 J/query warm is 0.37 × 30.7 ≈ 11 J per query
(~0.02% of the battery) for a mix like the frozen set. With rules the model is called for
only about 22% of heldout-v3 queries, so the energy difference between the 0.8B and 1.7B
narrows: roughly 4 J vs 8 J per query, both far below the 0.06% target. The remaining
trade-off is RAM (0.92 vs 1.71 GB) against accuracy (88% vs 98%).
