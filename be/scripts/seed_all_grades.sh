#!/usr/bin/env bash
set -euo pipefail

# Runs all known grade setup/seed commands that exist in current codebase.
# Usage:
#   ./scripts/seed_all_grades.sh
#   ./scripts/seed_all_grades.sh --dry-run

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODE="apply"
if [[ "${1:-}" == "--dry-run" ]]; then
  MODE="dry-run"
fi

echo "[seed_all_grades] root=$ROOT_DIR"
echo "[seed_all_grades] mode=$MODE"

RUNNER="python manage.py"
if command -v docker >/dev/null 2>&1 && docker compose ps web >/dev/null 2>&1; then
  RUNNER="docker compose exec -T web python manage.py"
fi
echo "[seed_all_grades] runner=$RUNNER"

run_cmd() {
  local cmd="$1"
  local check_cmd="${RUNNER} ${cmd} --help"

  if ! eval "$check_cmd" >/dev/null 2>&1; then
    echo "[skip] ${cmd} (command not found)"
    return 0
  fi

  if [[ "$MODE" == "apply" ]]; then
    echo "[run] ${cmd} --apply"
    eval "${RUNNER} ${cmd} --apply"
  else
    echo "[run] ${cmd} (dry-run)"
    eval "${RUNNER} ${cmd}"
  fi
}

run_cmd "setup_grade1_skills"
run_cmd "seed_grade1_missing_examples"

run_cmd "setup_grade2_skills"
run_cmd "seed_grade2_drill_examples"

run_cmd "setup_grade3_skills"
run_cmd "seed_grade3_drill_examples"

run_cmd "setup_grade4_skills"
run_cmd "seed_grade4_drill_examples"

run_cmd "setup_grade5_skills"
run_cmd "seed_grade5_drill_examples"

run_cmd "setup_grade6_skills"
run_cmd "seed_grade6_drill_examples"

run_cmd "setup_grade7_skills"
run_cmd "seed_grade7_drill_examples"

run_cmd "setup_grade8_skills"
run_cmd "seed_grade8_drill_examples"

run_cmd "setup_grade9_skills"
run_cmd "seed_grade9_drill_examples"

echo "[seed_all_grades] done"
