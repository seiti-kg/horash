# install_clamav.ps1 - instala ClamAV Windows para horash
# Baixa o zip oficial do GitHub, confere SHA-256 e preserva o banco existente.
# Uso: powershell -ExecutionPolicy Bypass -File tools/install_clamav.ps1

$ErrorActionPreference = "Stop"
$clamavVersion = "1.5.4"
$clamavSha256 = "0d9e0228b2674137ea1a2853566c98a0278ad52ab2582c3d6dbd75373848c395"
$urls = @(
    "https://github.com/Cisco-Talos/clamav/releases/download/clamav-$clamavVersion/clamav-$clamavVersion.win.x64.zip",
    "https://www.clamav.net/downloads/production/clamav-$clamavVersion.win.x64.zip"
)
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $toolsDir
$destDir = Join-Path $projectRoot "clamav"
$dbDir = Join-Path $destDir "db"
$zipPath = Join-Path $env:TEMP "clamav-$clamavVersion.zip"
$tmpExtract = Join-Path $env:TEMP ("clamav-extract-" + [guid]::NewGuid().ToString("N"))

Write-Host "[*] ClamAV $clamavVersion"
Write-Host "[*] Destino: $destDir"

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Baixa e valida ANTES de tocar na instalacao existente.
$downloaded = $false
foreach ($url in $urls) {
    Write-Host "[*] Baixando $url ..."
    try {
        if (Test-Path $zipPath) { Remove-Item $zipPath -Force -ErrorAction SilentlyContinue }
        Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing -TimeoutSec 300
        if ((Test-Path $zipPath) -and ((Get-Item $zipPath).Length -gt 100MB)) {
            $downloaded = $true
            break
        }
        Write-Host "[!] arquivo baixado invalido/tamanho inesperado" -ForegroundColor Yellow
    } catch {
        Write-Host "[!] falha: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}
if (-not $downloaded) {
    throw "Nao foi possivel baixar o ClamAV. Verifique a rede/proxy e tente novamente."
}

$actualHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLower()
if ($actualHash -ne $clamavSha256) {
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
    throw "Checksum SHA-256 do ClamAV nao confere (esperado $clamavSha256, obtido $actualHash)."
}
Write-Host "[*] checksum SHA256 ok"

Write-Host "[*] Extraindo..."
Expand-Archive -LiteralPath $zipPath -DestinationPath $tmpExtract -Force
$clamscan = Get-ChildItem -Path $tmpExtract -Recurse -Filter "clamscan.exe" | Select-Object -First 1
if (-not $clamscan) {
    throw "O zip baixado nao contem clamscan.exe."
}
$sourceRoot = $clamscan.Directory.FullName

# Preserva o banco antigo; substitui apenas binarios/configs.
if (Test-Path $destDir) {
    Write-Host "[*] Atualizando binarios (banco existente preservado)..."
    Get-ChildItem $destDir -Force | Where-Object { $_.Name -ne "db" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path $destDir | Out-Null
New-Item -ItemType Directory -Force -Path $dbDir | Out-Null
Copy-Item -Path (Join-Path $sourceRoot "*") -Destination $destDir -Recurse -Force

# Debug symbols, bibliotecas estaticas e manuais nao sao necessarios em runtime.
Get-ChildItem $destDir -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in @(".pdb", ".lib") } |
    Remove-Item -Force -ErrorAction SilentlyContinue
foreach ($extra in @("UserManual", "include")) {
    Remove-Item (Join-Path $destDir $extra) -Recurse -Force -ErrorAction SilentlyContinue
}

# Copia exemplo de conf, se ainda nao existir.
if (Test-Path (Join-Path $destDir "conf_examples\clamd.conf.sample")) {
    if (-not (Test-Path (Join-Path $destDir "clamd.conf"))) {
        Copy-Item (Join-Path $destDir "conf_examples\clamd.conf.sample") (Join-Path $destDir "clamd.conf") -Force
        (Get-Content (Join-Path $destDir "clamd.conf")) -replace 'Example', '#Example' | Set-Content (Join-Path $destDir "clamd.conf")
    }
    if (-not (Test-Path (Join-Path $destDir "freshclam.conf"))) {
        Copy-Item (Join-Path $destDir "conf_examples\freshclam.conf.sample") (Join-Path $destDir "freshclam.conf") -Force
        (Get-Content (Join-Path $destDir "freshclam.conf")) -replace 'Example', '#Example' | Set-Content (Join-Path $destDir "freshclam.conf")
    }
    foreach ($conf in @("freshclam.conf", "clamd.conf")) {
        $confPath = Join-Path $destDir $conf
        if (-not (Select-String -Path $confPath -Pattern "DatabaseDirectory" -Quiet -ErrorAction SilentlyContinue)) {
            Add-Content $confPath "DatabaseDirectory $dbDir"
        }
    }
}

Write-Host "[*] Atualizando assinaturas (freshclam)..."
$oldPath = $env:PATH
$env:PATH = "$destDir;$env:PATH"
try {
    & (Join-Path $destDir "freshclam.exe") --datadir="$dbDir"
} catch {
    Write-Host "[!] freshclam falhou; se ja havia banco, ele foi preservado." -ForegroundColor Yellow
    Write-Host "    rode manualmente: $destDir\freshclam.exe --datadir=`"$dbDir`""
} finally {
    $env:PATH = $oldPath
}

$dbOk = (Test-Path (Join-Path $dbDir "main.cvd")) -or (Test-Path (Join-Path $dbDir "main.cld")) -or
        (Test-Path (Join-Path $dbDir "daily.cvd")) -or (Test-Path (Join-Path $dbDir "daily.cld"))
if (-not $dbOk) {
    Write-Host "[!] banco do ClamAV ausente; o ClamAV vai aparecer como indisponivel ate rodar freshclam." -ForegroundColor Yellow
}

Write-Host "[*] Limpando temp..."
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $tmpExtract -ErrorAction SilentlyContinue

Write-Host "[*] ClamAV instalado em $destDir"
Write-Host "[*] Teste: $destDir\clamscan.exe --version"
& (Join-Path $destDir "clamscan.exe") --version

Write-Host "[*] Pronto! O server detecta automaticamente em clamav/db"
Write-Host "[*] Para atualizar assinaturas: $destDir\freshclam.exe --datadir=`"$dbDir`""
