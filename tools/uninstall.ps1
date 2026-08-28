# uninstall.ps1 - remove horash instalado via install.ps1
$installDir = "$env:LOCALAPPDATA\horash"
Write-Host "[*] removendo $installDir ..." -ForegroundColor Yellow
if (Test-Path $installDir) {
    Remove-Item -Recurse -Force $installDir -ErrorAction SilentlyContinue
    Write-Host "[*] pasta removida" -ForegroundColor Green
}
$desktop = Join-Path ([Environment]::GetFolderPath("Desktop")) "horash.lnk"
$startMenu = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs\horash.lnk"
foreach ($lnk in @($desktop, $startMenu)) {
    if (Test-Path $lnk) { Remove-Item $lnk -Force -ErrorAction SilentlyContinue; Write-Host "[*] atalho removido: $lnk" }
}
$shimDir = Join-Path $installDir "bin"
try {
    $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -like "*$shimDir*") {
        $newPath = ($userPath -split ";" | Where-Object { $_ -ne $shimDir }) -join ";"
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
        Write-Host "[*] removido do PATH" -ForegroundColor Green
    }
} catch {}
Write-Host "[*] desinstalado" -ForegroundColor Cyan
