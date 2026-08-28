@echo off
REM start.bat - Inicia File Hasher com ClamAV+YARA sempre ativo + VT anonimo
REM Duplo clique aqui e depois abra http://localhost:8765
REM Se tiver FileHasher.exe (build), ele ja inclui tudo - use ele com duplo clique

pushd "%~dp0\.."

echo [*] File Hasher - ClamAV+YARA sempre ativo + VT anonimo
echo [*] Porta: http://localhost:8765
echo [*] Se tiver dist\FileHasher.exe, pode usar ele direto (sem Python)
echo.

REM tenta python e python3
where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python src\server.py
    pause
    popd
    exit /b
)

where python3 >nul 2>nul
if %ERRORLEVEL%==0 (
    python3 src\server.py
    pause
    popd
    exit /b
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py src\server.py
    pause
    popd
    exit /b
)

echo [ERRO] Python nao encontrado no PATH.
echo Instale Python 3.9+ e tente novamente.
popd
pause
