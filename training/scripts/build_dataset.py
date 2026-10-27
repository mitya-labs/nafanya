#!/usr/bin/env python3
"""Turn labelled seeds into mlx-lm chat JSONL with tools and a stratified split."""

import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

REFUSALS = [
    "Так не умею.",
    "Этого я не умею.",
    "Не могу: такого инструмента у меня нет.",
    "Это не входит в мои возможности.",
    "Прости, я умею только управлять телефоном.",
]


def example(seed: dict, refusal: str, tools: list, system: str) -> dict:
    tool = seed["tool"]
    if tool is None:
        assistant = {"role": "assistant", "content": refusal}
    else:
        assistant = {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": tool, "arguments": seed["args"]}}],
        }
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": seed["q"]},
            assistant,
        ],
        "tools": tools,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default=str(DATA / "seeds-teacher-v0.jsonl"))
    ap.add_argument("--out", default=str(DATA / "pilot"))
    ap.add_argument("--tools", default=str(DATA / "tools-schema.json"))
    ap.add_argument("--system", default=str(DATA / "system-prompt.txt"))
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    tools = json.loads(Path(args.tools).read_text())
    system = Path(args.system).read_text().strip()
    seeds = [json.loads(line) for line in open(args.seeds) if line.strip()]
    groups: dict[str, list[dict]] = {}
    for seed in seeds:
        groups.setdefault(seed["tool"] or "NEGATIVE", []).append(seed)

    rng = random.Random(args.seed)
    train, valid, test = [], [], []
    for gi, key in enumerate(sorted(groups)):
        items = groups[key][:]
        rng.shuffle(items)
        n = len(items)
        n_train = max(1, round(0.7 * n))
        for i, seed in enumerate(items):
            if i < n_train:
                train.append(seed)
            elif (i - n_train + gi) % 2 == 0:
                valid.append(seed)
            else:
                test.append(seed)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, items in (("train", train), ("valid", valid), ("test", test)):
        with (out / f"{name}.jsonl").open("w") as f:
            for i, seed in enumerate(items):
                refusal = REFUSALS[int(seed["id"].split("-")[-1]) % len(REFUSALS)]
                f.write(json.dumps(example(seed, refusal, tools, system), ensure_ascii=False) + "\n")
        print(f"{out / f'{name}.jsonl'}: {len(items)}")


if __name__ == "__main__":
    main()
