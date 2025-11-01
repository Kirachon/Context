#!/usr/bin/env bash
set -euo pipefail

# Usage: scripts/backup_postgres.sh [BACKUP_DIR]
BACKUP_DIR="${1:-backups}"
DB="${POSTGRES_DB:-context_dev}"
USER="${POSTGRES_USER:-context}"
CONTAINER="${POSTGRES_CONTAINER:-context-postgres}"
PASSWORD="${POSTGRES_PASSWORD:-password}"

mkdir -p "$BACKUP_DIR"
ts=$(date +%Y%m%d-%H%M%S)
file="$BACKUP_DIR/postgres-$DB-$ts.sql"

echo "Creating PostgreSQL backup: $file"
docker exec -e PGPASSWORD="$PASSWORD" -t "$CONTAINER" pg_dump -U "$USER" "$DB" > "$file"
echo "Backup written to $file" 

