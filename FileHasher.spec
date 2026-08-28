# -*- mode: python ; coding: utf-8 -*-
# FileHasher.spec - Build .exe unico com ClamAV+YARA sempre ativo
# Uso: pyinstaller FileHasher.spec
# Requer: tools/bundle_all.ps1 ja executado (pastas clamav/ yara/ existem)

import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Pasta do projeto
project_root = os.path.abspath(os.path.dirname(__name__) if '__name__' in globals() else os.getcwd())

# Datas: inclui web/ e pastas clamav/yara se existirem
datas = [
    ('web/index.html', '.'),
    ('web/sha256.min.js', '.'),
    ('web/favicon.ico', '.'),
    ('web/favicon.png', '.'),
    ('web/favicon-32.png', '.'),
    # server.py etc como fallback de arquivo para main.py spec_from_file_location
    ('src/server.py', '.'),
    ('src/scanner.py', '.'),
    ('src/vt_incognito.py', '.'),
    ('src/vt_scrape.py', '.'),
]

# Adiciona clamav se existir (bundle)
if os.path.isdir(os.path.join(project_root, 'clamav')):
    datas.append(('clamav', 'clamav'))
else:
    print("AVISO: pasta clamav/ nao encontrada. Rode tools/install_clamav.ps1 antes do build")

if os.path.isdir(os.path.join(project_root, 'yara')):
    datas.append(('yara', 'yara'))
else:
    print("AVISO: pasta yara/ nao encontrada. Rode tools/install_yara.ps1 antes do build")

# Se tiver clamav/db, garante
if os.path.isdir(os.path.join(project_root, 'clamav', 'db')):
    # ja incluso via clamav
    pass

a = Analysis(
    ['src/main.py'],
    pathex=[project_root, os.path.join(project_root, 'src')],
    binaries=[],
    datas=datas,
    hiddenimports=['server', 'scanner', 'vt_incognito', 'vt_scrape'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Horash',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # True para ver logs; mude para False para janela sem console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='web/favicon.ico',
)

# Opcional: COLLECT para one-folder (descomente se preferir pasta ao inves de onefile)
# coll = COLLECT(
#     exe, a.binaries, a.zipfiles, a.datas,
#     strip=False, upx=True, upx_exclude=[], name='FileHasher'
# )
