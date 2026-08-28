# sign_exe.ps1 - Gera certificado self-signed e assina FileHasher.exe para bypassar SAC
# Smart App Control permite exe assinado cujo cert esteja em Trusted Publishers
# Uso: powershell -ExecutionPolicy Bypass -File tools/sign_exe.ps1
# Requer: Windows SDK signtool OU PowerShell (usa Set-AuthenticodeSignature como fallback)

$ErrorActionPreference = "Continue"
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $projectRoot) { $projectRoot = "C:\dev_seiti\projects\file_hasher" }
$exe = Join-Path $projectRoot "dist\FileHasher.exe"
if (-not (Test-Path $exe)) { $exe = Join-Path $projectRoot "dist\FileHasher_Quick.exe" }
if (-not (Test-Path $exe)) {
    Write-Host "[!] Nenhum exe encontrado em dist/. Gere primeiro com build.bat" -ForegroundColor Red
    exit 1
}

Write-Host "[*] Alvo: $exe" -ForegroundColor Cyan

# 1. Tenta signtool (Windows SDK)
$signtool = $null
$kitPaths = @("C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe", "C:\Program Files\Windows Kits\10\bin\*\x64\signtool.exe")
foreach ($pat in $kitPaths) {
    $found = Get-ChildItem -Path $pat -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($found) { $signtool = $found.FullName; break }
}

# 2. Cria cert self-signed para Code Signing
$certName = "FileHasher SelfSigned"
Write-Host "[*] Criando certificado self-signed: $certName"
try {
    # Remove antigo se existir
    Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -like "*$certName*" } | Remove-Item -ErrorAction SilentlyContinue
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=$certName, O=FileHasher Local, OU=Dev" -KeyAlgorithm RSA -KeyLength 2048 -NotAfter (Get-Date).AddYears(5) -CertStoreLocation Cert:\CurrentUser\My -KeyUsage DigitalSignature -FriendlyName $certName -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3")
    Write-Host "[*] Cert criado: $($cert.Thumbprint) - $($cert.Subject)" -ForegroundColor Green
} catch {
    Write-Host "[!] Falha ao criar cert: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "    Tente rodar PowerShell como Admin"
    exit 1
}

# 3. Adiciona cert em Trusted Publishers (para SAC confiar)
Write-Host "[*] Adicionando cert em Trusted Publishers (requer admin p/ LocalMachine, tenta CurrentUser)..."
try {
    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("TrustedPublisher","CurrentUser")
    $store.Open("ReadWrite")
    $store.Add($cert)
    $store.Close()
    Write-Host "[*] Cert adicionado em Cert:\CurrentUser\TrustedPublisher" -ForegroundColor Green
} catch {
    Write-Host "[!] Falha TrustedPublisher CurrentUser: $($_.Exception.Message)"
}
# Tenta LocalMachine se for admin
try {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} catch { $isAdmin = $false }
if ($isAdmin) {
    try {
        $store2 = New-Object System.Security.Cryptography.X509Certificates.X509Store("TrustedPublisher","LocalMachine")
        $store2.Open("ReadWrite")
        $store2.Add($cert)
        $store2.Close()
        Write-Host "[*] Cert adicionado em Cert:\LocalMachine\TrustedPublisher (admin)" -ForegroundColor Green
        # Tambem adiciona em Root para cadeia confiar (self-signed)
        try {
            $storeRoot = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root","CurrentUser")
            $storeRoot.Open("ReadWrite")
            $storeRoot.Add($cert)
            $storeRoot.Close()
            Write-Host "[*] Cert adicionado em Cert:\CurrentUser\Root (para cadeia confiar)" -ForegroundColor Green
        } catch {}
    } catch {
        Write-Host "[!] Falha LocalMachine (mesmo admin): $($_.Exception.Message)"
    }
} else {
    Write-Host "[!] Nao eh admin - cert so em CurrentUser. Para SAC, pode precisar admin. Rode este script como Admin: clique direito -> Executar como administrador" -ForegroundColor Yellow
    Write-Host "    Mesmo assim, use FileHasher.bat (bypass via python assinado) que funciona sem cert." -ForegroundColor Yellow
}

# 4. Assina
if ($signtool -and (Test-Path $signtool)) {
    Write-Host "[*] Assinando com signtool: $signtool"
    Write-Host "[*] Comando: signtool sign /fd SHA256 /a /tr http://timestamp.digicert.com /td SHA256 `"$exe`""
    try {
        & $signtool sign /fd SHA256 /a /tr http://timestamp.digicert.com /td SHA256 "$exe"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[*] Assinado com signtool OK!" -ForegroundColor Green
        } else {
            throw "signtool exit $LASTEXITCODE"
        }
    } catch {
        Write-Host "[!] signtool falhou: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "[*] Tentando Set-AuthenticodeSignature fallback..."
        $signtool = $null
    }
}

if (-not $signtool) {
    Write-Host "[*] Fallback: Set-AuthenticodeSignature (PowerShell)"
    try {
        $result = Set-AuthenticodeSignature -FilePath $exe -Certificate $cert -HashAlgorithm SHA256 -TimestampServer "http://timestamp.digicert.com"
        Write-Host "[*] Status: $($result.Status)" -ForegroundColor $(if($result.Status -eq "Valid"){"Green"}else{"Red"})
        if ($result.Status -ne "Valid") {
            Write-Host $result | Format-List | Out-String | Write-Host
        }
    } catch {
        Write-Host "[!] Set-AuthenticodeSignature falhou: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

# 5. Verifica
Write-Host "`n[*] Verificando assinatura..."
try {
    if ($signtool) {
        & $signtool verify /pa "$exe"
    } else {
        Get-AuthenticodeSignature "$exe" | Format-List | Out-String | Write-Host
    }
} catch {}

Write-Host "`n=== Pronto ===" -ForegroundColor Green
Write-Host "Exe assinado: $exe"
Write-Host "Cert: $certName ($($cert.Thumbprint))"
Write-Host "Agora SAC deve permitir (pois cert esta em Trusted Publishers)."
Write-Host "Se ainda bloquear, desative SAC temporariamente: Windows Security > App & browser control > Smart App Control > Off"
Write-Host "Ou use FileHasher.bat / FileHasher.ps1 (bypass via python assinado)"
