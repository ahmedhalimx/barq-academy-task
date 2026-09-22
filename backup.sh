#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/barq_tasks_${TIMESTAMP}.sql"

mkdir -p "${BACKUP_DIR}"

echo "Creating PostgreSQL backup from container 'postgres'..."

if docker exec -T postgres pg_dump -U barq_app -d barq_tasks > "${BACKUP_FILE}"; then
    if [ -s "${BACKUP_FILE}" ]; then
        echo "Backup successfully created: ${BACKUP_FILE}"
        exit 0
    else
        echo "Error: Backup file is empty." >&2
        rm -f "${BACKUP_FILE}"
        exit 1
    fi
else
    echo "Error: pg_dump failed." >&2
    rm -f "${BACKUP_FILE}"
    exit 1
fi
