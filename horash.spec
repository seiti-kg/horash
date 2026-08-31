# -*- mode: python ; coding: utf-8 -*-
# horash.spec - build leve (sem clamav/yara por padrao)
# uso: pyinstaller horash.spec  -> dist/horash.exe (~12mb, leve)
# offline: set HORASH_OFFLINE=1 & pyinstaller horash.spec -> dist/horash.exe com bundle

import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None
project_root = os.path.abspath(os.path.dirname(__name__) if '__name__' in globals() else os.getcwd())

# coleta tudo do pywebview (edgechromium, winforms, clr)
try:
    wv_datas, wv_binaries, wv_hidden = collect_all('webview')
    print(f"[*] pywebview collect: {len(wv_datas)} datas, {len(wv_binaries)} binaries")
except Exception as e:
    print(f"[!] collect_all webview falhou: {e}")
    wv_datas, wv_binaries, wv_hidden = [], [], []

datas = [
    ('web/index.html', '.'),
    ('web/style.css', '.'),
    ('web/app.js', '.'),
    ('web/sha256.min.js', '.'),
    ('web/favicon.ico', '.'),
    ('web/favicon.png', '.'),
    ('web/favicon-32.png', '.'),
    ('src/server.py', '.'),
    ('src/scanner.py', '.'),
    ('src/vt_incognito.py', '.'),
    ('src/vt_scrape.py', '.'),
]

# so embute engines se HORASH_OFFLINE=1 (para horash_setup_offline)
if os.environ.get('HORASH_OFFLINE') == '1':
    if os.path.isdir(os.path.join(project_root, 'clamav')):
        datas.append(('clamav', 'clamav'))
        print("[*] bundle clamav/ incluido (offline)")
    else:
        print("[!] HORASH_OFFLINE=1 mas clamav/ nao encontrado - rode tools/install_clamav.ps1")
    if os.path.isdir(os.path.join(project_root, 'yara')):
        datas.append(('yara', 'yara'))
        print("[*] bundle yara/ incluido (offline)")
    else:
        print("[!] HORASH_OFFLINE=1 mas yara/ nao encontrado - rode tools/install_yara.ps1")
else:
    print("[*] build leve - clamav/yara nao embutidos (setup baixa depois)")

a = Analysis(
    ['src/main.py'],
    pathex=[project_root, os.path.join(project_root, 'src')],
    binaries=wv_binaries,
    datas=datas + wv_datas,
    hiddenimports=['server', 'scanner', 'vt_incognito', 'vt_scrape'] + wv_hidden,
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
    name='horash',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='web/favicon.ico',
)
