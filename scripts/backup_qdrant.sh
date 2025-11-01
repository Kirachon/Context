#!/usr/bin/env bash
set -euo pipefail

# Usage: scripts/backup_qdrant.sh [BACKUP_DIR]
BACKUP_DIR="${1:-backups}"
CONTAINER="${QDRANT_CONTAINER:-context-qdrant}"

mkdir -p "$BACKUP_DIR"
ts=$(date +%Y%m%d-%H%M%S)
file="$BACKUP_DIR/qdrant-$ts.tar.gz"

echo "Creating Qdrant backup: $file"
# Archive the storage directory from inside the container
# This captures collections and payloads
docker exec "$CONTAINER" tar czf - -C / qdrant/storage | cat > "$file"
echo "Backup written to $file" 

