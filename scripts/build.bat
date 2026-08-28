@echo off
REM build.bat - Gera FileHasher.exe unico com ClamAV+YARA sempre ativo
REM Uso: duplo clique ou cmd: scripts\build.bat (ou build.bat na raiz via atalho)

REM Vai para a raiz do projeto (parent de scripts/)
pushd "%~dp0\.."

echo === File Hasher Build .exe ===

REM Verifica Python
python --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] Python nao encontrado. Instale Python 3.9+ e adicione ao PATH
    pause
    exit /b 1
)

REM Verifica PyInstaller
python -m PyInstaller --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [*] Instalando PyInstaller...
    python -m pip install -r requirements.txt
)

REM Verifica clamav/yara bundle
if not exist clamav (
    echo [!] Pasta clamav/ nao encontrada
    echo [*] Rodando tools/bundle_all.ps1 (pode demorar 2-5min, baixa ~300MB)...
    powershell -ExecutionPolicy Bypass -File tools/bundle_all.ps1
    if %ERRORLEVEL% neq 0 (
        echo [!] Bundle falhou, mas tentando build mesmo assim (scan local ficara OFF)
    )
)

if not exist yara (
    echo [!] Pasta yara/ nao encontrada, tentando instalar...
    powershell -ExecutionPolicy Bypass -File tools/install_yara.ps1
)

echo [*] Limpando builds antigos...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

echo [*] Gerando FileHasher.exe (pode demorar 1-3min)...
python -m PyInstaller FileHasher.spec --noconfirm --clean

if %ERRORLEVEL% neq 0 (
    echo [!] Build falhou
    popd
    pause
    exit /b 1
)

echo.
echo === Build OK ===
echo EXE: dist\FileHasher.exe
dir dist\FileHasher.exe | find "FileHasher"
echo.
echo Para testar: dist\FileHasher.exe
echo (vai abrir http://localhost:8765 e ja com ClamAV+YARA)
echo.
popd
pause
