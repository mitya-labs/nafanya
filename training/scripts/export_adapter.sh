#!/bin/sh
# Export an MLX QLoRA adapter to a merged, quantized GGUF for the phone.
# Usage: ./export_adapter.sh <adapter-dir> <run-name> [base-gguf] [base-model-dir]
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ADAPTER=${1:?usage: export_adapter.sh <adapter-dir> <run-name> [base-gguf]}
NAME=${2:?usage: export_adapter.sh <adapter-dir> <run-name> [base-gguf]}
BASE_GGUF=${3:-$ROOT/../kuzya/models/Qwen3.5-0.8B-Q4_K_M.gguf}
BASE_MODEL=${4:-$ROOT/training/models/Qwen3.5-0.8B}
LLAMA=$ROOT/training/vendor/llama.cpp-6050b46
OUT=$ROOT/training/runs/$NAME

mkdir -p "$OUT"
echo "==> MLX adapter -> PEFT"
$ROOT/training/.venv/bin/python "$ROOT/training/scripts/mlx_adapter_to_peft.py" \
  --adapter "$ADAPTER" --out "$OUT/peft"

echo "==> PEFT -> GGUF LoRA"
$ROOT/training/.venv-convert/bin/python "$LLAMA/convert_lora_to_gguf.py" \
  --base "$BASE_MODEL" --outfile "$OUT/lora.gguf" --outtype f16 "$OUT/peft"

echo "==> merge LoRA into base GGUF"
"$LLAMA/build-mac/bin/llama-export-lora" \
  -m "$BASE_GGUF" -o "$OUT/merged.gguf" --lora "$OUT/lora.gguf"

# The base is already Q4_K_M; llama-export-lora preserves its tensor types.
echo "==> final model"
cp "$OUT/merged.gguf" "$OUT/model.gguf"

ls -lh "$OUT/lora.gguf" "$OUT/merged.gguf" "$OUT/model.gguf"
