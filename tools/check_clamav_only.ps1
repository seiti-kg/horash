# check_clamav_only.ps1 - Mostra SO ClamAV e se fecha ao parar terminal
# Uso: powershell -ExecutionPolicy Bypass -File tools/check_clamav_only.ps1

Write-Host "=== SO CLAMAV ===" -ForegroundColor Cyan
python -c "from scanner import check_scanners; import json; c=check_scanners(); print(json.dumps({k:v for k,v in c.items() if 'clamav' in k.lower()}, indent=2))"

Write-Host "`n--- Processo clamscan ---" -ForegroundColor Cyan
$p = Get-Process clamscan -ErrorAction SilentlyContinue
if ($p) { $p | Format-Table Id, ProcessName, CPU -AutoSize } else { Write-Host "Nenhum clamscan rodando agora (normal - so aparece DURANTE scan de 2-10s, depois morre)" -ForegroundColor Yellow }

Write-Host "`n--- Server :8765 ---" -ForegroundColor Cyan
$listen = netstat -ano | findstr "8765" | findstr "LISTENING"
if ($listen) {
    Write-Host "Server ON (terminal aberto):" -ForegroundColor Green
    $listen | Write-Host
    try { Invoke-RestMethod http://localhost:8765/health/scan | Select-Object -ExpandProperty clamav_available | ForEach-Object { Write-Host "Health clamav_available: $_" } } catch {}
} else {
    Write-Host "Server OFF (terminal fechado) -> ClamAV nao pode ser chamado" -ForegroundColor Red
}

Write-Host "`n--- Teste: fecha terminal = ClamAV fecha? ---" -ForegroundColor Cyan
Write-Host "1. Deixe este terminal do server aberto e rode este script em OUTRO terminal"
Write-Host "2. Feche o terminal do server (Ctrl+C ou X)"
Write-Host "3. Rode novamente: netstat -ano | findstr 8765  -> deve ficar vazio"
Write-Host "4. Get-Process clamscan -> deve ficar vazio (sem scan em andamento, sem processo)"
Write-Host "SIM, ao fechar o terminal o server morre e ClamAV (filho via subprocess.run em scanner.py:118) nao pode mais ser chamado. Se um scan estava em andamento, o clamscan filho termina em segundos e morre sozinho (nao fica daemon)."
