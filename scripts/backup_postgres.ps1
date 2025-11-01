param(
  [string]$BackupDir = "backups",
  [string]$Container = "context-postgres"
)

$ErrorActionPreference = "Stop"
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$db = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "context_dev" }
$user = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "context" }
$pwd = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "password" }

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$file = Join-Path $BackupDir "postgres-$db-$ts.sql"

Write-Host "Creating PostgreSQL backup: $file"
& docker exec -e PGPASSWORD=$pwd -t $Container pg_dump -U $user $db | Set-Content -Path $file -Encoding UTF8
Write-Host "Backup written to $file"

