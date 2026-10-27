#!/usr/bin/env python3
"""Validate a seed/dataset JSONL and check leakage against Kuzya tests."""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KUZYA = ROOT.parent / "kuzya"
TOOLS = json.loads((ROOT / "data" / "tools-schema.json").read_text())
SCHEMA = {t["function"]["name"]: t["function"] for t in TOOLS}
ALLOWED_UNITS = {
    "NetworkManager",
    "bluetooth",
    "ModemManager",
    "avahi-daemon",
    "systemd-resolved",
    "systemd-timesyncd",
    "power-profiles-daemon",
}
CATEGORIES = {
    "direct",
    "slang",
    "typo",
    "english",
    "indirect",
    "numbers_in_words",
    "near_miss_negative",
    "out_of_scope",
}


def norm(text: str) -> str:
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def tokens(text: str) -> set[str]:
    return set(norm(text).split())


def jaccard(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta and not tb:
        return 1.0
    return len(ta & tb) / len(ta | tb)


def lev(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def norm_dist(a: str, b: str) -> float:
    m = max(len(a), len(b))
    return 0.0 if m == 0 else lev(a, b) / m


def check_args(tool: str, args: dict) -> list[str]:
    errs = []
    fn = SCHEMA[tool]
    props = fn["parameters"].get("properties", {})
    required = fn["parameters"].get("required", [])
    for key in required:
        if key not in args:
            errs.append(f"missing required arg {key}")
    for key, value in args.items():
        if key not in props:
            errs.append(f"unknown arg {key}")
            continue
        typ = props[key].get("type")
        if typ == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            errs.append(f"{key} must be integer")
        if typ == "string" and not isinstance(value, str):
            errs.append(f"{key} must be string")
        enum = props[key].get("enum")
        if enum and value not in enum:
            errs.append(f"{key} must be one of {enum}")
    if "percent" in args and isinstance(args["percent"], int):
        lo, hi = (5, 100) if tool == "brightness_set" else (0, 100)
        if not lo <= args["percent"] <= hi:
            errs.append(f"percent out of range {lo}..{hi}")
    if "unit" in args and args["unit"] not in ALLOWED_UNITS:
        errs.append(f"unit not in allowlist: {args['unit']}")
    if "connection" in args and not re.fullmatch(r"[A-Za-z0-9_.@+-]{1,64}", args["connection"]):
        errs.append(f"bad connection name: {args['connection']}")
    return errs


def load_tests() -> list[tuple[str, str]]:
    out = []
    for path in sorted((KUZYA / "tests").glob("cases*.json")):
        for item in json.loads(path.read_text()):
            out.append((path.name, item["q"]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=str(ROOT / "data" / "seeds-teacher-v0.jsonl"))
    ap.add_argument("--near", type=float, default=0.7, help="Jaccard threshold for warnings")
    args = ap.parse_args()

    rows = []
    with open(args.path) as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"line {line_no}: invalid JSON: {e}")
                sys.exit(1)
            item["_line"] = line_no
            rows.append(item)

    errors = []
    ids = set()
    for item in rows:
        tag = f"line {item['_line']} id {item.get('id')}"
        for key in ("id", "q", "tool", "args", "category", "split", "source", "terms"):
            if key not in item:
                errors.append(f"{tag}: missing {key}")
        if item.get("id") in ids:
            errors.append(f"{tag}: duplicate id")
        ids.add(item.get("id"))
        if item.get("category") not in CATEGORIES:
            errors.append(f"{tag}: bad category {item.get('category')}")
        tool = item.get("tool")
        if tool is None:
            if item.get("args"):
                errors.append(f"{tag}: negative must have empty args")
        elif tool not in SCHEMA:
            errors.append(f"{tag}: unknown tool {tool}")
        else:
            errors.extend(f"{tag}: {e}" for e in check_args(tool, item.get("args") or {}))

    tests = load_tests()
    exact = []
    near = []
    for item in rows:
        for test_file, q in tests:
            if norm(item["q"]) == norm(q):
                exact.append((item["id"], test_file, q))
            j = jaccard(item["q"], q)
            if args.near <= j < 1.0:
                near.append((j, item["id"], test_file, q))
    near.sort(reverse=True)

    print(f"rows: {len(rows)}")
    print("by tool:", dict(Counter(item.get("tool") for item in rows)))
    print("by category:", dict(Counter(item.get("category") for item in rows)))
    neg = sum(1 for item in rows if item.get("tool") is None)
    print(f"negatives: {neg}/{len(rows)} ({100*neg/len(rows):.0f}%)")
    if exact:
        print("\nEXACT duplicates against tests:")
        for row in exact:
            print(" ", row)
    if near:
        print(f"\nNear duplicates (Jaccard >= {args.near}), top 10:")
        for j, item_id, test_file, q in near[:10]:
            print(f"  {j:.2f}  {item_id}  vs {test_file}: {q}")
    if errors:
        print("\nERRORS:")
        for e in errors:
            print(" ", e)
    if errors or exact:
        sys.exit(1)
    print("\nOK")


if __name__ == "__main__":
    main()
