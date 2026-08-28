@echo off
REM build_quick.bat - Gera .exe SEM bundle ClamAV (rapido para teste, ~10MB)
REM Scan local ficara OFF, mas da para testar hash + VT

pushd "%~dp0\.."
python -m pip install pyinstaller -q
echo [*] Build rapido sem clamav/yara...
python -m PyInstaller --onefile --name FileHasher_Quick --add-data "web/index.html;." --add-data "web/sha256.min.js;." src/main.py --noconfirm --clean
echo EXE: dist\FileHasher_Quick.exe
popd
pause
