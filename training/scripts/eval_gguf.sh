#!/bin/sh
# Evaluate a GGUF model on the Mac with the same Go runner as the phone.
# Usage: ./eval_gguf.sh <model.gguf> [cases.json] [tag]
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODEL=${1:?usage: eval_gguf.sh <model.gguf> [cases.json] [tag]}
CASES=${2:-$ROOT/../kuzya/tests/cases-subset.json}
TAG=${3:-$(basename "$MODEL" .gguf)}
PORT=${PORT:-18080}
SERVER=$ROOT/training/vendor/llama.cpp-6050b46/build-mac/bin/llama-server

"$SERVER" -m "$MODEL" --jinja \
  --chat-template-kwargs '{"enable_thinking":false}' \
  -c 4096 -t 4 -ngl 99 --host 127.0.0.1 --port "$PORT" \
  > "$ROOT/logs/server-$TAG.log" 2>&1 &
pid=$!
trap 'kill $pid 2>/dev/null || true; wait $pid 2>/dev/null || true' EXIT

for i in $(seq 1 120); do
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break
  sleep 1
done

KUZYA_URL="http://127.0.0.1:$PORT/v1/chat/completions" \
  "$ROOT/training/bin/kuzya-eval" -cases "$CASES" -out "$ROOT/logs/eval-$TAG.jsonl" \
  > "$ROOT/logs/eval-$TAG.txt" 2>&1 || true

tail -40 "$ROOT/logs/eval-$TAG.txt"
