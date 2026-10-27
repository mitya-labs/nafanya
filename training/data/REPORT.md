# Data report — pilot v0

Date: 2026-10-27.

## Seeds

- File: `seeds-teacher-v0.jsonl`
- Rows: 60
- Positives: 40, negatives: 20 (33%)
- Coverage: 3 examples per tool (4 for `nosleep_set`), 20 negatives
- Categories: direct 18, indirect 13, slang 2, English 3, numbers in words 3, typo 1,
  out-of-scope 12, near-miss 8
- Duplicate/leakage check against `../kuzya/tests/cases*.json`: no exact duplicates;
  no Jaccard ≥ 0.7 warnings in the first run.
- SHA256: `2360eee4e8ce38062d934adeeb7d035608718f8b61ce8014621712afc4680c92`

## Pilot split

- Train: 41
- Valid: 9
- Test: 10
- Built by `training/scripts/build_dataset.py` (seed 42, stratified by tool, 70/15/15).

The pilot is for pipeline validation, not for a final accuracy decision: the seed set is
too small and the teacher phrases may be close to the test themes.

## Dataset v1

- File: `seeds-all-v1.jsonl`
- Rows: 433 unique (60 seeds + 40 targeted seeds + 337 teacher paraphrases)
- Negatives: 121 (28%); target is 35–40%, so more near-miss negatives are needed
- Per tool: 21–29 examples; `nosleep_set` 28, `volume_set`/`volume_step`/`brightness_set`/`brightness_step` 29
- Longest training example: 931 tokens with the compact prompt; fits `max_seq_length` 1024
- Split: 305 train / 64 valid / 64 test (stratified by tool, seed 42)
- SHA256 seeds: `01dc1e6b76b0e280077f0553c79c3aeffe9716125484ed2dfa90429a25368046`
- SHA256 paraphrases: `3e2396b4845f0c0b1346b71592b6a96305116ef4a6e196ccfdf7d14fcdc96a81`
- Leakage check against `../kuzya/tests/cases*.json`: no exact duplicates; no Jaccard ≥ 0.7 warnings in the validator run.

## Dataset v2

- 567 unique rows: v1 + 159 teacher-generated hard negatives (255 negatives, 45%).
- Compact prompt with one-line descriptions: 1118 tokens, max training example 1160.

## Dataset v3

- 625 unique rows: v2 + 40 manual hard negatives + 24 targeted relative-volume/brightness
  seeds (290 negatives, 46%).
- Longest example: 1244 tokens; max_seq_length 1280.
- The extra negatives cover Wi-Fi on/off, stopping services, ssh/sshd, disk/memory,
  timer, flashlight, browser, calls, translation, calculations and phone power.
- The extra positives target `volume_step`/`brightness_step` vs absolute
  `volume_set`/`brightness_set`.

## Pilot results

Evaluated on `../kuzya/tests/cases-subset.json` (26 queries), temperature 0,
`enable_thinking=False`:

| Configuration | Correct tool | With args |
|---|---|---|
| BF16 base + full prompt (1639 tokens) | 11/26 (42%) | 11/26 (42%) |
| BF16 base + compact prompt (889 tokens, no tool descriptions) | 7/26 (27%) | 7/26 (27%) |
| BF16 LoRA pilot + compact prompt | **16/26 (62%)** | 15/26 (58%) |

The pilot improves the compact prompt by 9 cases over the base with the same prompt and
by 5 cases over the base with the full prompt. It still confuses `volume_step` vs
`brightness_step`, `brightness_set` vs `brightness_step`, and some negatives; the seed
set is too small. MLX 4-bit Qwen3.5 was also tested and collapses quality (it refuses a
battery query that BF16 answers with a tool call), so it is not used.

## Known gaps

- Only one typo example and two slang examples; the real set needs many more.
- The negatives are mostly clear near-misses; add more compound and ambiguous requests.
- No multi-turn examples yet (tool result → final answer).
- The pilot test split is not an independent held-out set; use
  `../kuzya/tests/cases-all.json` for external evaluation.
