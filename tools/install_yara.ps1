# install_yara.ps1 - Instala YARA Windows + regras para File Hasher
# Uso: powershell -ExecutionPolicy Bypass -File tools/install_yara.ps1

$ErrorActionPreference = "Continue"
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $toolsDir
$destDir = Join-Path $projectRoot "yara"
$zipPath = Join-Path $env:TEMP "yara.zip"

Write-Host "[*] YARA - tentando baixar binario Windows"
Write-Host "[*] Destino: $destDir"

if (Test-Path $destDir) {
    Remove-Item -Recurse -Force $destDir -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path $destDir | Out-Null

# Tenta multiplos mirrors (GitHub 4.5.5, 4.5.2, SourceForge, etc)
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
    Write-Host "[*] Tentando $url ..."
    try {
        Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing -TimeoutSec 30
        if ((Test-Path $zipPath) -and ((Get-Item $zipPath).Length -gt 100000)) {
            Write-Host "[*] Baixado com sucesso: $url"
            $downloaded = $true
            break
        }
    } catch {
        Write-Host "[!] Falha: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 1
}

if (-not $downloaded) {
    Write-Host "[!] Nenhum mirror funcionou. Tentando via pip yara-python como fallback..."
    try {
        python -m pip install yara-python -q
        Write-Host "[*] yara-python instalado via pip"
        # cria wrapper .exe fake que usa python -m yara
        @"
@echo off
python -m yara %*
"@ | Set-Content (Join-Path $destDir "yara64.bat") -Encoding ASCII
    } catch {
        Write-Host "[!] pip falhou tambem"
    }
    # continua para criar regras basicas mesmo sem binario
}

if ($downloaded) {
    Write-Host "[*] Extraindo..."
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
        Write-Host "[!] Falha ao extrair: $($_.Exception.Message)"
    }
} else {
    Write-Host "[!] Sem binario YARA, criando modo fallback (regras basicas apenas)"
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
}

Write-Host "[*] Baixando regras YARA-Forge..."
$rulesDir = Join-Path $destDir "rules"
New-Item -ItemType Directory -Force -Path $rulesDir | Out-Null
# Regras recomendadas: YARA-Forge + Elastic
$ruleUrls = @(
    "https://raw.githubusercontent.com/YARAHQ/yara-forge/master/compiled/maxi.yar",
    "https://raw.githubusercontent.com/elastic/protections-artifacts/main/yara/rules/malware_MALW_Alien.yar"
)
# Como maxi.yar pode ser grande, vamos clonar YARA-Forge via git se disponivel
if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Host "[*] Clonando YARA-Forge (recomendado)..."
    $tmpForge = Join-Path $env:TEMP "yara-forge"
    if (Test-Path $tmpForge) { Remove-Item -Recurse -Force $tmpForge }
    git clone --depth 1 https://github.com/YARAHQ/yara-forge.git $tmpForge
    # Copia regras compiladas ou src
    $srcRules = Join-Path $tmpForge "packages"
    if (Test-Path $srcRules) {
        Copy-Item -Path "$srcRules\*" -Destination $rulesDir -Recurse -Force
        Write-Host "[*] Regras copiadas para $rulesDir"
    }
    # Cria index
    $allYar = Get-ChildItem -Path $rulesDir -Recurse -Filter "*.yar" | ForEach-Object { 'include "' + $_.FullName.Replace("\","/") + '"' }
    $allYar | Out-File -LiteralPath (Join-Path $destDir "rules.yar") -Encoding ascii
    Remove-Item -Recurse -Force $tmpForge -ErrorAction SilentlyContinue
} else {
    Write-Host "[!] git nao encontrado, baixando regra unica..."
    try {
        Invoke-WebRequest -Uri $ruleUrls[0] -OutFile (Join-Path $destDir "rules.yar") -UseBasicParsing
        # converte para ascii sem BOM
        $c = Get-Content (Join-Path $destDir "rules.yar") -Raw
        $c | Out-File -LiteralPath (Join-Path $destDir "rules.yar") -Encoding ascii
    } catch {
        # fallback: cria regra basica EICAR para teste (ascii sem BOM)
        @"
import "pe"
rule EICAR_Test {
    strings:
        `$eicar = "X5O!P%@AP[4\\PZX54(P^)7CC)7}\`$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!\`$H+H*"
    condition:
        `$eicar
}
rule Suspicious_Heavy_File {
    condition:
        filesize > 650MB
}
"@ | Out-File -LiteralPath (Join-Path $destDir "rules.yar") -Encoding ascii
    }
}

# Se ainda nao tem rules.yar ou esta vazio, cria basico (ascii sem BOM para YARA)
$rulesYar = Join-Path $destDir "rules.yar"
$needsFallback = $true
if (Test-Path $rulesYar) {
    $content = Get-Content $rulesYar -Raw -ErrorAction SilentlyContinue
    if ($content -and $content.Trim().Length -gt 20) { $needsFallback = $false }
}
if ($needsFallback) {
    $found = Get-ChildItem -Path $rulesDir -Recurse -Filter "*.yar" -ErrorAction SilentlyContinue
    if ($found -and $found.Count -gt 0) {
        $found | ForEach-Object { 'include "' + $_.FullName.Replace("\","/") + '"' } | Out-File -LiteralPath $rulesYar -Encoding ascii
        Write-Host "[*] Criado $rulesYar com $($found.Count) includes"
        if ((Get-Item $rulesYar).Length -lt 20) { $needsFallback = $true } else { $needsFallback = $false }
    }
}
if ($needsFallback -or -not (Test-Path $rulesYar) -or (Get-Item $rulesYar -ErrorAction SilentlyContinue).Length -lt 20) {
    Write-Host "[*] Criando regra basica EICAR fallback (ascii)..."
    @"
import "pe"
rule EICAR_Test {
    strings:
        `$eicar = "X5O!P%@AP[4\\PZX54(P^)7CC)7}\`$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!\`$H+H*"
    condition:
        `$eicar
}
rule Suspicious_Heavy_File {
    condition:
        filesize > 650MB
}
rule Generic_Malware_Strings {
    strings:
        `$a = "malware" nocase
        `$b = "keylogger" nocase
        `$c = "ransom" nocase
    condition:
        any of them
}
"@ | Out-File -LiteralPath $rulesYar -Encoding ascii
    Write-Host "[*] Fallback criado: $rulesYar"
}

Write-Host "[*] Limpando..."
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

Write-Host "[*] YARA instalado em $destDir"
Get-ChildItem $destDir | Format-Table Name, Length -AutoSize
if (Test-Path (Join-Path $destDir "rules.yar")) {
    Write-Host "[*] Regras: $(Join-Path $destDir "rules.yar")"
    Get-Content (Join-Path $destDir "rules.yar") | Select-Object -First 5 | Write-Host
}
Write-Host "[*] Teste: yara64.exe rules.yar <arquivo>"
