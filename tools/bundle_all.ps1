# bundle_all.ps1 - Prepara tudo para build do .exe
# Uso: powershell -ExecutionPolicy Bypass -File tools/bundle_all.ps1

Write-Host "=== File Hasher Bundle ===" -ForegroundColor Cyan
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "`n[1/2] ClamAV..." -ForegroundColor Yellow
& (Join-Path $toolsDir "install_clamav.ps1")
if ($LASTEXITCODE -ne 0) { Write-Host "[!] ClamAV falhou, continue mesmo assim" -ForegroundColor Red }

Write-Host "`n[2/2] YARA..." -ForegroundColor Yellow
& (Join-Path $toolsDir "install_yara.ps1")
if ($LASTEXITCODE -ne 0) { Write-Host "[!] YARA falhou" -ForegroundColor Red }

Write-Host "`n=== Bundle pronto ===" -ForegroundColor Green
Write-Host "Pastas criadas: clamav/ yara/"
Write-Host "Proximo: python -m pip install -r requirements.txt; pyinstaller FileHasher.spec"
Get-ChildItem (Split-Path -Parent $toolsDir) | Where-Object { $_.Name -in @("clamav","yara") } | Format-Table Name, LastWriteTime -AutoSize
