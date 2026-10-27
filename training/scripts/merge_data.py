#!/usr/bin/env python3
"""Merge seed and paraphrase files, deduplicate by normalised query, keep seeds first."""

import argparse
import json
import re
from pathlib import Path


def norm(text: str) -> str:
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="training/data/seeds-all-v1.jsonl")
    ap.add_argument("files", nargs="+")
    args = ap.parse_args()

    seen = set()
    ids = set()
    rows = []
    for path in args.files:
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            key = norm(row["q"])
            if key in seen:
                continue
            seen.add(key)
            rid = row["id"]
            if rid in ids:
                n = 2
                while f"{rid}-{n}" in ids:
                    n += 1
                row["id"] = f"{rid}-{n}"
            ids.add(row["id"])
            rows.append(row)

    with open(args.out, "w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} unique rows to {args.out}")


if __name__ == "__main__":
    main()
