# Dev environment setup. Idempotent — safe to re-run.
# Usage: pwsh -File scripts/dev_setup.ps1

Write-Host "Starting db..." -ForegroundColor Cyan
docker compose up -d db

Write-Host "Waiting for db to be healthy..." -ForegroundColor Cyan
$timeout = 30
$elapsed = 0
while ($elapsed -lt $timeout) {
    $status = (docker compose ps db --format json | ConvertFrom-Json).Health
    if ($status -eq "healthy") { break }
    Start-Sleep -Seconds 1
    $elapsed++
}
if ($elapsed -ge $timeout) {
    Write-Error "db did not become healthy within ${timeout}s"
    exit 1
}

Write-Host "Applying migrations..." -ForegroundColor Cyan
docker compose run --rm migrator alembic upgrade head
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "Ensuring test database exists..." -ForegroundColor Cyan
$check = docker compose exec -T db psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='notes_test';"
if ($check.Trim() -ne "1") {
    docker compose exec -T db psql -U postgres -c "CREATE DATABASE notes_test;"
    Write-Host "  Created notes_test" -ForegroundColor Green
} else {
    Write-Host "  notes_test already exists" -ForegroundColor Green
}

Write-Host "Seeding units..." -ForegroundColor Cyan
docker compose run --rm api python -m scripts.seed_units

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green