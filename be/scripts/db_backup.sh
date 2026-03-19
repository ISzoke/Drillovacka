#!/usr/bin/env bash
# Daily MySQL backup → compressed dump → upload to MEGA

set -euo pipefail

PROJECT_DIR="/home/debian/superlectures/be"
BACKUP_DIR="${PROJECT_DIR}/db_backups"
DB_NAME="drillovacka-demo"
DB_USER="root"
DB_PASS=$(grep '^MYSQLPASSWORD=' "${PROJECT_DIR}/.env" | cut -d= -f2)
CONTAINER="be-db-1"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/drillovacka_${TIMESTAMP}.sql.gz"
LOG="${BACKUP_DIR}/backup.log"

# Read MEGA credentials directly from .env
MEGA_EMAIL=$(grep '^MEGA_EMAIL=' "${PROJECT_DIR}/.env" | cut -d= -f2)
MEGA_PASSWORD=$(grep '^MEGA_PASSWORD=' "${PROJECT_DIR}/.env" | cut -d= -f2)

mkdir -p "${BACKUP_DIR}"
echo "[$(date '+%F %T')] Starting backup" >> "${LOG}"

# Dump and compress
docker exec "${CONTAINER}" mysqldump -u"${DB_USER}" -p"${DB_PASS}" "${DB_NAME}" \
    --single-transaction --quick --lock-tables=false \
    | gzip > "${BACKUP_FILE}" \
    && echo "[$(date '+%F %T')] Dump OK: ${BACKUP_FILE}" >> "${LOG}" \
    || { echo "[$(date '+%F %T')] ERROR: dump failed" >> "${LOG}"; exit 1; }

# Upload to MEGA using megatools
if megaput \
    --username "${MEGA_EMAIL}" \
    --password "${MEGA_PASSWORD}" \
    --path /Root/db_backups \
    --no-progress \
    "${BACKUP_FILE}" >> "${LOG}" 2>&1; then
    echo "[$(date '+%F %T')] MEGA upload OK: ${BACKUP_FILE}" >> "${LOG}"
else
    echo "[$(date '+%F %T')] WARN: MEGA upload failed, local backup kept" >> "${LOG}"
fi

# Keep only last 14 days of local backups
find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +14 -delete

echo "[$(date '+%F %T')] Backup finished" >> "${LOG}"
