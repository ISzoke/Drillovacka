#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BP_ROOT_DEFAULT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${SCRIPT_DIR}/dropbox-sync.env"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

BP_ROOT="${BP_ROOT:-${BP_ROOT_DEFAULT}}"
AUDIO_DIR="${AUDIO_DIR:-${BP_ROOT}/audioprompts}"
SURVEY_DIR="${SURVEY_DIR:-${BP_ROOT}/survey}"
RCLONE_BIN="${RCLONE_BIN:-rclone}"
RCLONE_REMOTE="${RCLONE_REMOTE:-dropbox:BP_Subject_Recordings}"
MIN_AGE="${MIN_AGE:-2m}"
LOG_FILE="${LOG_FILE:-${BP_ROOT}/dropbox-sync.log}"
LOCK_FILE="${LOCK_FILE:-/tmp/bp-dropbox-sync.lock}"

mkdir -p "$(dirname "${LOG_FILE}")"

echo "[$(date '+%F %T')] Starting Dropbox sync" >> "${LOG_FILE}"

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  echo "[$(date '+%F %T')] Sync already running, exiting" >> "${LOG_FILE}"
  exit 0
fi

if ! command -v "${RCLONE_BIN}" >/dev/null 2>&1; then
  echo "[$(date '+%F %T')] ERROR: rclone not found at '${RCLONE_BIN}'" >> "${LOG_FILE}"
  exit 1
fi

remote_name="${RCLONE_REMOTE%%:*}"
if ! "${RCLONE_BIN}" listremotes | grep -qx "${remote_name}:"; then
  echo "[$(date '+%F %T')] ERROR: rclone remote '${remote_name}' not configured" >> "${LOG_FILE}"
  exit 1
fi

sync_dir() {
  local source_dir="$1"
  local target_subdir="$2"

  if [[ ! -d "${source_dir}" ]]; then
    echo "[$(date '+%F %T')] WARN: missing directory '${source_dir}', skipping" >> "${LOG_FILE}"
    return 0
  fi

  if ! find "${source_dir}" -type f \( -name "*.wav" -o -name "*.json" \) -print -quit | grep -q .; then
    echo "[$(date '+%F %T')] No files to sync in '${source_dir}'" >> "${LOG_FILE}"
    return 0
  fi

  "${RCLONE_BIN}" move "${source_dir}/" "${RCLONE_REMOTE}/${target_subdir}/" \
    --min-age "${MIN_AGE}" \
    --include "*.wav" \
    --include "*.json" \
    --transfers 4 \
    --checkers 8 \
    --retries 3 \
    --low-level-retries 10 \
    --log-file "${LOG_FILE}" \
    --log-level INFO

  echo "[$(date '+%F %T')] Synced '${source_dir}' -> '${RCLONE_REMOTE}/${target_subdir}/'" >> "${LOG_FILE}"
}

sync_dir "${AUDIO_DIR}" "audioprompts"
sync_dir "${SURVEY_DIR}" "survey"

echo "[$(date '+%F %T')] Dropbox sync finished" >> "${LOG_FILE}"
