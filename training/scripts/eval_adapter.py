#!/usr/bin/env python3
"""Evaluate an MLX LoRA adapter on Kuzya cases without exporting to GGUF."""

import argparse
import json
import re
import sys
from pathlib import Path

from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

FUNC_RE = re.compile(r"<function=([^>\s]+)>")
PARAM_RE = re.compile(r"<parameter=([^>\s]+)>\s*(.*?)\s*</parameter>", re.S)
JSON_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)


def parse_tool_call(text: str):
    m = FUNC_RE.search(text)
    if m:
        name = m.group(1)
        args = {}
        for key, raw in PARAM_RE.findall(text[m.end() :]):
            raw = raw.strip()
            try:
                args[key] = json.loads(raw)
            except json.JSONDecodeError:
                args[key] = raw
        return name, args
    for raw in JSON_CALL_RE.findall(text):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        fn = obj.get("function", obj)
        name = fn.get("name")
        args = fn.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                continue
        if name:
            return name, args
    return None, {}


def norm(v):
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, str):
        s = v.strip().rstrip("%")
        if s.endswith(".service"):
            s = s[: -len(".service")]
        try:
            return str(int(s))
        except ValueError:
            return s.lower()
    return str(v)


def args_match(want: dict, got: dict) -> bool:
    for key, value in want.items():
        if key not in got:
            return False
        if norm(got[key]) != norm(value):
            return False
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="training/models/Qwen3.5-0.8B-4bit")
    ap.add_argument("--adapter", default="")
    ap.add_argument("--cases", default="../kuzya/tests/cases-subset.json")
    ap.add_argument("--tools", default=str(DATA / "tools-schema.json"))
    ap.add_argument("--system", default=str(DATA / "system-prompt.txt"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="")
    ap.add_argument("--max-tokens", type=int, default=256)
    args = ap.parse_args()

    cases = json.loads(Path(args.cases).read_text())
    tools = json.loads(Path(args.tools).read_text())
    system = Path(args.system).read_text().strip()
    if args.limit:
        cases = cases[: args.limit]

    model, tokenizer = load(args.model, adapter_path=args.adapter or None)
    sampler = make_sampler(temp=0.0)
    results = []
    for case in cases:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": case["q"]},
        ]
        prompt = tokenizer.apply_chat_template(
            messages,
            tools=tools,
            add_generation_prompt=True,
            enable_thinking=False,
            tokenize=False,
        )
        reply = generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=args.max_tokens,
            sampler=sampler,
            verbose=False,
        )
        got_tool, got_args = parse_tool_call(reply)
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
                "reply": reply.strip(),
            }
        )
        mark = "ok  " if args_ok else "FAIL"
        print(
            f"{mark} {case['id']:>3} {case['q'][:52]:<52} "
            f"want {str(case['tool']):<16} got {str(got_tool):<16} {got_args}"
        )

    total = len(results)
    tool_ok = sum(r["tool_ok"] for r in results)
    args_ok = sum(r["args_ok"] for r in results)
    print(f"\nTOTAL tool {tool_ok}/{total} ({100*tool_ok/total:.0f}%), "
          f"args {args_ok}/{total} ({100*args_ok/total:.0f}%)")
    if args.out:
        with open(args.out, "w") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
