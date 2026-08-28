# bundle_all.ps1 - compat: agora chama bootstrap.ps1 (leve, sem git)
# Uso: powershell -ExecutionPolicy Bypass -File tools/bundle_all.ps1
# ou melhor: powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1

Write-Host "=== horash bundle (compat) ===" -ForegroundColor Cyan
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $toolsDir "bootstrap.ps1") @args
if ($LASTEXITCODE -ne 0) { Write-Host "[!] bootstrap falhou" -ForegroundColor Red }

Write-Host "`n=== bundle pronto ===" -ForegroundColor Green
Write-Host "pastas criadas: clamav/ yara/"
Write-Host "proximo: scripts\build.bat (leve) ou scripts\build_setup.bat (setups)"
Get-ChildItem (Split-Path -Parent $toolsDir) | Where-Object { $_.Name -in @("clamav","yara") } | Format-Table Name, LastWriteTime -AutoSize
