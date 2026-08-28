# install_yara.ps1 - instala YARA Windows + regras para horash
# uso: powershell -ExecutionPolicy Bypass -File tools/install_yara.ps1

$ErrorActionPreference = "Continue"
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $toolsDir
$destDir = Join-Path $projectRoot "yara"
$zipPath = Join-Path $env:TEMP "yara.zip"

Write-Host "[*] yara - tentando baixar binario Windows"
Write-Host "[*] destino: $destDir"

if (Test-Path $destDir) {
    Remove-Item -Recurse -Force $destDir -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path $destDir | Out-Null

$urls = @(
    "https://github.com/VirusTotal/yara/releases/download/v4.5.2/yara-v4.5.2-2326-win64.zip",
    "https://github.com/VirusTotal/yara/releases/download/v4.5.1/yara-v4.5.1-2329-win64.zip",
    "https://github.com/VirusTotal/yara/releases/download/v4.5.5/yara-v4.5.5-2368-win64.zip",
    "https://sourceforge.net/projects/yara.mirror/files/v4.5.2/yara-v4.5.2-2326-win64.zip/download",
    "https://github.com/VirusTotal/yara/releases/download/v4.3.2/yara-4.3.2-2150-win64.zip"
)
$downloaded = $false
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
foreach ($url in $urls) {
    Write-Host "[*] tentando $url ..."
    try {
        Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing -TimeoutSec 30
        if ((Test-Path $zipPath) -and ((Get-Item $zipPath).Length -gt 100000)) {
            Write-Host "[*] baixado: $url"
            $downloaded = $true
            break
        }
    } catch {
        Write-Host "[!] falha: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 1
}

if (-not $downloaded) {
    Write-Host "[!] nenhum mirror funcionou, tentando via pip yara-python..."
    try {
        python -m pip install yara-python -q
        Write-Host "[*] yara-python instalado via pip"
        "@echo off`npython -m yara %*" | Set-Content (Join-Path $destDir "yara64.bat") -Encoding ASCII
    } catch {
        Write-Host "[!] pip falhou tambem"
    }
}

if ($downloaded) {
    Write-Host "[*] extraindo..."
    try {
        Expand-Archive -LiteralPath $zipPath -DestinationPath $destDir -Force
        $yaraExe = Get-ChildItem -Path $destDir -Recurse -Filter "yara64.exe" | Select-Object -First 1
        if ($yaraExe -and $yaraExe.FullName -ne (Join-Path $destDir "yara64.exe")) {
            Copy-Item $yaraExe.FullName $destDir -Force -ErrorAction SilentlyContinue
            Write-Host "[*] yara64.exe em $destDir"
        } elseif ($yaraExe) {
            Write-Host "[*] yara64.exe ja em $destDir"
        }
        try { & (Join-Path $destDir "yara64.exe") --version } catch { Write-Host "[!] yara64.exe falhou" }
        if (-not $yaraExe) {
            $alt = Get-ChildItem -Path $destDir -Recurse -Filter "yara.exe" | Select-Object -First 1
            if ($alt -and $alt.FullName -ne (Join-Path $destDir "yara.exe")) { Copy-Item $alt.FullName $destDir -Force; Write-Host "[*] yara.exe copiado" }
        }
    } catch {
        Write-Host "[!] falha ao extrair: $($_.Exception.Message)"
    }
} else {
    Write-Host "[!] sem binario yara, criando modo fallback (regras basicas apenas)"
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
}

Write-Host "[*] baixando regras yara-forge (core)..."
$rulesDir = Join-Path $destDir "rules"
New-Item -ItemType Directory -Force -Path $rulesDir | Out-Null
$rulesYar = Join-Path $destDir "rules.yar"

$forgeOk = $false
$forgeUrls = @(
    "https://github.com/YARAHQ/yara-forge/releases/download/20260823/yara-forge-rules-core.zip",
    "https://github.com/YARAHQ/yara-forge/releases/download/20260809/yara-forge-rules-core.zip",
    "https://github.com/YARAHQ/yara-forge/releases/latest/download/yara-forge-rules-core.zip"
)
$tmpZip = Join-Path $env:TEMP "yara-forge-core.zip"
$tmpExtract = Join-Path $env:TEMP "yara-forge-extract"
foreach ($furl in $forgeUrls) {
    Write-Host "[*] tentando $furl ..."
    try {
        if (Test-Path $tmpZip) { Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue }
        if (Test-Path $tmpExtract) { Remove-Item -Recurse -Force $tmpExtract -ErrorAction SilentlyContinue }
        Invoke-WebRequest -Uri $furl -OutFile $tmpZip -UseBasicParsing -TimeoutSec 60
        if ((Test-Path $tmpZip) -and ((Get-Item $tmpZip).Length -gt 100000)) {
            Write-Host "[*] baixado core: $furl ($([math]::Round((Get-Item $tmpZip).Length/1MB,2)) MB)"
            Expand-Archive -LiteralPath $tmpZip -DestinationPath $tmpExtract -Force
            $coreYar = Get-ChildItem -Path $tmpExtract -Recurse -Filter "yara-rules-core.yar" | Select-Object -First 1
            if ($coreYar) {
                Copy-Item $coreYar.FullName $rulesYar -Force
                Copy-Item $coreYar.FullName (Join-Path $rulesDir "yara-rules-core.yar") -Force
                Write-Host "[*] regras core instaladas: $rulesYar ($([math]::Round((Get-Item $rulesYar).Length/1MB,2)) MB)"
                $forgeOk = $true
                break
            }
        }
    } catch {
        Write-Host "[!] falha core: $($_.Exception.Message)"
    }
}
if (Test-Path $tmpZip) { Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue }
if (Test-Path $tmpExtract) { Remove-Item -Recurse -Force $tmpExtract -ErrorAction SilentlyContinue }

if (-not $forgeOk) {
    Write-Host "[!] yara-forge core falhou, usando fallback curado local..." -ForegroundColor Yellow
    $fixPy = Join-Path $toolsDir "fix_yara.py"
    if (Test-Path $fixPy) {
        try {
            python $fixPy
            Write-Host "[*] fallback curado via fix_yara.py"
        } catch {
            Write-Host "[!] fallback falhou: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "[!] fix_yara.py nao encontrado em $fixPy" -ForegroundColor Red
    }
}

try {
    $yarac = Get-ChildItem -Path $destDir -Recurse -Filter "yarac64.exe" | Select-Object -First 1
    if ($yarac) { & $yarac.FullName $rulesYar "$env:TEMP\dummy" 2>&1 | Out-Null; Write-Host "[*] validacao yara ok" }
} catch {}

Write-Host "[*] limpando..."
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

Write-Host "[*] yara instalado em $destDir"
Get-ChildItem $destDir | Format-Table Name, Length -AutoSize
if (Test-Path $rulesYar) {
    Write-Host "[*] regras: $rulesYar"
    Get-Content $rulesYar | Select-Object -First 5 | Write-Host
}
Write-Host "[*] teste: yara64.exe rules.yar <arquivo>"
