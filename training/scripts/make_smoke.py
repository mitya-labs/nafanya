#!/usr/bin/env python3
"""Build a tiny tool-calling smoke dataset in the mlx-lm chat format.

It uses the real system prompt and the real tool schemas exported from ../kuzya,
so the smoke run checks the same chat template that the agent uses.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

TOOLS = json.loads((DATA / "tools-schema.json").read_text())
SYSTEM = (DATA / "system-prompt.txt").read_text().strip()

# 16 positives, one or two per tool, and 4 negatives.
CASES = [
    ("покажи уровень батареи", "battery_status", {}),
    ("сколько заряда осталось до вечера?", "battery_status", {}),
    ("к какому вайфаю подключён телефон?", "wifi_status", {}),
    ("подключи телефон к сети Home_5G", "wifi_connect", {"connection": "Home_5G"}),
    ("что сейчас запущено в системе?", "services_running", {}),
    ("покажи журнал bluetooth", "service_logs", {"unit": "bluetooth"}),
    ("что пишет NetworkManager, последние 20 строк", "service_logs",
     {"unit": "NetworkManager", "lines": 20}),
    ("перезапусти bluetooth", "service_restart", {"unit": "bluetooth"}),
    ("не давай телефону засыпать", "nosleep_set", {"mode": "on"}),
    ("разреши телефону спать", "nosleep_set", {"mode": "off"}),
    ("какая сейчас громкость?", "volume_get", {}),
    ("поставь громкость 35", "volume_set", {"percent": 35}),
    ("сделай звук тише", "volume_step", {"direction": "down"}),
    ("заглуши звук", "mute_set", {"mode": "on"}),
    ("поставь яркость 40", "brightness_set", {"percent": 40}),
    ("сделай экран ярче", "brightness_step", {"direction": "up"}),
    ("какая завтра погода?", None, None),
    ("поставь таймер на пять минут", None, None),
    ("перезапусти sshd", None, None),
    ("включи bluetooth", None, None),
]


def example(q: str, tool: str | None, args: dict | None) -> dict:
    assistant = {"role": "assistant", "content": ""}
    if tool is None:
        assistant["content"] = "Так не умею."
    else:
        assistant["tool_calls"] = [
            {"function": {"name": tool, "arguments": args or {}}}
        ]
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": q},
            assistant,
        ],
        "tools": TOOLS,
    }


def main() -> None:
    out = DATA / "smoke"
    out.mkdir(parents=True, exist_ok=True)
    rows = [example(*c) for c in CASES]
    splits = {"train": rows[:14], "valid": rows[14:17], "test": rows[17:]}
    for name, items in splits.items():
        path = out / f"{name}.jsonl"
        with path.open("w") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"{path}: {len(items)} examples")


if __name__ == "__main__":
    main()
