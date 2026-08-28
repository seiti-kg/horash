@echo off
REM horash.bat - launcher que bypassa Smart App Control (SAC)
REM SAC bloqueia .exe nao assinado, mas permite python.exe assinado (Microsoft Store)
REM este .bat chama python src/main.py e funciona mesmo com SAC em Enforced

title horash
echo [*] horash - iniciando...
echo [*] se falhar, instale Python 3.11+ da Microsoft Store: https://apps.microsoft.com/detail/9NRWMJP3717K
echo.

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python --version
    python src\main.py
    pause
    exit /b
)

where python3 >nul 2>nul
if %ERRORLEVEL%==0 (
    python3 --version
    python3 src\main.py
    pause
    exit /b
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py --version
    py src\main.py
    pause
    exit /b
)

if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" (
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" src\main.py
    pause
    exit /b
)

echo [!] python nao encontrado.
echo     instale via: winget install Python.Python.3.11
echo     ou https://www.python.org/downloads/
echo     ou Microsoft Store
pause
exit /b 1
