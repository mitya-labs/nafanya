# Rules for agents — nafanya

Inherits the rules in `../kuzya/AGENTS.md` and `../skladenos/AGENTS.md`.

- Announce every job before running it: `[~N min/sec, HH:MM] what I am doing`; for jobs
  longer than a minute add `→ ~HH:MM`. If a job runs late, report it and give a new
  estimate.
- Keep status in `SUMMARY.md`, logs in `logs/`, and use background execution for long
  blocking commands.
- Write new documentation in English. Do not delete or force-translate existing Russian
  text.
- Phone access and the `nosleep` workflow are described in `../kuzya/LOCAL.md` and
  `../kuzya/AGENTS.md`. Enable `phone-nosleep on` before phone work and turn it off
  afterwards.

## nafanya specifics

- Scope: model data, distillation, training, export and evaluation. Agent code, tools,
  prompts and tests stay in `../kuzya`.
- Do not change `../kuzya` from here unless the task explicitly asks for it. If a tool or
  prompt there changes, run its `tests/` and record the correct-call rate in
  `../kuzya/SUMMARY.md`.
- Never commit API keys, phone data, model weights, adapters or generated datasets whose
  licence is unclear. Keep secrets in environment variables.
- Record data provenance and terms in `training/data/SOURCES.md`.
- Freeze `../kuzya/tests/cases*.json` before generating training data; the leakage check
  must fail on any overlap.
- The model must never get a shell. New agent tools are still added only in
  `../kuzya/internal/tools/` and marked `Dangerous: true` when they change the system.
