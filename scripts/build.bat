@echo off
REM build.bat - gera horash.exe leve (~12mb) + setups
pushd "%~dp0\.."

echo === horash build ===

python --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] python nao encontrado. instale python 3.11+
    pause
    exit /b 1
)

python -m PyInstaller --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [*] instalando pyinstaller...
    python -m pip install -r requirements.txt
)

echo [*] limpando builds antigos...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [*] gerando horash.exe leve (horash.spec)...
python -m PyInstaller horash.spec --noconfirm --clean
if %ERRORLEVEL% neq 0 (
    echo [!] build horash.exe falhou
    popd
    pause
    exit /b 1
)

echo.
echo === build ok ===
dir dist\horash.exe | find "horash"
echo.
echo para testar: dist\horash.exe
echo.
echo para gerar setups (requer Inno Setup 6):
echo   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" tools\horash_setup.iss
echo   powershell -ExecutionPolicy Bypass -File tools\bootstrap.ps1
echo   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" tools\horash_setup_offline.iss
echo.
popd
pause
