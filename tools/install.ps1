# install.ps1 - instalador horash via irm (sem .exe, sem SAC block)
# uso: powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/seiti-kg/horash/main/tools/install.ps1 | iex"
# ou:  irm https://raw.githubusercontent.com/seiti-kg/horash/main/tools/install.ps1 | iex

$ErrorActionPreference = "Stop"
$repo = "seiti-kg/horash"
$branch = "main"
$installDir = "$env:LOCALAPPDATA\horash"
$zipUrl = "https://github.com/$repo/archive/refs/heads/$branch.zip"
$tmpZip = Join-Path $env:TEMP "horash.zip"
$tmpExtract = Join-Path $env:TEMP "horash-extract"

Write-Host "[*] horash - instalador" -ForegroundColor Cyan
Write-Host "[*] destino: $installDir"

# 1. verifica python
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0) { $python = $cmd; Write-Host "[*] python encontrado: $ver ($cmd)" -ForegroundColor Green; break }
    } catch {}
}
if (-not $python) {
    Write-Host "[!] python nao encontrado, tentando instalar via winget..." -ForegroundColor Yellow
    try {
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
            $python = "python"
            Write-Host "[*] python instalado via winget, reinicie o terminal se falhar" -ForegroundColor Green
        } else {
            throw "winget nao encontrado"
        }
    } catch {
        Write-Host "[!] instale python manualmente:" -ForegroundColor Red
        Write-Host "    https://www.python.org/downloads/ ou https://apps.microsoft.com/detail/9NRWMJP3717K"
        Write-Host "    depois rode novamente: irm https://raw.githubusercontent.com/$repo/$branch/tools/install.ps1 | iex"
        exit 1
    }
}

# 2. baixa zip do repo
Write-Host "[*] baixando $zipUrl ..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
try {
    if (Test-Path $tmpZip) { Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue }
    if (Test-Path $tmpExtract) { Remove-Item -Recurse -Force $tmpExtract -ErrorAction SilentlyContinue }
    Invoke-WebRequest -Uri $zipUrl -OutFile $tmpZip -UseBasicParsing -TimeoutSec 60
    if (-not (Test-Path $tmpZip) -or ((Get-Item $tmpZip).Length -lt 10000)) { throw "zip vazio" }
    Write-Host "[*] baixado $([math]::Round((Get-Item $tmpZip).Length/1KB,1)) KB"
    Expand-Archive -LiteralPath $tmpZip -DestinationPath $tmpExtract -Force
    $src = Get-ChildItem $tmpExtract -Directory | Select-Object -First 1
    if (-not $src) { throw "falha ao extrair" }
    Write-Host "[*] extraido para $($src.FullName)"
} catch {
    Write-Host "[!] falha ao baixar: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 3. instala/atualiza
if (Test-Path $installDir) {
    Write-Host "[*] atualizando instalacao existente..."
    # preserva clamav/db e yara se ja existem
    $keepClamav = Test-Path (Join-Path $installDir "clamav\db\main.cvd")
    $keepYara = Test-Path (Join-Path $installDir "yara\rules.yar")
}
New-Item -ItemType Directory -Force -Path $installDir | Out-Null
# copia tudo exceto .git, clamav, yara (preserva se ja tem)
$exclude = @(".git", "clamav", "yara", "build", "dist", "__pycache__")
Get-ChildItem $src.FullName -Force | Where-Object { $_.Name -notin $exclude } | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $installDir $_.Name) -Recurse -Force
}
Write-Host "[*] copiado para $installDir"

# 4. dependencias python
Write-Host "[*] instalando dependencias python..."
try {
    & $python -m pip install -q --upgrade pip 2>&1 | Out-Null
    & $python -m pip install -q -r (Join-Path $installDir "requirements.txt") 2>&1 | Out-Null
    Write-Host "[*] dependencias ok" -ForegroundColor Green
} catch {
    Write-Host "[!] falha pip: $($_.Exception.Message)" -ForegroundColor Yellow
}

# 5. baixa protecoes (clamav/yara) se nao tem
$needBootstrap = $false
if (-not (Test-Path (Join-Path $installDir "yara\yara64.exe"))) { $needBootstrap = $true }
if (-not (Test-Path (Join-Path $installDir "clamav\clamscan.exe"))) { $needBootstrap = $true }
if ($needBootstrap) {
    Write-Host "[*] baixando protecoes (clamav ~300mb + yara 7mb, 2-5 min)..." -ForegroundColor Yellow
    try {
        $bootstrap = Join-Path $installDir "tools\bootstrap.ps1"
        if (Test-Path $bootstrap) {
            powershell -ExecutionPolicy Bypass -File $bootstrap
        } else {
            Write-Host "[!] bootstrap.ps1 nao encontrado, pule" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[!] falha bootstrap: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[*] protecoes ja existem, pulando" -ForegroundColor Green
}

# 6. cria atalho na area de trabalho e menu iniciar
$desktop = [Environment]::GetFolderPath("Desktop")
$startMenu = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs\horash.lnk"
$targetBat = Join-Path $installDir "horash.bat"
$icon = Join-Path $installDir "web\favicon.ico"
try {
    $ws = New-Object -ComObject WScript.Shell
    foreach ($lnkPath in @((Join-Path $desktop "horash.lnk"), $startMenu)) {
        $dir = Split-Path $lnkPath -Parent
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        $lnk = $ws.CreateShortcut($lnkPath)
        $lnk.TargetPath = $targetBat
        $lnk.WorkingDirectory = $installDir
        if (Test-Path $icon) { $lnk.IconLocation = $icon }
        $lnk.Description = "horash - triage local"
        $lnk.Save()
        Write-Host "[*] atalho criado: $lnkPath" -ForegroundColor Green
    }
} catch {
    Write-Host "[!] falha ao criar atalho: $($_.Exception.Message)" -ForegroundColor Yellow
}

# 7. cria comando horash no PATH (opcional, via shims)
$shimDir = Join-Path $installDir "bin"
New-Item -ItemType Directory -Force -Path $shimDir | Out-Null
$shim = Join-Path $shimDir "horash.cmd"
"@echo off`ncall `"$targetBat`" %*" | Set-Content $shim -Encoding ASCII
# adiciona ao PATH do usuario se nao tiver
try {
    $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -notlike "*$shimDir*") {
        [Environment]::SetEnvironmentVariable("PATH", "$userPath;$shimDir", "User")
        Write-Host "[*] adicionado ao PATH: $shimDir (reinicie terminal)" -ForegroundColor Green
    }
} catch {}

# limpeza
Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $tmpExtract -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "[*] instalado com sucesso em $installDir" -ForegroundColor Cyan
Write-Host "[*] para iniciar: horash (no terminal) ou duplo clique no atalho" -ForegroundColor Cyan
Write-Host "[*] para desinstalar: powershell -ExecutionPolicy Bypass -File $installDir\tools\uninstall.ps1" -ForegroundColor Gray

# pergunta se quer iniciar agora
$run = Read-Host "iniciar horash agora? (s/n)"
if ($run -eq "s" -or $run -eq "S") {
    Start-Process $targetBat -WorkingDirectory $installDir
}
