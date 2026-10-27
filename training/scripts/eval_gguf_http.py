#!/usr/bin/env python3
"""Evaluate a running llama-server with a custom system prompt and tool schema."""

import argparse
import json
import urllib.request
from pathlib import Path


def norm(v):
    if isinstance(v, str):
        s = v.strip().rstrip("%")
        if s.endswith(".service"):
            s = s[: -len(".service")]
        try:
            return str(int(s))
        except ValueError:
            return s.lower()
    return str(v)


def args_match(want, got):
    return all(k in got and norm(got[k]) == norm(v) for k, v in want.items())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:18080/v1/chat/completions")
    ap.add_argument("--cases", default="../kuzya/tests/cases-all.json")
    ap.add_argument("--tools", default="training/data/tools-schema-compact2.json")
    ap.add_argument("--system", default="training/data/system-prompt-compact.txt")
    ap.add_argument("--out", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--start", type=int, default=0)
    args = ap.parse_args()

    tools = json.loads(Path(args.tools).read_text())
    system = Path(args.system).read_text().strip()
    cases = json.loads(Path(args.cases).read_text())
    if args.start:
        cases = cases[args.start :]
    if args.limit:
        cases = cases[: args.limit]

    results = []
    for case in cases:
        body = json.dumps(
            {
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": case["q"]},
                ],
                "tools": tools,
                "temperature": 0,
                "max_tokens": 256,
            }
        ).encode()
        req = urllib.request.Request(
            args.url, data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.load(resp)
        msg = data["choices"][0]["message"]
        calls = msg.get("tool_calls") or []
        got_tool = calls[0]["function"]["name"] if calls else None
        got_args = {}
        if calls:
            raw = calls[0]["function"].get("arguments", "{}")
            try:
                got_args = json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError:
                got_args = {}
        want_tool = case["tool"] or None
        tool_ok = got_tool == want_tool
        args_ok = tool_ok and args_match(case.get("args", {}), got_args)
        results.append(
            {
                **case,
                "got_tool": got_tool,
                "got_args": got_args,
                "tool_ok": tool_ok,
                "args_ok": args_ok,
                "reply": (msg.get("content") or "").strip(),
            }
        )
        print(
            f"{'ok  ' if args_ok else 'FAIL'} {case['id']:>3} {case['q'][:50]:<50} "
            f"want {str(case['tool']):<16} got {str(got_tool):<16} {got_args}"
        )

    total = len(results)
    tool_ok = sum(r["tool_ok"] for r in results)
    args_ok = sum(r["args_ok"] for r in results)
    print(
        f"\nTOTAL tool {tool_ok}/{total} ({100*tool_ok/total:.0f}%), "
        f"args {args_ok}/{total} ({100*args_ok/total:.0f}%)"
    )
    if args.out:
        with open(args.out, "w") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
