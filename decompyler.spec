# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect all PySide6 binaries, datas, and hidden imports
pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all('PySide6')

icon_file = None
if sys.platform.startswith('win'):
    icon_file = 'assets/logo.ico'
elif sys.platform == 'darwin':
    icon_file = 'assets/logo.icns'

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=pyside6_binaries,
    datas=[('assets/logo-rounded.png', 'assets')] + pyside6_datas,
    hiddenimports=[
        'pyinstxtractor_ng',
        'Crypto.Cipher.AES',
        'Crypto.Util.Counter',
        'xdis.unmarshal',
        'pygments',
        'pygments.lexers',
        'pygments.styles',
    ] + pyside6_hiddenimports,
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
    name='decompyler',
    icon=icon_file,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
