#!/bin/sh
# Measure energy per query by integrating current_now * voltage_now on the phone.
# Usage: ./phone_energy_eval.sh [model] [tag] [cases]
# The battery driver reports current_now in uA and voltage_now in uV, so
# uV * uA = pW; one sample per second, so J = sum(pW) / 1e12.
set -eu
cd "$HOME/kuzya"

MODEL=${1:-models/nafanya-1.7b-Q4_K_M.gguf}
TAG=${2:-energy}
CASES=${3:-cases30.json}
BAT=/sys/class/power_supply/qcom-battery
CSV="$TAG.csv"

if pgrep -x llama-server >/dev/null; then
  echo "llama-server already running; stop it first" >&2
  exit 1
fi

# Idle baseline for 20 s before the model starts.
: > "$CSV"
sample() {
  while :; do
    printf '%s %s %s %s %s\n' "$(date +%s)" \
      "$(cat "$BAT/current_now")" "$(cat "$BAT/voltage_now")" \
      "$(cat "$BAT/capacity")" "$(cat "$BAT/temp")" >> "$CSV"
    sleep 1
  done
}
sample &
sampler=$!
trap 'kill $sampler 2>/dev/null || true' EXIT
sleep 20

start=$(date +%s)
./bin/llama-server -m "$MODEL" --jinja \
  --chat-template-kwargs '{"enable_thinking":false}' \
  -c 4096 -t 4 --host 127.0.0.1 --port 8080 \
  > "server-$TAG.log" 2>&1 &
srv=$!
trap 'kill $sampler $srv 2>/dev/null || true' EXIT
for _ in $(seq 1 180); do
  curl -sf http://127.0.0.1:8080/health >/dev/null && break
  sleep 1
done

./bin/kuzya-eval -cases "$CASES" -out "eval-$TAG.jsonl" > "eval-$TAG.txt" 2>&1 || true
end=$(date +%s)
sleep 5
kill -9 "$sampler" 2>/dev/null || true
wait "$sampler" 2>/dev/null || true
pkill -P "$sampler" 2>/dev/null || true
hwm=$(grep VmHWM "/proc/$srv/status" | awk '{print $2}')
kill -9 "$srv" 2>/dev/null || true
wait "$srv" 2>/dev/null || true

queries=$(grep -c '^ok\|^FAIL' "eval-$TAG.txt" || true)
awk -v q="$queries" -v t0="$start" -v t1="$end" '
  { e += ($2 < 0 ? -$2 : $2) * $3 / 1e12; if ($1 >= t0 && $1 <= t1) run += ($2 < 0 ? -$2 : $2) * $3 / 1e12 }
  END {
    printf "energy_total_J=%.1f energy_run_J=%.1f queries=%d J_per_query=%.1f\n", e, run, q, (q ? run / q : 0)
  }' "$CSV"
echo "peak_kb=$hwm wall_seconds=$((end - start))"
tail -3 "eval-$TAG.txt"
