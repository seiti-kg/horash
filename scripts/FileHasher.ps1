# FileHasher.ps1 - Launcher PowerShell que bypassa SAC (assinado via Microsoft)
# SAC permite powershell.exe assinado, diferente de .exe custom nao assinado
# Uso: clique direito -> Executar com PowerShell, ou: powershell -ExecutionPolicy Bypass -File FileHasher.ps1

$ErrorActionPreference = "Continue"
$scriptsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptsDir
Set-Location $projectRoot

Write-Host "[*] File Hasher - ClamAV+YARA (PowerShell launcher, bypass SAC)" -ForegroundColor Cyan
Write-Host "[*] Projeto: $projectRoot"

# Encontra Python
$py = $null
foreach ($cmd in @("python","python3","py")) {
    try {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($found) { $py = $found.Source; break }
    } catch {}
}
if (-not $py) {
    $storePy = "$env:LOCALAPPDATA\Microsoft\WindowsApps\python.exe"
    if (Test-Path $storePy) { $py = $storePy }
}

if (-not $py) {
    Write-Host "[!] Python nao encontrado. Instale via winget ou Store" -ForegroundColor Red
    Write-Host "    winget install Python.Python.3.11 --silent"
    Read-Host "Pressione Enter para sair"
    exit 1
}

Write-Host "[*] Python: $py" -ForegroundColor Green
& $py --version
Write-Host "[*] Iniciando src/main.py (http://localhost:8765)..."
Write-Host "[*] Feche esta janela para encerrar"

# Roda main.py (que ja abre navegador)
& $py src/main.py

Write-Host "[*] Encerrado"
Read-Host "Pressione Enter"
