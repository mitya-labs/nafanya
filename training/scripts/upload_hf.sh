#!/bin/sh
# Upload a nafanya model (adapter + GGUF + card) to Hugging Face.
# Usage: ./upload_hf.sh 1.7b|0.8b <user>/<repo> [--public]
# Needs: pip install -U huggingface_hub && hf auth login
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
KIND=${1:?usage: upload_hf.sh 1.7b|0.8b <user>/<repo> [--public]}
REPO=${2:?usage: upload_hf.sh 1.7b|0.8b <user>/<repo> [--public]}
VIS=${3:-private}

case "$KIND" in
	1.7b)
		SRC="$ROOT/training/runs/pilot-1.7b"
		GGUF="$SRC/model-Q4_K_M.gguf"
		CARD="$ROOT/training/hf/README-1.7b.md"
		;;
	0.8b)
		SRC="$ROOT/training/runs/nafanya-0.8b-v8"
		GGUF="$SRC/model.gguf"
		CARD="$ROOT/training/hf/README-0.8b.md"
		;;
	*) echo "неизвестная модель: $KIND (ждали 1.7b или 0.8b)" >&2; exit 2 ;;
esac

[ -f "$SRC/peft/adapter_model.safetensors" ] || { echo "нет адаптера: $SRC/peft" >&2; exit 1; }
[ -f "$GGUF" ] || { echo "нет GGUF: $GGUF" >&2; exit 1; }

if command -v hf >/dev/null 2>&1; then
	CLI=hf
elif command -v huggingface-cli >/dev/null 2>&1; then
	CLI=huggingface-cli
else
	echo "нет hf/huggingface-cli. Установи: python3 -m pip install -U huggingface_hub && hf auth login" >&2
	exit 1
fi

STAGE="$ROOT/training/.hf-stage/$KIND"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp "$SRC/peft/adapter_model.safetensors" "$STAGE/"
cp "$SRC/peft/adapter_config.json" "$STAGE/"
cp "$GGUF" "$STAGE/model-Q4_K_M.gguf"
cp "$CARD" "$STAGE/README.md"
cp "$ROOT/training/hf/LICENSE" "$STAGE/"
du -sh "$STAGE"

PRIVATE=--private
[ "$VIS" = "--public" ] && PRIVATE=--public
"$CLI" repo create "$REPO" --repo-type model "$PRIVATE" -y 2>/dev/null || true
"$CLI" upload "$REPO" "$STAGE" --repo-type model

echo "готово: https://huggingface.co/$REPO"
