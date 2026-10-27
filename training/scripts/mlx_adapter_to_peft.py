#!/usr/bin/env python3
"""Convert an MLX LoRA adapter to PEFT layout for llama.cpp.

MLX stores A as [in, rank] and B as [rank, out]; PEFT stores
A as [rank, in] and B as [out, rank]. The LoRA scale is converted to
PEFT's alpha: alpha = scale * rank.
"""

import argparse
import json
from pathlib import Path

import mlx.core as mx

TARGETS = [
    "self_attn.q_proj",
    "self_attn.v_proj",
    "mlp.gate_proj",
    "mlp.up_proj",
    "mlp.down_proj",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-name", default="Qwen/Qwen3.5-0.8B")
    ap.add_argument("--rank", type=int, default=0)
    ap.add_argument("--scale", type=float, default=0.0)
    args = ap.parse_args()

    adapter_dir = Path(args.adapter)
    cfg = json.loads((adapter_dir / "adapter_config.json").read_text())
    lora = cfg.get("lora_parameters", {})
    rank = args.rank or int(lora.get("rank", 8))
    scale = args.scale or float(lora.get("scale", 16.0))
    targets = lora.get("keys") or TARGETS

    src = mx.load(str(adapter_dir / "adapters.safetensors"))
    out = {}
    for key, value in src.items():
        if key.endswith(".lora_a"):
            base = key[: -len(".lora_a")]
            out["base_model.model." + base + ".lora_A.weight"] = value.T
        elif key.endswith(".lora_b"):
            base = key[: -len(".lora_b")]
            out["base_model.model." + base + ".lora_B.weight"] = value.T
        else:
            raise ValueError(f"unexpected adapter key: {key}")

    dst = Path(args.out)
    dst.mkdir(parents=True, exist_ok=True)
    mx.save_safetensors(str(dst / "adapter_model.safetensors"), out)
    config = {
        "peft_type": "LORA",
        "task_type": "CAUSAL_LM",
        "base_model_name_or_path": args.base_name,
        "r": rank,
        "lora_alpha": int(scale * rank),
        "lora_dropout": 0.05,
        "bias": "none",
        "fan_in_fan_out": False,
        "target_modules": targets,
        "inference_mode": True,
    }
    (dst / "adapter_config.json").write_text(json.dumps(config, indent=2) + "\n")
    print(f"wrote {len(out)} tensors to {dst}")


if __name__ == "__main__":
    main()
