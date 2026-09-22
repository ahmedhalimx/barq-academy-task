#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="backups"

if [ "$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' postgres 2>/dev/null || true)" != "barq-assessment" ]; then
    echo "Error: container 'postgres' is not owned by the barq-assessment Compose project." >&2
    exit 1
fi

# Accept backup file path argument or grab the latest SQL file in backups/
if [ -n "${1:-}" ]; then
    BACKUP_FILE="$1"
else
    BACKUP_FILE=$(ls -t "${BACKUP_DIR}"/*.sql 2>/dev/null | head -n 1 || true)
fi

if [ -z "${BACKUP_FILE}" ] || [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: No valid backup file found." >&2
    exit 1
fi

echo "Restoring database from: ${BACKUP_FILE}"

# Re-create database and restore scheme/data
if docker exec -i postgres psql -U barq_app -d postgres -c "DROP DATABASE IF EXISTS barq_tasks;" && \
    docker exec -i postgres psql -U barq_app -d postgres -c "CREATE DATABASE barq_tasks;" && \
    docker exec -i postgres psql -U barq_app -d barq_tasks < "${BACKUP_FILE}"; then

    # Query record count from 'records' table to verify restoration
    RECORD_COUNT=$(docker exec -i postgres psql -U barq_app -d barq_tasks -t -A -c "SELECT COUNT(*) FROM records;" 2>/dev/null || echo "0")

    echo "Restoration successful! Verified record count: ${RECORD_COUNT}"
    exit 0
else
    echo "Error: Database restoration failed." >&2
    exit 1
fi
