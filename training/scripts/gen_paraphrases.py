#!/usr/bin/env python3
"""Generate paraphrases for Kuzya seeds with the teacher model via `opencode run`.

The teacher sees one seed and its exact label and returns strict JSONL. Every row is
validated against the seed label and the tool schema before it is written.
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SCHEMA = {t["function"]["name"]: t["function"] for t in json.loads((DATA / "tools-schema.json").read_text())}
CATEGORIES = {
    "direct", "slang", "typo", "english", "indirect", "numbers_in_words",
    "near_miss_negative", "out_of_scope",
}
TERMS = "DeepSeek Open Platform ToS 2026-04-22 §4.2(3)"


def norm_args(args):
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return None
    if not isinstance(args, dict):
        return None
    return args


def prompt_for(seed: dict, n: int) -> str:
    tool = seed["tool"]
    if tool is None:
        label = "инструмент не нужен, ответить текстом"
        extra = ("Сделай negatives: часть — явно вне возможностей (погода, файлы, звонки), "
                 "часть — близкие к инструментам, но не поддерживаемые (включить Wi-Fi, "
                 "остановить службу, sshd, bluetooth, фонарик).")
    else:
        label = f"tool={tool}, args={json.dumps(seed['args'], ensure_ascii=False)}"
        extra = ("Сохрани ровно тот же инструмент и те же аргументы. Меняй только формулировку. "
                 "Разнообразь: сленг, опечатки, числа словами, косвенная просьба, английский.")
    return f"""Ты генерируешь данные для обучения русского офлайн-агента Кузи.
Доступные инструменты: {json.dumps(SCHEMA, ensure_ascii=False)}
Исходная фраза: {json.dumps(seed['q'], ensure_ascii=False)}
Правильная метка: {label}
Сгенерируй {n} новых фраз с тем же смыслом. {extra}
Не копируй известные тестовые запросы и не повторяй исходную фразу.
Верни только JSONL, по одному объекту на строку, поля q, tool, args, category.
category: direct, slang, typo, english, indirect, numbers_in_words, near_miss_negative, out_of_scope.
Без markdown, без пояснений, без пустых строк."""


def run_teacher(prompt: str, model: str) -> str:
    proc = subprocess.run(
        ["opencode", "run", "--format", "json", "--model", model, prompt],
        capture_output=True, text=True, timeout=240,
    )
    texts = []
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "text":
            texts.append(event.get("part", {}).get("text", ""))
    text = "".join(texts)
    # tolerate fences and leading prose
    text = re.sub(r"```(?:jsonl?)?", "", text)
    return text


def parse_rows(text: str):
    rows = []
    for line in text.splitlines():
        line = line.strip().rstrip(",")
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows.append(row)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default=str(DATA / "seeds-teacher-v0.jsonl"))
    ap.add_argument("--out", default=str(DATA / "generated" / "paraphrases-v1.jsonl"))
    ap.add_argument("--per-seed", type=int, default=6)
    ap.add_argument("--model", default="deepseek/deepseek-flash")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=1.0)
    args = ap.parse_args()

    seeds = [json.loads(line) for line in open(args.seeds) if line.strip()]
    if args.start:
        seeds = seeds[args.start :]
    if args.limit:
        seeds = seeds[: args.limit]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if out.exists():
        for line in open(out):
            try:
                seen.add(json.loads(line)["q"].strip().lower())
            except Exception:
                pass

    kept = 0
    for idx, seed in enumerate(seeds, 1):
        try:
            text = run_teacher(prompt_for(seed, args.per_seed), args.model)
            rows = parse_rows(text)
        except Exception as e:
            print(f"[{idx}/{len(seeds)}] {seed['id']}: teacher error: {e}", file=sys.stderr)
            continue

        added = 0
        for row in rows:
            q = str(row.get("q", "")).strip()
            tool = row.get("tool")
            got_args = norm_args(row.get("args", {}))
            category = row.get("category", "direct")
            if not q or got_args is None:
                continue
            if tool != seed["tool"]:
                continue
            if seed["tool"] is None:
                if got_args:
                    continue
            elif got_args != seed["args"]:
                continue
            if category not in CATEGORIES:
                category = "direct"
            key = q.lower()
            if key in seen:
                continue
            seen.add(key)
            row = {
                "id": f"pp-{seed['id']}-{added + 1:02d}",
                "q": q,
                "tool": tool,
                "args": got_args,
                "category": category,
                "split": "train",
                "source": f"{args.model}-via-opencode",
                "terms": TERMS,
            }
            with out.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            added += 1
            kept += 1

        print(f"[{idx}/{len(seeds)}] {seed['id']}: +{added}")
        time.sleep(args.sleep)

    print(f"kept {kept} rows in {out}")


if __name__ == "__main__":
    main()
