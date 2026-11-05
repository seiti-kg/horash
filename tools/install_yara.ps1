# install_yara.ps1 - instala YARA Windows + regras para horash
# uso: powershell -ExecutionPolicy Bypass -File tools/install_yara.ps1 [-Package core|extended|full]

param(
    [ValidateSet("core", "extended", "full")]
    [string]$Package = "full"
)

$ErrorActionPreference = "Continue"
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $toolsDir
$destDir = Join-Path $projectRoot "yara"
$zipPath = Join-Path $env:TEMP "yara.zip"

Write-Host "[*] yara - tentando baixar binario Windows"
Write-Host "[*] destino: $destDir"

if (Test-Path $destDir) {
    Write-Host "[*] limpando binarios/regras antigos (fallback preservado)..."
    foreach ($old in @("yara64.exe", "yarac64.exe", "yara.exe", "yarac.exe", "yara64.bat")) {
        Remove-Item (Join-Path $destDir $old) -Force -ErrorAction SilentlyContinue
    }
    Remove-Item (Join-Path $destDir "rules") -Recurse -Force -ErrorAction SilentlyContinue
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

Write-Host "[*] baixando regras YARA Forge ($Package)..."
$rulesDir = Join-Path $destDir "rules"
New-Item -ItemType Directory -Force -Path $rulesDir | Out-Null
$rulesYar = Join-Path $rulesDir "$Package.yar"
$rulesYarc = Join-Path $rulesDir "$Package.yarc"
$assetName = "yara-forge-rules-$Package.zip"
$tmpZip = Join-Path $env:TEMP "yara-forge-$Package.zip"
$tmpExtract = Join-Path $env:TEMP "yara-forge-extract-$Package"
$downloadUrl = $null
$expectedHash = $null

try {
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/YARAHQ/yara-forge/releases/latest" -Headers @{ "User-Agent" = "horash-installer" } -TimeoutSec 30
    $asset = $release.assets | Where-Object { $_.name -eq $assetName } | Select-Object -First 1
    if ($asset) {
        $downloadUrl = $asset.browser_download_url
        if ($asset.digest) { $expectedHash = ($asset.digest -replace '^sha256:', '').ToLower() }
        Write-Host "[*] release $($release.tag_name): $assetName ($([math]::Round($asset.size/1MB,2)) MB)"
    }
} catch {
    Write-Host "[!] API do YARA Forge falhou: $($_.Exception.Message)" -ForegroundColor Yellow
}
if (-not $downloadUrl) {
    $downloadUrl = "https://github.com/YARAHQ/yara-forge/releases/latest/download/$assetName"
    Write-Host "[!] usando latest/download sem checksum" -ForegroundColor Yellow
}

$forgeOk = $false
try {
    if (Test-Path $tmpZip) { Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue }
    if (Test-Path $tmpExtract) { Remove-Item -Recurse -Force $tmpExtract -ErrorAction SilentlyContinue }
    Invoke-WebRequest -Uri $downloadUrl -OutFile $tmpZip -UseBasicParsing -TimeoutSec 120
    if ((Test-Path $tmpZip) -and ((Get-Item $tmpZip).Length -gt 100000)) {
        if ($expectedHash) {
            $actualHash = (Get-FileHash -LiteralPath $tmpZip -Algorithm SHA256).Hash.ToLower()
            if ($actualHash -ne $expectedHash) { throw "checksum SHA256 nao confere" }
            Write-Host "[*] checksum SHA256 ok"
        }
        Expand-Archive -LiteralPath $tmpZip -DestinationPath $tmpExtract -Force
        $ruleFile = Get-ChildItem -Path $tmpExtract -Recurse -Filter "yara-rules-$Package.yar" | Select-Object -First 1
        if (-not $ruleFile) {
            $ruleFile = Get-ChildItem -Path $tmpExtract -Recurse -Filter "*.yar" | Select-Object -First 1
        }
        if (-not $ruleFile) { throw "arquivo .yar nao encontrado no zip" }

        Copy-Item $ruleFile.FullName $rulesYar -Force
        $ruleCount = (Select-String -Path $rulesYar -Pattern "^rule " -ErrorAction SilentlyContinue | Measure-Object).Count
        Write-Host "[*] regras $Package instaladas: $rulesYar ($ruleCount regras, $([math]::Round((Get-Item $rulesYar).Length/1MB,2)) MB)"

        $yarac = Get-ChildItem -Path $destDir -Recurse -Filter "yarac64.exe" | Select-Object -First 1
        if (-not $yarac) { $yarac = Get-ChildItem -Path $destDir -Recurse -Filter "yarac.exe" | Select-Object -First 1 }
        if ($yarac) {
            & $yarac.FullName $rulesYar $rulesYarc
            if (($LASTEXITCODE -eq 0) -and (Test-Path $rulesYarc)) {
                Write-Host "[*] regras compiladas: $rulesYarc ($([math]::Round((Get-Item $rulesYarc).Length/1MB,2)) MB)"
            } else {
                Write-Host "[!] falha ao compilar .yarc; o scanner usa o .yar" -ForegroundColor Yellow
            }
        } else {
            Write-Host "[!] yarac64.exe nao encontrado; sem .yarc" -ForegroundColor Yellow
        }
        $forgeOk = $true
    }
} catch {
    Write-Host "[!] falha ao instalar regras: $($_.Exception.Message)" -ForegroundColor Yellow
}
if (Test-Path $tmpZip) { Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue }
if (Test-Path $tmpExtract) { Remove-Item -Recurse -Force $tmpExtract -ErrorAction SilentlyContinue }

if (-not $forgeOk) {
    Write-Host "[!] yara-forge falhou, usando fallback curado local..." -ForegroundColor Yellow
    $fixPy = Join-Path $toolsDir "fix_yara.py"
    if (Test-Path $fixPy) {
        Push-Location $projectRoot
        try {
            python $fixPy
            $rulesYar = Join-Path $destDir "fallback.yar"
            Write-Host "[*] fallback curado via fix_yara.py"
        } catch {
            Write-Host "[!] fallback falhou: $($_.Exception.Message)" -ForegroundColor Red
        } finally {
            Pop-Location
        }
    } else {
        Write-Host "[!] fix_yara.py nao encontrado em $fixPy" -ForegroundColor Red
    }
}

Write-Host "[*] limpando..."
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

Write-Host "[*] yara instalado em $destDir"
Get-ChildItem $destDir | Format-Table Name, Length -AutoSize
if (Test-Path $rulesYar) {
    $ruleCount = (Select-String -Path $rulesYar -Pattern "^rule " -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host "[*] regras ativas: $rulesYar ($ruleCount regras)"
} else {
    Write-Host "[!] nenhuma regra encontrada; o scan YARA vai reportar erro" -ForegroundColor Red
}
Write-Host "[*] teste: yara64.exe $rulesYar <arquivo>"
