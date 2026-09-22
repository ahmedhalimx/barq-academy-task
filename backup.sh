#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/barq_tasks_${TIMESTAMP}.sql"

if [ "$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' postgres 2>/dev/null || true)" != "barq-assessment" ]; then
    echo "Error: container 'postgres' is not owned by the barq-assessment Compose project." >&2
    exit 1
fi

mkdir -p "${BACKUP_DIR}"

echo "Creating PostgreSQL backup from container 'postgres'..."

if docker exec postgres pg_dump -U barq_app -d barq_tasks > "${BACKUP_FILE}"; then
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
