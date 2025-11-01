#!/usr/bin/env bash
set -euo pipefail

# Usage: scripts/restore_postgres.sh <SQL_FILE>
BACKUP_FILE="${1:?Usage: scripts/restore_postgres.sh <SQL_FILE>}"
DB="${POSTGRES_DB:-context_dev}"
USER="${POSTGRES_USER:-context}"
CONTAINER="${POSTGRES_CONTAINER:-context-postgres}"
PASSWORD="${POSTGRES_PASSWORD:-password}"

echo "Restoring PostgreSQL database $DB from $BACKUP_FILE"
cat "$BACKUP_FILE" | docker exec -e PGPASSWORD="$PASSWORD" -i "$CONTAINER" psql -U "$USER" "$DB"
echo "Restore complete" 

