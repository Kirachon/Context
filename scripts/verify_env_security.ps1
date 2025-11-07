#!/usr/bin/env pwsh
# Verify that .env files are properly gitignored

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Environment File Security Verification                  ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$projectRoot = "D:\GitProjects\Context"
Set-Location $projectRoot

# Check 1: Verify .gitignore has .env
Write-Host "Check 1: Verifying .gitignore configuration..." -ForegroundColor Yellow
$gitignoreContent = Get-Content ".gitignore" -Raw

if ($gitignoreContent -match "\.env" -and $gitignoreContent -match "!\.env\.example") {
    Write-Host "✅ .gitignore correctly configured" -ForegroundColor Green
    Write-Host "   - .env files are ignored" -ForegroundColor Gray
    Write-Host "   - .env.example is tracked" -ForegroundColor Gray
} else {
    Write-Host "❌ .gitignore may not be properly configured" -ForegroundColor Red
}

Write-Host ""

# Check 2: Verify .env is not tracked by git
Write-Host "Check 2: Verifying .env files are not tracked..." -ForegroundColor Yellow

$trackedFiles = git ls-files | Select-String "\.env$"

if ($trackedFiles) {
    Write-Host "❌ WARNING: .env files are tracked by git!" -ForegroundColor Red
    Write-Host "   Files found:" -ForegroundColor Red
    $trackedFiles | ForEach-Object { Write-Host "   - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "   To fix this, run:" -ForegroundColor Yellow
    Write-Host "   git rm --cached deployment/docker/.env" -ForegroundColor White
} else {
    Write-Host "✅ No .env files are tracked by git" -ForegroundColor Green
}

Write-Host ""

# Check 3: Verify .env.example is tracked
Write-Host "Check 3: Verifying .env.example is tracked..." -ForegroundColor Yellow

$exampleTracked = git ls-files | Select-String "\.env\.example$"

if ($exampleTracked) {
    Write-Host "✅ .env.example is tracked (correct)" -ForegroundColor Green
} else {
    Write-Host "⚠️  .env.example is not tracked" -ForegroundColor Yellow
}

Write-Host ""

# Check 4: Verify actual .env file exists
Write-Host "Check 4: Checking for actual .env file..." -ForegroundColor Yellow

$envFile = "deployment/docker/.env"

if (Test-Path $envFile) {
    Write-Host "✅ .env file exists at: $envFile" -ForegroundColor Green
    
    # Check if it contains sensitive data
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match "GOOGLE_API_KEY=AIza") {
        Write-Host "✅ Contains Google API key" -ForegroundColor Green
    } elseif ($envContent -match "GOOGLE_API_KEY=") {
        Write-Host "⚠️  GOOGLE_API_KEY is set but appears empty" -ForegroundColor Yellow
    } else {
        Write-Host "ℹ️  GOOGLE_API_KEY not yet configured" -ForegroundColor Cyan
    }
} else {
    Write-Host "⚠️  .env file does not exist yet" -ForegroundColor Yellow
    Write-Host "   Run: .\scripts\setup_google_embeddings.ps1" -ForegroundColor Gray
}

Write-Host ""

# Check 5: Verify git status doesn't show .env
Write-Host "Check 5: Verifying git status..." -ForegroundColor Yellow

$gitStatus = git status --porcelain | Select-String "\.env$"

if ($gitStatus) {
    Write-Host "❌ WARNING: .env file appears in git status!" -ForegroundColor Red
    Write-Host "   This means it might be committed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "   To fix this, run:" -ForegroundColor Yellow
    Write-Host "   git rm --cached deployment/docker/.env" -ForegroundColor White
    Write-Host "   git commit -m 'Remove .env from tracking'" -ForegroundColor White
} else {
    Write-Host "✅ .env file is properly ignored by git" -ForegroundColor Green
}

Write-Host ""

# Summary
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                      SUMMARY                               ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "Safe to commit:" -ForegroundColor Yellow
Write-Host "  ✅ .env.example (template with no secrets)" -ForegroundColor Green
Write-Host "  ✅ Source code files" -ForegroundColor Green
Write-Host "  ✅ Configuration files" -ForegroundColor Green
Write-Host ""

Write-Host "Never commit:" -ForegroundColor Yellow
Write-Host "  ❌ deployment/docker/.env (contains API keys)" -ForegroundColor Red
Write-Host "  ❌ Any file with actual secrets" -ForegroundColor Red
Write-Host ""

Write-Host "Your API key location:" -ForegroundColor Cyan
Write-Host "  📁 deployment/docker/.env" -ForegroundColor White
Write-Host "  🔒 This file is gitignored (safe)" -ForegroundColor Green
Write-Host ""

Write-Host "To add your API key:" -ForegroundColor Cyan
Write-Host "  1. Run: .\scripts\setup_google_embeddings.ps1" -ForegroundColor White
Write-Host "  2. Or manually edit: deployment/docker/.env" -ForegroundColor White
Write-Host ""

