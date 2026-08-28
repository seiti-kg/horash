# install_clamav.ps1 - Instala ClamAV Windows para File Hasher
# Baixa ClamAV oficial e prepara DB, para uso com server.py / bundle .exe
# Uso: powershell -ExecutionPolicy Bypass -File tools/install_clamav.ps1

$ErrorActionPreference = "Stop"
$clamavVersion = "1.4.2"
$url = "https://www.clamav.net/downloads/production/clamav-$clamavVersion.win.x64.zip"
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $toolsDir
$destDir = Join-Path $projectRoot "clamav"
$zipPath = Join-Path $env:TEMP "clamav.zip"
$dbDir = Join-Path $destDir "db"

Write-Host "[*] ClamAV $clamavVersion"
Write-Host "[*] Destino: $destDir"

if (Test-Path $destDir) {
    Write-Host "[*] Removendo antigo..."
    Remove-Item -Recurse -Force $destDir -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path $destDir | Out-Null
New-Item -ItemType Directory -Force -Path $dbDir | Out-Null

Write-Host "[*] Baixando $url ..."
try {
    # Usa TLS 1.2
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
} catch {
    Write-Host "[!] Falha download oficial, tentando mirror..."
    # Mirror alternativo (GitHub release)
    $mirror = "https://github.com/Cisco-Talos/clamav/releases/download/rel%2F$clamavVersion/clamav-$clamavVersion.win.x64.zip"
    Invoke-WebRequest -Uri $mirror -OutFile $zipPath -UseBasicParsing
}

Write-Host "[*] Extraindo..."
Expand-Archive -LiteralPath $zipPath -DestinationPath $env:TEMP -Force
$extracted = Get-ChildItem -Path $env:TEMP -Directory | Where-Object { $_.Name -like "clamav*" } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $extracted) {
    Write-Error "Falha ao extrair"
    exit 1
}
Copy-Item -Path (Join-Path $extracted.FullName "*") -Destination $destDir -Recurse -Force

# Copia exemplo de conf
if (Test-Path (Join-Path $destDir "conf_examples\clamd.conf.sample")) {
    Copy-Item (Join-Path $destDir "conf_examples\clamd.conf.sample") (Join-Path $destDir "clamd.conf") -Force
    Copy-Item (Join-Path $destDir "conf_examples\freshclam.conf.sample") (Join-Path $destDir "freshclam.conf") -Force
    # Ajusta DB dir
    (Get-Content (Join-Path $destDir "clamd.conf")) -replace 'Example', '#Example' | Set-Content (Join-Path $destDir "clamd.conf")
    (Get-Content (Join-Path $destDir "freshclam.conf")) -replace 'Example', '#Example' | Set-Content (Join-Path $destDir "freshclam.conf")
    # Configura DatabaseDirectory
    Add-Content (Join-Path $destDir "freshclam.conf") "DatabaseDirectory $dbDir"
    Add-Content (Join-Path $destDir "clamd.conf") "DatabaseDirectory $dbDir"
}

Write-Host "[*] Baixando assinaturas iniciais (freshclam)..."
$oldPath = $env:PATH
$env:PATH = "$destDir;$env:PATH"
try {
    & (Join-Path $destDir "freshclam.exe") --datadir="$dbDir"
} catch {
    Write-Host "[!] freshclam falhou, tente rodar manualmente: $destDir\freshclam.exe --datadir=`"$dbDir`""
}
$env:PATH = $oldPath

Write-Host "[*] Limpando temp..."
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $extracted.FullName -ErrorAction SilentlyContinue

Write-Host "[*] ClamAV instalado em $destDir"
Write-Host "[*] Teste: $destDir\clamscan.exe --version"
& (Join-Path $destDir "clamscan.exe") --version

Write-Host "[*] Pronto! Server.py vai detectar automaticamente em clamav/db"
Write-Host "[*] Para atualizar assinaturas: $destDir\freshclam.exe --datadir=`"$dbDir`""
