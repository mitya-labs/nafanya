#!/usr/bin/env python3
"""Convert a fused MLX Qwen3.5 checkpoint into HF text-model layout.

MLX-LM saves Qwen3.5 text weights as ``language_model.model.*``; the HF
checkpoint and llama.cpp's converter expect ``model.language_model.*``.
The fused config also carries ``Qwen3_5ForConditionalGeneration`` and a vision
section; for text-only GGUF conversion we switch it to ``Qwen3_5ForCausalLM``
and drop the vision config.
"""

import argparse
import json
import shutil
from pathlib import Path

import mlx.core as mx

COPY_FILES = [
    "tokenizer.json",
    "tokenizer_config.json",
    "merges.txt",
    "vocab.json",
    "chat_template.jinja",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fused", required=True, help="fused MLX model directory")
    ap.add_argument("--base", required=True, help="original HF model directory")
    ap.add_argument("--out", required=True, help="output HF text-model directory")
    args = ap.parse_args()

    fused = Path(args.fused)
    base = Path(args.base)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    weights = mx.load(str(fused / "model.safetensors"))
    renamed = {}
    for key, value in weights.items():
        if key.startswith("language_model.model."):
            key = "model.language_model." + key[len("language_model.model.") :]
        elif key.startswith("language_model."):
            key = "model." + key[len("language_model.") :]
        renamed[key] = value
    mx.save_safetensors(str(out / "model.safetensors"), renamed)

    config = json.loads((base / "config.json").read_text())
    config["architectures"] = ["Qwen3_5ForCausalLM"]
    config.pop("vision_config", None)
    (out / "config.json").write_text(json.dumps(config, indent=2) + "\n")

    for name in COPY_FILES:
        src = base / name
        if src.exists():
            shutil.copy2(src, out / name)

    print(f"wrote {len(renamed)} tensors to {out}")


if __name__ == "__main__":
    main()
