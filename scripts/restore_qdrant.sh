#!/usr/bin/env bash
set -euo pipefail

# Usage: scripts/restore_qdrant.sh <ARCHIVE.tar.gz>
ARCHIVE="${1:?Usage: scripts/restore_qdrant.sh <ARCHIVE.tar.gz>}"
CONTAINER="${QDRANT_CONTAINER:-context-qdrant}"

# Stop Qdrant to avoid inconsistent state
echo "Stopping $CONTAINER"
docker stop "$CONTAINER" >/dev/null

echo "Restoring Qdrant data from $ARCHIVE"
# Use a helper container to write into the stopped container's volumes
docker run --rm --volumes-from "$CONTAINER" -v "$(pwd)":/backup alpine \
  sh -c "rm -rf /qdrant/storage/* && tar xzf /backup/$ARCHIVE -C /"

echo "Starting $CONTAINER"
docker start "$CONTAINER" >/dev/null
echo "Restore complete" 

