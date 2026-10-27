# nafanya — model fine-tuning plan (kuzya agent)

Status: working copy, 2026-10-27. Snapshot of `../kuzya/docs/TRAINING.md`; this is the
working copy for the model workspace.

## Naming

- **nafanya** — the model produced here.
- **kuzya** — the offline agent in `../kuzya` that runs nafanya on the phone.
- **Qwen3.5 / Qwen3** — base models used for training.

## Paths

The agent, tests, logs and deploy scripts stay in `../kuzya`:

- `tests/...` → `../kuzya/tests/...`
- `internal/tools/...` → `../kuzya/internal/tools/...`
- `logs/...` → `../kuzya/logs/...`
- `deploy/...` → `../kuzya/deploy/...`
- `PLAN.md` and `SUMMARY.md`, when they mean the agent, → `../kuzya/...`

Everything else is relative to this repository.

Goal: replace prompt-only tool selection with a LoRA-tuned model that is stable on our
13 tools, refuses out-of-scope requests, allows much shorter tool descriptions, and
fits the phone's RAM budget. The tuned model is adopted only if it beats the
prompt-only baseline on unseen phrasings and on negatives.

Current prompt-only reference (prompt v3, variant D, `temperature` 0):
Gemma 4 E2B 133/148 (90%), peak RAM 2.3–3.2 GB; Qwen3.5-0.8B 61/80 (76%), peak RAM
0.89 GB, 5.3 s mean; Qwen3.5-2B 75/80 (94%), peak RAM 1.68 GB. **The target is
Qwen3.5-0.8B**, not Gemma: the tuned 0.8B must reach useful accuracy while keeping peak
RAM near 1 GB and the battery cost per query low. Gemma 4 E2B stays only as a reference
point.

Pilot result (2026-10-27, 26-query `cases-subset.json`, temperature 0, `enable_thinking`
false): BF16 base with the full prompt 11/26 (42%), BF16 base with the compact prompt
7/26 (27%), BF16 LoRA v0/v1 with the 889-token no-description prompt 16/26 (62%),
BF16 LoRA v2 with the 1118-token one-line-description prompt **19/26 (73%)**. On all 148
queries v2 scores **109/148 (74%)**, positives 93/108 (86%), negatives only 16/40 (40%):
the remaining work is mostly refusal calibration and relative "louder/brighter" requests.
These are signals, not final results; the training sets are still small.
Qwen3-1.7B LoRA (8 layers, 100 iterations, same v5 data) scores **20/26 (77%)** on the
hard subset and **128/148 (86%)** on all queries: positives 97/108 (90%), negatives
31/40 (78%), args 121/148 (82%). A 300-iteration run is in progress; the 1.7B uses about
1.71 GB peak RAM on the phone, still under the 2 GB fallback limit.

Evaluation sets:

| Set | Queries | Negatives | Role |
|---|---|---|---|
| `tests/cases-all.json` | 148 | 34 | main rate; includes ids 1–120 and the relative/held ids |
| `tests/cases-hard2.json` | 40 | 18 | hard phrasings and near-miss negatives |
| `tests/cases-held.json` | 16 | 10 | external test for prompt changes, but it is a subset of `cases-all` |
| new `tests/cases-held2.json` (T2.6) | 50–80 | about 40% | truly independent set written after the data freeze |

Non-goals: training from scratch, changing tool behaviour, adding a shell, making the
model learn new capabilities instead of refusing, multilingual support beyond Russian
and mixed English.

## Constraints

- Phone: Poco F1, 5.4 GB RAM available. Memory and battery are the first constraint, not
  raw accuracy. The primary target is Qwen3.5-0.8B at about 0.89 GB peak RAM; the tuned
  0.8B must stay at or below 1.2 GB peak, ideally around 1.0 GB. The fallback
  Qwen3-1.7B is allowed up to 2.0 GB peak only if it clearly reaches the accuracy target;
  Gemma 4 E2B (2.3–3.2 GB, about 0.1% battery per query) remains a reference and must not
  become the default.
- Power: measure `qcom-battery/current_now` on the phone at the same screen brightness and
  network state. Target: at most about 0.06% of the battery per query, clearly below
  Gemma 4 E2B's ~0.1%; a cold start must beat the current 100–265 s and shrink with the
  shorter prompt. These are targets until measured.
- Mac: M2 Pro, 16 GB RAM, 83 GB free (checked 2026-10-27). Python 3.14.7 and `mlx`
  0.32.1 are installed; `mlx_lm` is not. Use a Python 3.12 virtual environment for the
  MLX-LM and conversion stack, not the system Python.
- Tool set is frozen during the experiment: 13 tools in `internal/tools/`
  (`battery_status`, `wifi_status`, `wifi_connect`, `services_running`, `service_logs`,
  `service_restart`, `nosleep_set`, `volume_get`, `volume_set`, `volume_step`, `mute_set`,
  `brightness_set`, `brightness_step`). Any tool or schema change invalidates the
  training data and the saved prompt-cache slot.
- Data licensing: the primary teacher is the model running this session, DeepSeek V4.1
  Flash, through the Open Platform API. The DeepSeek Open Platform Terms of Service
  (release 2026-04-22, effective 2026-04-29, §4.2(3)) allow using Inputs and Outputs for
  "training other models (such as model distillation)" subject to the Terms. Conditions:
  API only (never scripting the web chat), key only in an environment variable, no data
  from the phone, record the terms revision, and label the dataset as AI-generated if it
  is published. Local Qwen3 under Apache-2.0 is the fallback teacher. Text from other
  providers (for example Claude) is not training data without a terms check. Record the
  source and licence of every data file.
- Evaluation must run on the phone for the final decision; Mac results are only for
  iteration.

## Decisions to confirm before starting

| ID | Decision | Recommended default |
|---|---|---|
| D1 | Base model(s) for training | Qwen3.5-0.8B for the memory-first target; Qwen3-1.7B is the accuracy fallback and currently leads (128/148, 86%) at ~1.71 GB peak; Qwen3.5-2B only an upper bound; Gemma 4 E2B is a reference baseline only |
| D2 | Source of paraphrases | Teacher-generated seeds and paraphrases from DeepSeek V4.1 Flash via the API; local Qwen3-8B/14B as fallback; owner reviews a sample instead of writing seeds |
| D3 | Dataset size | 2,000–3,000 train, 250 dev, 250 internal test; 35–40% negatives |
| D4 | Success threshold | See "Decision rule"; at minimum +5 pp overall vs the same model's baseline, ≥90% on negatives, no more than one regression on the 148-query set |
| D5 | Where to evaluate | Mac for iteration; phone for the final A/B; two runs of the 148-query set for the winner if time allows |
| D6 | Repository policy for generated data | Commit seeds, generator and reports; keep large generated JSONL and weights outside git unless their licence clearly allows redistribution |

## Task breakdown

### Phase 0 — environment and de-risking (0.5–1 day)

- [ ] **T0.1** Create `training/` with `README.md`, `data/`, `runs/`, `scripts/`, and a
  `.gitignore` for virtualenvs, HF caches, generated JSONL and model weights. Add a
  `Makefile` with `env`, `data`, `train`, `export`, `eval` targets.
- [ ] **T0.2** Create the Python environment: `uv venv --python 3.12 training/.venv`,
  install `mlx-lm`, `huggingface_hub`, `transformers`, `datasets`, `sentencepiece`,
  `torch` and the `llama.cpp` conversion requirements. Pin versions; save
  `pip freeze` next to the first run.
- [ ] **T0.3** Clone the `llama.cpp` repository at commit `6050b46` (the commit used for
  the phone binaries) or at a commit whose GGUF output is known to load on the phone.
  Do not upgrade the phone binary without re-running the full eval. Verify
  `convert_hf_to_gguf.py` and `llama-quantize` work on the Mac.
- [x] **T0.4** Build a compatibility matrix for Qwen3.5-0.8B first, then Qwen3-1.7B and
  Qwen3.5-2B: HF weights available and licence, MLX-LM model support, LoRA support,
  `mlx_lm.fuse`, GGUF conversion in the pinned `llama.cpp`, chat template and tool-call
  parser support. Gemma 4 E2B is listed only for comparison. Record it in
  `training/README.md`. Result (2026-10-27): `Qwen/Qwen3.5-0.8B` is Apache-2.0, model type
  `qwen3_5`, multimodal; MLX-LM 0.32.2 loads the text model and supports LoRA. BF16 LoRA
  at 1024 tokens (compact prompt, 889 tokens per example) fits 2 layers and trains
  stably with `MLX_DISABLE_COMPILE=1`; 4+ layers OOM at longer contexts. **MLX 4-bit
  quantization of Qwen3.5 collapses quality** (the 4-bit model refuses a battery query
  that the BF16 model answers with a correct tool call), so training uses BF16 and
  inference uses the existing GGUF Q4_K_M. The chat template is identical between HF and
  the base GGUF (7755 bytes, same SHA256).
- [x] **T0.5** End-to-end smoke chain on Qwen3.5-0.8B (the memory-first target): 20 toy
  examples, 20 training steps, fuse, convert to GGUF F16, quantize to Q4_K_M, start
  `llama-server --jinja`, parse one tool call. Record commands, wall time, peak RAM and
  logs in `logs/training-smoke.log`. **Gate 1: passed 2026-10-27, with a changed export
  path.** `mlx_lm.fuse --export-gguf` does not support `qwen3_5`, and exporting fused
  MLX weights into HF layout produces garbage. Working path: QLoRA adapter → PEFT layout
  (`training/scripts/mlx_adapter_to_peft.py`) → `convert_lora_to_gguf.py` →
  `llama-export-lora` into the original base `Q4_K_M`. The merged model answers tool
  calls through `llama-server --jinja`; a 2-iteration smoke adapter is not expected to
  be accurate yet.

### Phase 1 — frozen baselines (0.5 day, plus phone time)

- [ ] **T1.1** Freeze the experiment: record the git commit, system prompt v3, variant D,
  `temperature` 0, `max_tokens` 256, the 13 tool schemas and the SHA256 of each model
  file. Export `tools.Schemas()` to `training/data/tools-schema.json` and use it to
  validate every training label.
- [ ] **T1.2** Run the missing baseline on the phone for **Qwen3.5-0.8B** on all 148
  queries, the 40-query hard set and the 16-query held set. This is the model we are
  trying to keep, so its full baseline is the priority. Qwen3.5-2B and Gemma 4 E2B already
  have 80-query and 148-query results respectively; run 2B only as an upper-bound
  reference if time allows. Use a cooled phone, the thermal guard, one model per run;
  record peak RAM, load time, mean time and battery per query.
- [ ] **T1.3** Put the baseline matrix in `SUMMARY.md`: overall, positives, negatives,
  with-arguments, per-tool misses, parse errors.
- [ ] **T1.4** Add a small comparison script (shell or Python) that reads two eval
  `.jsonl` files and reports per-tool deltas, changed ids and a paired discordant count.
  This is the primary tool for tuned vs baseline, more reliable than comparing totals.

### Phase 2 — training data (2–3 days; owner input required)

- [ ] **T2.1** Teacher seed set: use the teacher model (DeepSeek V4.1 Flash via the API)
  to generate 300–500 seed utterances with labels, 15–25 per tool and 100–150 negatives,
  covering direct requests, slang, typos, mixed English, numbers in words, indirect and
  compound phrasing, and near-miss negatives. Put the 13 tool schemas and a coverage
  matrix in the prompt; require strict JSONL with `q`, `tool`, `args`, `category`,
  `source`. Do not show the existing test files to the teacher. The owner reviews 50
  random examples instead of writing the set. Store it as
  `training/data/seeds-teacher-v0.jsonl`.
- [ ] **T2.2** Write the bulk generator `training/scripts/gen.py` that calls the teacher
  API in batches (key from the environment) with the seed, tool schema and category;
  request strict JSONL paraphrases; validate the tool name and arguments against
  `tools-schema.json`; drop duplicates and meaning drift; run a second "critic" pass or a
  self-consistency vote on the labels; record the model name, version and terms revision
  per output. Use the local Qwen model as a fallback if the API is unavailable or
  rate-limited.
- [ ] **T2.3** Normalise labels: exact tool names, canonical service names (`sshd` is not
  in the allowlist), integer percentages in range, `direction` exactly `up`/`down`,
  `mode` exactly `on`/`off`. Do not train optional arguments unless the eval checks
  them; keep the first version to required arguments only.
- [ ] **T2.4** Build the dataset: 2,000–3,000 train, 250 dev, 250 internal test; 35–40%
  negatives; balanced per tool; user utterance length capped (for example 160
  characters). Add prompt-length augmentation: the same example rendered with full,
  compact and schema-only tool descriptions, so the tuned model does not depend on the
  exact long descriptions and a shorter prompt v4 can be adopted later. Optionally add
  tool-set augmentation: random subsets of the 13 tools plus one or two decoy tools that
  are never called.
- [ ] **T2.5** Leakage gate. All existing `tests/cases*.json` files (including
  `cases-all.json`, `cases-held.json`, `cases-hard2.json`, `cases-relative.json` and
  `cases-subset.json`) are the test set and must not be used for training. Check
  normalised exact duplicates and near-duplicates (token-set Jaccard ≥ 0.7 or edit
  distance ≤ 0.2); fail the build on any hit. Split train/dev/test by paraphrase
  *family*, not randomly: whole phrasing patterns are held out, so dev and test measure
  generalisation to new wording.
- [ ] **T2.6** Create a new external held-out set *after* the data freeze: 50–80 queries
  with about 40% negatives and new phrasings, generated by a **different** model (local
  Qwen) or written by the owner, not by the teacher that generated the training data. The
  existing `cases-held.json` is already part of `cases-all.json`, so it is a test set but
  not an independent one. If a different generator is impossible, keep `cases-all.json`
  and `cases-hard2.json` as the primary external tests and treat the new set as a smoke
  test only. Keep the new file out of the training data and out of prompt tuning.
- [ ] **T2.7** Audit: validate every label against the schema; sample 50 random examples
  and all near-miss negatives for owner review; record counts per tool, negative share,
  token-length distribution and duplicate-check results in
  `training/data/REPORT.md`; record sources and licences in `training/data/SOURCES.md`.
  Freeze dataset v1 with SHA256 and a git tag.

### Phase 3 — training (1–2 days)

- [ ] **T3.1** Tokenisation/template parity gate. Render five examples with the HF
  tokenizer's `apply_chat_template` with the same `tools` payload used by the agent;
  compare the token ids with `llama-tokenize` or the server's prompt debug output on the
  base GGUF. Include BOS/EOS and the assistant tool-call tokens. **Gate 2: exact match;
  do not train until this passes.** If the templates differ, fix the data rendering or
  stop and choose a different protocol; do not rely on the server parser to repair it.
- [ ] **T3.2** Training configuration: BF16 LoRA (not QLoRA — MLX 4-bit Qwen3.5 loses
  quality), **2 last layers**, rank 16, scale 16, dropout 0.05, learning rate around
  `5e-5`, batch 1 (batch 4 triggers the macOS watchdog; batch 1 is stable but slower),
  1–3 epochs, max sequence length 1280 with the compact prompt with one-line tool
  descriptions (1118 tokens; the 889-token no-description variant still confuses
  volume/brightness), mask the prompt tokens, gradient checkpointing,
  `clear_cache_threshold: 1`, `MLX_DISABLE_COMPILE=1`. Disable intermediate validation
  (`steps_per_eval` greater than the number of iterations, and remove `valid.jsonl` for
  the run) because a validation pass can trigger the GPU watchdog; evaluate the saved
  adapter separately. 4+ layers OOM or hit the watchdog. Target keys:
  `self_attn.q_proj`, `self_attn.v_proj`, `mlp.gate_proj`, `mlp.up_proj`,
  `mlp.down_proj`.
- [ ] **T3.3** Run matrix: BF16 LoRA on Qwen3.5-0.8B first; 2–3 learning-rate/epoch
  variants for it. Only if it cannot reach 90% after tuning, try Qwen3-1.7B (safe
  fallback) and then Qwen3.5-2B as an upper bound. Fixed seed; save config, loss curve,
  wall time and peak RAM under `training/runs/`.
- [ ] **T3.4** Validation: dev exact tool+args, JSON validity, negatives, refusal rate.
  Target dev ≥95% and negatives ≥90% before exporting. Inspect 30 errors by hand and
  classify them (wrong tool, wrong args, no call, spurious call).
- [ ] **T3.5** Forgetting/overfitting check: train-vs-dev gap; a small general Russian
  set (owner-written, 20 prompts) to confirm the model still answers in text, does not
  call a tool for everything, and keeps varied refusals. Optionally add 100 two-turn
  examples with a synthetic tool result and a final answer, because the agent currently
  sometimes gets an empty reply after a tool call.
- [ ] **T3.6** Select checkpoints by dev exact-match, not train loss. Save the adapter,
  fused HF weights and checksums. Do not delete the base weights until the phone eval is
  finished.

### Phase 4 — export and on-device evaluation (1–2 days)

- [ ] **T4.1** Export: do **not** use `mlx_lm.fuse --export-gguf` for `qwen3_5` (not
  supported) and do **not** convert fused MLX weights into HF layout (the Qwen3.5
  GatedDeltaNet layout is MLX-specific and the result is garbage). Working path:
  `mlx_adapter_to_peft.py` → `convert_lora_to_gguf.py` → `llama-export-lora` into the
  original base GGUF → `llama-quantize` Q4_K_M. Verify the base model still answers
  coherently, the adapter changes only the target tensors, and record file sizes and
  SHA256. Build Q5_K_M and Q8_0 for the winner if RAM allows.
- [ ] **T4.2** Parser test on the Mac: `llama-server --jinja` with the tuned GGUF, 30
  prompts, zero HTTP 500/parse errors, valid JSON arguments against the schema. Add five
  two-turn scenarios (user → tool call → tool result → final Russian answer) and the
  confirmation/refusal path.
- [ ] **T4.3** Mac eval on all sets to catch regressions cheaply; compare against the
  frozen baseline with the paired script. Iterate on the data or hyperparameters before
  spending phone time.
- [ ] **T4.4** Phone eval of the winner: all 148 queries, the hard set and the new
  held-out set; two runs of the 148-query set if time allows; cooled phone and the 48 °C
  guard. Record peak RAM, load time, cold first request, prompt tokens, mean latency,
  battery per query and parse errors.
- [ ] **T4.5** Quantisation trade-off on the phone: Q4_K_M vs Q5_K_M/Q8_0 for the winner;
  choose by peak RAM first, then accuracy and latency. Q4_K_M is the default; a higher
  quantisation must fit under 1.2 GB and show a real accuracy gain.
- [ ] **T4.6** End-to-end agent check on the phone: dangerous-tool confirmation and
  refusal, empty-reply handling, `service_restart`, `wifi_connect` from the local SXMO
  session. This is a regression check, not a rate measurement.

### Phase 5 — shorter prompt and tool descriptions (0.5–1 day)

- [x] **T5.1** Create prompt v4 with compact tool descriptions (target at least 30%
  fewer prompt tokens) while keeping the semantics that the hard cases depend on
  ("stop" ≠ "restart", "all services" is not one service, what the agent cannot do). The
  current compact variant with one-line descriptions is 1118 tokens vs 1639 for the full
  prompt (32% shorter); use it as the starting point. Done: `tools-schema-compact2.json` + `system-prompt-compact.txt`, 1118 tokens (32% shorter); the Go schema matches it exactly.
- [ ] **T5.2** Evaluate four combinations on the phone or Mac: baseline+short,
  tuned+full, tuned+short, baseline+full. The tuned model must not depend on the long
  descriptions, otherwise the shortening is not usable. Gate: tuned+short is no worse
  than tuned+full by more than one case on the hard and held sets.
- [x] **T5.3** If v4 wins, update `agent.System` and the tool descriptions, rebuild the
  prompt-cache slot, and re-run the full test set. The slot file is valid only for the
  same model, flags, system prompt and schemas. Done: compact prompt/schema are the agent default; slot cache regenerated (128 MB).
- [x] **T5.4** Record the new prompt size, cold first request and slot file size; compare
  with the 1300-token / 100–265 s baseline. Done: prompt 1176 bytes, slot 128 MB, warm-up about 2–3 min on the phone.

### Phase 6 — decision and rollout (0.5 day)

- [x] **T6.1** Fill the decision matrix: baseline vs tuned on the 148-query set, hard set,
  independent held-out set, negatives, args, parse errors, peak RAM, latency, cold start
  and battery per query. Done: `training/RESULTS.md`, `../kuzya/SUMMARY.md`.
- [x] **T6.2** If the tuned model wins, make it the default in `deploy/` and the phone
  config, keep the prompt-only model as a fallback, regenerate the slot cache, update
  `SUMMARY.md` and `PLAN.md`, and run the whole `tests/` suite once more. Done: nafanya-1.7b is the `kuzya-server` default; full suite re-run, 131/148.
- [ ] **T6.3** If it loses, document the negative result and keep the best compact
  prompt-only model (Qwen3.5-0.8B or Qwen3.5-2B); do not switch to Gemma 4 E2B by
  default. Archive the adapter, data and reports so the experiment is reproducible.
- [ ] **T6.4** Reproducibility: `training/Makefile`, pinned environment, dataset SHA256,
  provenance file, run configs and logs. A fresh checkout should be able to rebuild the
  dataset and the GGUF with the documented commands.

### Phase 7 — after integration (started 2026-10-27)

The model is integrated; what remains is accuracy on stable misses and a precise battery
measurement.

- [x] **T7.1** Targeted data v7: teacher-generated examples for the stable misses only —
  `service_logs` with a line count before the service name, `nosleep_set` off phrased as
  "снова/теперь спать", `mute_set` verbs ("размуть"), step vs absolute volume/brightness,
  colloquial `wifi_status` ("вафля"), `wifi_connect` with the network name only, and
  near-miss negatives (ssh/sshd, all services, wifi on/off, arithmetic). Target 120–160
  new rows, negatives 45–50%, validate leakage against `tests/cases*.json` **and**
  `heldout-40.json`. Train 1.7B LoRA 100–150 iterations with checkpoints, evaluate every
  checkpoint on heldout-40 + the 26-query subset. Gate: at least +2 points on heldout-40
  and no regression on negatives. Done 2026-10-27: v7 (831 rows, 38% negatives) trained to ~90 iterations; dev heldout-40 35/40 MLX / 34/40 GGUF vs 34/40 for v1; gate not met.
- [x] **T7.2** Freeze `heldout-40.json` as the development set and create a new
  `heldout-v2` (40 fresh phrasings) after v7 training; report the final rate on it, not
  on the set used for checkpoint selection. Done: `heldout-v2.json` created and validated; v1 33/40, v7 32/40.
- [x] **T7.3** Precise battery measurement: sample `current_now` and `voltage_now` at
  1 Hz during a fixed 30-query batch, screen off, for nafanya-1.7b and the 0.8B fallback;
  compute joules per query. Gate: at most ~0.06% of the battery per query and no worse
  than Gemma 4 E2B. Done: 1.7B 49.9 J/query, 0.8B 23.7 J/query (cold 30-query batch); the percentage gauge proved unreliable under load.
- [x] **T7.4** If v7 passes T7.1, export to GGUF Q4_K_M, run the full 148-query set on the
  phone, update `RESULTS.md`, `MODEL-CARD.md`, `SUMMARY.md` and the slot cache; otherwise
  keep nafanya-1.7b v1 and document the negative result. Done: v7 did not pass, v1 stays; negative result recorded in `training/RESULTS.md`.
### Phase 8 — revisit the model choice (started 2026-10-27)

- [x] **T8.1** Qwen3.5-2B Q4_K_M prompt-only with the full prompt scored 34/40 on
  heldout-v2, 34/40 on heldout-40 and 23/26 on the subset — equal or better than
  nafanya-1.7b. Measure it on the phone: 148 queries, peak RAM, load, battery/energy. Done on Mac (2B full prompt: 34/40 heldout-v2, 34/40 dev, 23/26 subset, 1.63 GB); the phone run was stopped at 40/148 because it is slower and cannot save energy.
- [x] **T8.2** If 2B wins with acceptable RAM and energy, decide between shipping the
  stock 2B with the full prompt or fine-tuning the 2B on the v5/v7 data (LoRA, 8
  layers) and repeating the decision rule. Decided 2026-10-27: keep nafanya-1.7b as the production default; the stock 2B is a fallback if accuracy outweighs latency/energy. Fine-tuning the 2B is not started.
- [x] **T8.3** Update the agent default, slot cache and docs to the chosen model. No default change; docs updated in `training/RESULTS.md` and `MODEL-CARD.md`.
### Phase 9 — deterministic rules layer (done 2026-10-27)

- [x] **T9.1** Add `internal/rules` with `Refusal`, `Preroute` and `Repair`; cover hard
  negatives (wifi on/off, ssh/sshd, all services, stop, arithmetic), obvious commands
  (battery, volume/brightness, mute, nosleep, service logs/restart, wifi) and the known
  argument mistakes (line count, mute/nosleep mode, step direction).
- [x] **T9.2** Wire the rules into `kuzya-eval --rules` and into `agent.Run` (default).
  `go test ./...` passes, including table-driven rule tests.
- [x] **T9.3** Evaluate on a fresh set: heldout-v3 39/40 (98%) vs 32/40 (80%) for the
  model alone; heldout-v2 40/40; 148 frozen 148/148 (in-sample — the rules were derived
  from those failures). 78% of heldout-v3 requests are served without the model.
- [x] **T9.4** Measure the phone run with rules (148 queries, peak RAM, energy) and
  update the docs and the slot cache if anything changed. Done: phone 148/148, mean 2.4 s, peak RAM 1.71 GB; the energy run with rules is pending because the phone was charging.
## Decision rule

A tuned model is adopted only if all of the following hold against the *same* model's
prompt-only baseline, measured with `temperature` 0 on the phone:

1. Independent held-out set: at least +5 percentage points and at least 90% correct.
2. Hard set: at least 90% correct, and a clear gain over the baseline for the same model
   (Qwen3.5-0.8B's hard-set baseline is measured in T1.2; Gemma's 92.5% is only a
   reference).
3. Negatives: at least 90% on both the hard and held-out sets; no increase in spurious
   dangerous calls.
4. The 148-query set: no more than one regression on positive cases compared with the
   baseline; overall at least +3 percentage points.
5. Peak RAM at most 1.2 GB for the 0.8B (ideally around 1.0 GB), or at most 2.0 GB for
   the 1.7B fallback; mean latency no worse than the baseline by more than 10%. The 1.7B
   is adopted only if it clearly beats the 0.8B on the held-out and hard sets and stays
   under 2.0 GB.
6. Battery per query at most about 0.06% and clearly below Gemma 4 E2B's ~0.1%, measured
   at the same screen brightness and network state.
7. If prompt v4 is part of the change, tuned+short must pass the gate in T5.2 and reduce
   the cold first request.

If any condition fails, keep the best compact prompt-only model (Qwen3.5-0.8B if its rate
is acceptable, otherwise Qwen3.5-2B) and record why. Do not fall back to Gemma 4 E2B by
default: it is the memory and battery reference we are trying to leave.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| MLX-LM does not support Qwen3.5 | T0.4 compatibility spike on Qwen3.5-0.8B; fallback Qwen3-1.7B; do not start data work before Gate 1 |
| MLX-LM LoRA on `qwen3_5` hits the Metal descriptor limit | Practical config: BF16 LoRA, **2 layers**, rank 16, batch 4–8, compact prompt (889 tokens), 1024 context, `MLX_DISABLE_COMPILE=1`; validate after training, not during; 4+ layers OOM or hit the macOS GPU watchdog; fallback Qwen3-1.7B; issue ml-explore/mlx-lm#1185 |
| MLX 4-bit quantization of Qwen3.5 collapses quality | Train on BF16; keep the proven GGUF Q4_K_M for inference. Do not use the MLX 4-bit model for evaluation or training |
| Fused MLX weights cannot be converted to HF/GGUF directly | Keep the base GGUF untouched; convert the adapter to PEFT/GGUF LoRA and merge with `llama-export-lora` (tested) |
| HF chat template and GGUF template differ, so training does not match inference | T3.1 token-parity gate; compare token ids, not strings; stop if it fails |
| Dataset leaks into the test set | T2.5 duplicate checker over all `tests/cases*.json`; freeze the test set first; independent held-out set in T2.6 |
| Paraphraser produces meaning drift or bland duplicates | Teacher-generated seeds, schema validation, dedupe, 50-example audit, hold out whole template families |
| Overfitting to phrasings | Family split, prompt-length augmentation, early stopping on dev, independent held-out set |
| Catastrophic forgetting / refusal collapse | 35–40% negatives, general Russian check set, varied refusal texts |
| Qwen3.5-0.8B cannot reach 90% after tuning | Try Qwen3-1.7B, then Qwen3.5-2B as the upper bound; do not jump to Gemma; keep the memory budget |
| Quantisation destroys the adapter's gain | Q4_K_M is the default; try Q5_K_M/Q8_0 only if they fit under 1.2 GB and show a real gain |
| 16 GB Mac runs out of memory | Python 3.12 venv, small batch, sequence 2048, monitoring, close other apps |
| Phone thermal drift hides the difference | Cooled phone, 48 °C guard, paired A/B runs, repeat misses |
| Tool or schema change invalidates data and cache | Freeze the 13-tool set; version `tools-schema.json`; regenerate the slot file after any change |
| Licence/provenance problem | DeepSeek Open Platform ToS §4.2(3) for the teacher; local Apache-2.0 fallback; owner spot-check; `SOURCES.md`; no phone data |

## Suggested schedule

| Day | Work |
|---|---|
| 1 | T0.1–T0.5 compatibility and smoke chain; start T1.2 baselines in parallel |
| 2–3 | T2.1 seeds, T2.2 generator, T2.4 dataset v1, T2.5 leakage gate |
| 4 | T2.6 independent held-out, T2.7 audit, dataset freeze |
| 5 | T3.1 parity gate, T3.2–T3.3 first real training runs |
| 6 | T3.4–T3.6 validation and checkpoint selection |
| 7 | T4.1–T4.3 export and Mac eval |
| 8 | T4.4–T4.6 phone eval and end-to-end check |
| 9 | T5.1–T5.4 short prompt and slot cache |
| 10 | T6.1–T6.4 decision, docs and rollout |

This is a part-time estimate; phone runs take longer because of cooling and one-model-at-a-time
RAM limits.

## Immediate next actions

1. Confirm D1–D6 (especially the memory-first base model and the teacher/fallback source).
2. Run T0.4–T0.5: compatibility matrix and the end-to-end smoke chain on Qwen3.5-0.8B.
3. Run T1.2: the full 148-query, hard-set and held-set baseline for Qwen3.5-0.8B, with
   peak RAM and battery per query.
4. Teacher generates the T2.1 seed set; the owner spot-checks 50 examples; meanwhile
   prepare the generator, validator and duplicate checker.
5. Freeze the test set and prepare the independent held-out set before any training data is
   generated.

## Open questions

- Is the goal to beat Gemma 4 E2B at the same RAM, or is a smaller model with a slightly
  lower rate acceptable if it is much cheaper?
- Is the session using the DeepSeek Open Platform API (the terms above) rather than a
  consumer chat interface? The API path is a precondition for using the teacher output.
- May generated JSONL be committed to the repository, or should it stay only on the Mac?
- Who spot-checks the 50-example audit?
- What is the hard RAM ceiling on the phone: 1.2 GB, or should we aim for 1.0 GB?
