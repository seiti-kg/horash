# bootstrap.ps1 - baixa clamav + yara sem git, sem manual
# uso: powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1
# chamado pelo horash_setup.exe leve ou manual via Releases

$ErrorActionPreference = "Continue"
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $toolsDir
# se rodar de {app} instalado, projectRoot = {app}
if (-not (Test-Path (Join-Path $projectRoot "src\main.py"))) {
    # tenta achar horash instalado
    $candidates = @(
        "$env:LOCALAPPDATA\horash",
        "$env:PROGRAMFILES\horash",
        "${env:ProgramFiles(x86)}\horash",
        (Join-Path $projectRoot "..")
    )
    foreach ($c in $candidates) {
        if (Test-Path (Join-Path $c "horash.exe")) { $projectRoot = $c; break }
    }
}
Write-Host "[*] horash bootstrap - destino: $projectRoot" -ForegroundColor Cyan

$doClamav = $true
$doYara = $true
# args: -no-clamav, -no-yara
foreach ($a in $args) {
    if ($a -eq "-no-clamav") { $doClamav = $false }
    if ($a -eq "-no-yara") { $doYara = $false }
}

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Download-WithProgress($url, $dest) {
    Write-Host "[*] baixando $url"
    try {
        # tenta com progresso via BitsTransfer se disponivel, fallback Invoke-WebRequest
        try {
            Import-Module BitsTransfer -ErrorAction SilentlyContinue
            Start-BitsTransfer -Source $url -Destination $dest -ErrorAction Stop
            return $true
        } catch {}
        Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing -TimeoutSec 120
        return (Test-Path $dest) -and ((Get-Item $dest).Length -gt 1000)
    } catch {
        Write-Host "[!] falha: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

if ($doClamav) {
    $clamavDir = Join-Path $projectRoot "clamav"
    $dbDir = Join-Path $clamavDir "db"
    if ((Test-Path (Join-Path $clamavDir "clamscan.exe")) -and (Test-Path $dbDir) -and ((Get-ChildItem $dbDir -Filter "*.cvd" -ErrorAction SilentlyContinue | Measure-Object).Count -ge 2)) {
        Write-Host "[*] clamav ja instalado em $clamavDir, pulando download" -ForegroundColor Green
        Write-Host "[*] atualizando assinaturas (freshclam)..."
        try { & (Join-Path $clamavDir "freshclam.exe") --datadir="$dbDir" --quiet } catch { Write-Host "[!] freshclam falhou, tudo bem - assinaturas locais ok" }
    } else {
        Write-Host "`n[1/2] clamav..." -ForegroundColor Yellow
        & (Join-Path $toolsDir "install_clamav.ps1")
        if ($LASTEXITCODE -ne 0) { Write-Host "[!] clamav falhou mas continua" -ForegroundColor Red }
    }
} else {
    Write-Host "[*] clamav pulado (-no-clamav)"
}

if ($doYara) {
    $yaraDir = Join-Path $projectRoot "yara"
    $rulesYar = Join-Path $yaraDir "rules.yar"
    $hasRules = (Test-Path $rulesYar) -and ((Get-Item $rulesYar -ErrorAction SilentlyContinue).Length -gt 5000)
    if ($hasRules -and (Test-Path (Join-Path $yaraDir "yara64.exe"))) {
        Write-Host "[*] yara ja instalado em $yaraDir, pulando" -ForegroundColor Green
    } else {
        Write-Host "`n[2/2] yara..." -ForegroundColor Yellow
        & (Join-Path $toolsDir "install_yara.ps1")
        if ($LASTEXITCODE -ne 0) { Write-Host "[!] yara falhou mas continua" -ForegroundColor Red }
    }
} else {
    Write-Host "[*] yara pulado (-no-yara)"
}

Write-Host "`n[*] verificando..." -ForegroundColor Cyan
try {
    $py = "python"
    if (Get-Command "python" -ErrorAction SilentlyContinue) { $py = "python" } elseif (Get-Command "py" -ErrorAction SilentlyContinue) { $py = "py" }
    & $py (Join-Path $projectRoot "src\scanner.py") 2>&1 | Write-Host
} catch {}
Get-ChildItem $projectRoot -Directory | Where-Object { $_.Name -in @("clamav","yara") } | ForEach-Object {
    $s = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host ("[*] {0}: {1:N1} MB" -f $_.Name, $s)
}
Write-Host "`n[*] pronto! rode horash.exe ou horash.bat" -ForegroundColor Green
