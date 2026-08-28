@echo off
REM build_setup.bat - gera horash_setup.exe e horash_setup_offline.exe
pushd "%~dp0\.."

where iscc >nul 2>nul
if %ERRORLEVEL% neq 0 (
    if not exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
        echo [!] Inno Setup 6 nao encontrado. instale via: choco install innosetup
        echo     ou https://jrsoftware.org/isdl.php
        pause
        exit /b 1
    )
    set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else (
    set ISCC=iscc
)

if not exist dist\horash.exe (
    echo [*] horash.exe nao encontrado, gerando...
    python -m PyInstaller horash.spec --noconfirm --clean
)

echo [*] gerando horash_setup.exe (leve)...
%ISCC% tools\horash_setup.iss
if %ERRORLEVEL% neq 0 (
    echo [!] falha horash_setup
    popd
    pause
    exit /b 1
)

echo [*] preparando engines para offline (se faltar)...
if not exist clamav\clamscan.exe (
    echo [*] baixando clamav/yara (2-5 min)...
    powershell -ExecutionPolicy Bypass -File tools\bootstrap.ps1
)

echo [*] gerando horash_setup_offline.exe (full)...
%ISCC% tools\horash_setup_offline.iss
if %ERRORLEVEL% neq 0 (
    echo [!] falha horash_setup_offline
    popd
    pause
    exit /b 1
)

echo.
echo === setups ok ===
dir dist\horash_setup*.exe
popd
pause
