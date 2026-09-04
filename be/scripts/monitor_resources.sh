#!/usr/bin/env bash
#
# monitor_resources.sh — samples `docker stats` for the drillovacka containers
# at a fixed interval and appends to a CSV, so a load-test run (see
# load_test_games.py) can be checked afterwards for a memory leak: RSS that
# keeps climbing over the run and doesn't come back down once load stops is
# the signature to look for, not just a high peak.
#
# Usage:
#   ./monitor_resources.sh [interval_seconds] [output_csv]
#
# Run this in its own terminal BEFORE starting a load test, let it keep
# running for a few minutes after the test ends too (to see whether memory
# is reclaimed), then Ctrl+C it and inspect the CSV (or plot it).
#
# Safe by construction: read-only (`docker stats`), touches nothing but its
# own output file.

set -euo pipefail

INTERVAL="${1:-5}"
OUT="${2:-resource_log_$(date +%Y%m%d_%H%M%S).csv}"

echo "timestamp,container,cpu_percent,mem_usage,mem_limit,mem_percent,net_io,block_io,pids" > "$OUT"
echo "Logging docker stats every ${INTERVAL}s to $OUT — Ctrl+C to stop."

while true; do
  ts="$(date -Iseconds)"
  # Only containers whose name contains "be-" (web/db/redis/nginx from this
  # project's compose) — adjust the grep if your compose project name differs.
  docker stats --no-stream --format \
    '{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}' \
    | grep -E '^(be-|drillovacka)' | while IFS=',' read -r name cpu mem_usage mem_perc net_io block_io pids; do
        mem_used="${mem_usage%% / *}"
        mem_limit="${mem_usage##* / }"
        echo "${ts},${name},${cpu},${mem_used},${mem_limit},${mem_perc},${net_io},${block_io},${pids}" >> "$OUT"
      done
  sleep "$INTERVAL"
done
