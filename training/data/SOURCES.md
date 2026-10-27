# Data sources and terms

## Teacher (primary)

- Model: DeepSeek V4.1 Flash, provider `deepseek`, used through the Open Platform API.
- Terms: **DeepSeek Open Platform Terms of Service**, release 2026-04-22, effective
  2026-04-29, retrieved 2026-10-27.
- Relevant clause: §4.2(3) — Inputs and Outputs may be used for a wide range of cases,
  including "training other models (such as model distillation)", subject to applicable
  law and the Terms.
- Conditions we follow:
  - API only; never script the web chat or extract data with robots/spiders.
  - API key only in an environment variable; never in git.
  - No private data from the phone; only synthetic tool-selection phrasings.
  - Record the terms revision next to every data file.
  - If the dataset is published, state that it is AI-generated; do not use the DeepSeek
    name or logo in a way that implies partnership.
- The general DeepSeek Terms of Use (last update 2026-03-27) also applies; §3.1 requires
  accuracy checks and an AI-generated label when Outputs are published.

## Teacher (fallback)

- Qwen3, Apache-2.0, run locally on the Mac. Verify the exact model card licence before
  bulk generation and record the repository and revision.

## Other sources

- Text written by other providers (for example Claude) is not used as training data
  without checking that provider's terms.
- No text from the phone, no logs, no personal data.

## Files

| File | Source | Terms | SHA256 |
|---|---|---|---|
| `seeds-teacher-v0.jsonl` | DeepSeek V4.1 Flash, API | DeepSeek Open Platform ToS 2026-04-22 §4.2(3) | `2360eee4e8ce38062d934adeeb7d035608718f8b61ce8014621712afc4680c92` |
| `heldout-40.json` | DeepSeek V4.1 Flash (written directly, not generated), 2026-10-27 | DeepSeek Open Platform ToS 2026-04-22 §4.2(3) | `68009fc7b4740a1f2e4ffc55f376df929739f4b17e67d44961380da27ab6859d` |

`heldout-40.json` is an evaluation-only set: 40 fresh phrasings (28 positives, 12
negatives), never used for training. A normalized-text check found no exact duplicate
against `../kuzya/tests/cases*.json` or any `seeds-*.jsonl`; the highest token Jaccard
similarity is 0.83 (a negative paraphrase).

Add a row for every generated dataset, including the generator version and the date.
