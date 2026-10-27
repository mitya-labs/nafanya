#!/bin/sh
# Run the tuned 1.7B model on the phone in 50-query chunks and record RAM/battery.
# Usage: ./phone_eval.sh [model] [tag]
set -eu
cd "$HOME/kuzya"

MODEL=${1:-models/nafanya-1.7b-Q4_K_M.gguf}
TAG=${2:-1.7b-lora}
PORT=8090
BAT=/sys/class/power_supply/qcom-battery

if pgrep -x llama-server >/dev/null; then
  echo "llama-server already running; stop it first" >&2
  exit 1
fi

cap0=$(cat "$BAT/capacity")
temp0=$(cat "$BAT/temp")
cur0=$(cat "$BAT/current_now" 2>/dev/null || echo 0)
echo "start: battery=${cap0}% temp=${temp0} current=${cur0}"

t0=$(date +%s)
./bin/llama-server -m "$MODEL" --jinja \
  --chat-template-kwargs '{"enable_thinking":false}' \
  -c 4096 -t 4 --host 127.0.0.1 --port "$PORT" \
  > "server-$TAG.log" 2>&1 &
pid=$!
trap 'kill $pid 2>/dev/null || true; wait $pid 2>/dev/null || true' EXIT

for _ in $(seq 1 180); do
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break
  kill -0 "$pid" 2>/dev/null || { echo "server died" >&2; exit 1; }
  sleep 1
done
load_s=$(( $(date +%s) - t0 ))
echo "load_seconds=$load_s"

CHUNKS=${CHUNKS:-"0 50 100"}
for start in $CHUNKS; do
  python3 -u eval_gguf_http.py \
    --url "http://127.0.0.1:$PORT/v1/chat/completions" \
    --cases cases-all.json \
    --tools tools-schema-compact2.json \
    --system system-prompt-compact.txt \
    --start "$start" --limit 50 \
    --out "eval-$TAG-chunk-$start.jsonl" \
    > "eval-$TAG-chunk-$start.txt" 2>&1 || true
  cap=$(cat "$BAT/capacity")
  temp=$(cat "$BAT/temp")
  echo "chunk $start: battery=${cap}% temp=${temp}"
  while [ "$temp" -ge 450 ]; do
    sleep 30
    temp=$(cat "$BAT/temp")
    echo "cooling: temp=${temp}"
  done
done

cap1=$(cat "$BAT/capacity")
temp1=$(cat "$BAT/temp")
cur1=$(cat "$BAT/current_now" 2>/dev/null || echo 0)
hwm=$(grep VmHWM "/proc/$pid/status" | awk '{print $2}')
echo "end: battery=${cap1}% temp=${temp1} current=${cur1} peak_kb=${hwm} load_s=${load_s}"
echo "battery_drop=$((cap0 - cap1))"
for f in eval-"$TAG"-chunk-*.txt; do
  echo "--- $f"; tail -2 "$f"
done
