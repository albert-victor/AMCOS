# Expose local Django (port 8000) via ngrok.
# 1) Start Django FIRST in another terminal:
#      python manage.py runserver 8000
# 2) Then run this script:
#      .\scripts\ngrok-dev.ps1

$ErrorActionPreference = "Stop"
$port = if ($env:NGROK_PORT) { $env:NGROK_PORT } else { "8000" }
$addr = "127.0.0.1:$port"

Write-Host ""
Write-Host "=== AMCOS ngrok tunnel ===" -ForegroundColor Green
Write-Host "Target: http://$addr (Django must already be running)" -ForegroundColor Yellow
Write-Host ""
Write-Host "After ngrok starts, copy the https://....ngrok-free.dev URL into .env:" -ForegroundColor Cyan
Write-Host "  CSRF_TRUSTED_ORIGINS=https://YOUR-SUBDOMAIN.ngrok-free.dev" -ForegroundColor Cyan
Write-Host "  (Optional) NGROK_URL=https://YOUR-SUBDOMAIN.ngrok-free.dev" -ForegroundColor Cyan
Write-Host ""
Write-Host "Do NOT use --host-header=rewrite (breaks CSRF with Django)." -ForegroundColor Yellow
Write-Host ""

# Quick local check
try {
    $r = Invoke-WebRequest -Uri "http://$addr/health/" -UseBasicParsing -TimeoutSec 3
    Write-Host "Local Django OK (HTTP $($r.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Cannot reach http://$addr — start runserver first!" -ForegroundColor Red
    Write-Host "  python manage.py runserver $port" -ForegroundColor Red
}

$ngrok = Get-Command ngrok -ErrorAction SilentlyContinue
if (-not $ngrok) {
    Write-Host "ngrok not found in PATH. Install from https://ngrok.com/download" -ForegroundColor Red
    exit 1
}

& ngrok http $addr
