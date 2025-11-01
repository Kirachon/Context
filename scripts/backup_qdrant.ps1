param(
  [string]$BackupDir = "backups",
  [string]$Container = "context-qdrant"
)

$ErrorActionPreference = "Stop"
$ts = Get-Date -Format "yyyyMMdd-HHmmss"

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$file = Join-Path $BackupDir "qdrant-$ts.tar.gz"

Write-Host "Creating Qdrant backup: $file"
# Stream archive from inside the container to host file
& docker exec $Container tar czf - -C / qdrant/storage | Set-Content -Path $file -Encoding Byte
Write-Host "Backup written to $file"

