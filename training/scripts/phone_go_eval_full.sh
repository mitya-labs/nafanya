#!/bin/sh
# Run the real kuzya-eval binary against a model and record load time, peak RAM, battery.
# Usage: ./phone_go_eval.sh [model] [tag]
set -eu
cd "$HOME/kuzya"

MODEL=${1:-models/nafanya-1.7b-Q4_K_M.gguf}
TAG=${2:-go-eval}
BAT=/sys/class/power_supply/qcom-battery

if pgrep -x llama-server >/dev/null; then
  echo "llama-server already running; stop it first" >&2
  exit 1
fi

cap0=$(cat "$BAT/capacity")
temp0=$(cat "$BAT/temp")
t0=$(date +%s)
./bin/llama-server -m "$MODEL" --jinja \
  --chat-template-kwargs '{"enable_thinking":false}' \
  -c 4096 -t 4 --host 127.0.0.1 --port 8080 \
  > "server-$TAG.log" 2>&1 &
pid=$!
trap 'kill $pid 2>/dev/null || true; wait $pid 2>/dev/null || true' EXIT

for _ in $(seq 1 180); do
  curl -sf http://127.0.0.1:8080/health >/dev/null && break
  kill -0 "$pid" 2>/dev/null || { echo "server died" >&2; exit 1; }
  sleep 1
done
echo "load_seconds=$(( $(date +%s) - t0 ))"

./bin/kuzya-eval --full -cases cases-all.json -out "eval-$TAG.jsonl" > "eval-$TAG.txt" 2>&1 || true

hwm=$(grep VmHWM "/proc/$pid/status" | awk '{print $2}')
echo "peak_kb=$hwm"
echo "battery=${cap0}%->$(cat "$BAT/capacity")% temp=${temp0}->$(cat "$BAT/temp")"
tail -8 "eval-$TAG.txt"
