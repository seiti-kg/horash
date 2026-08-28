@echo off
REM horash.bat - launcher que bypassa Smart App Control (SAC)
REM SAC bloqueia .exe nao assinado, mas permite python.exe assinado (Microsoft Store)
REM este .bat chama python src/main.py e funciona mesmo com SAC em Enforced

title horash
echo [*] horash - iniciando...
echo [*] se falhar, instale Python 3.11+ da Microsoft Store: https://apps.microsoft.com/detail/9NRWMJP3717K
echo.

REM usa diretorio do proprio .bat, nao o cwd
set "HORASH_DIR=%~dp0"
if "%HORASH_DIR:~-1%"=="\" set "HORASH_DIR=%HORASH_DIR:~0,-1%"

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python --version
    python "%HORASH_DIR%\src\main.py"
    pause
    exit /b
)

where python3 >nul 2>nul
if %ERRORLEVEL%==0 (
    python3 --version
    python3 "%HORASH_DIR%\src\main.py"
    pause
    exit /b
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py --version
    py "%HORASH_DIR%\src\main.py"
    pause
    exit /b
)

if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" (
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" "%HORASH_DIR%\src\main.py"
    pause
    exit /b
)

echo [!] python nao encontrado.
echo     instale via: winget install Python.Python.3.11
echo     ou https://www.python.org/downloads/
echo     ou Microsoft Store
pause
exit /b 1
