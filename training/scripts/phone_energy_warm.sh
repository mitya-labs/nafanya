#!/bin/sh
# Warm energy measurement: the server must already be running with a restored slot cache.
# Usage: ./phone_energy_warm.sh [tag] [cases]
set -eu
cd "$HOME/kuzya"

TAG=${1:-warm-1.7b}
CASES=${2:-cases30.json}
FLAGS=${FLAGS:-}
BAT=/sys/class/power_supply/qcom-battery
CSV="$TAG.csv"

./kuzya-server status >/dev/null 2>&1 || { echo "start kuzya-server first" >&2; exit 1; }

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
trap 'kill -9 "$sampler" 2>/dev/null || true' EXIT
sleep 15

start=$(date +%s)
./bin/kuzya-eval $FLAGS -cases "$CASES" -out "eval-$TAG.jsonl" > "eval-$TAG.txt" 2>&1 || true
end=$(date +%s)
sleep 5
kill -9 "$sampler" 2>/dev/null || true
wait "$sampler" 2>/dev/null || true

queries=$(grep -cE '^(ok|FAIL)' "eval-$TAG.txt" || true)
awk -v q="$queries" -v t0="$start" -v t1="$end" '
  NR == 1 { base_samples = 1 }
  { p = ($2 < 0 ? -$2 : $2) * $3 / 1e12
    if ($1 < t0) { bs += p; bn++ }
    if ($1 >= t0 && $1 <= t1) { run += p; n++ } }
  END {
    base = (bn ? bs / bn : 0)
    printf "baseline_W=%.2f window_s=%d energy_run_J=%.1f queries=%d J_per_query=%.1f above_idle_J_per_query=%.1f\n", \
      base, (t1 - t0), run, q, (q ? run / q : 0), (q ? (run - base * (t1 - t0)) / q : 0)
  }' "$CSV"
tail -2 "eval-$TAG.txt"
