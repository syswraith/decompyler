# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Determine OS-specific binary folder to bundle
platform_name = sys.platform
if platform_name.startswith('win'):
    bin_folder = 'src/decompyler/bin/windows'
elif platform_name.startswith('darwin'):
    bin_folder = 'src/decompyler/bin/macos'
else:
    bin_folder = 'src/decompyler/bin/linux'

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[],
    datas=[(bin_folder, f'decompyler/bin/{platform_name.replace("win", "windows").replace("darwin", "macos").replace("linux", "linux")}')],
    hiddenimports=['pyinstxtractor_ng', 'pygments', 'pygments.lexers', 'pygments.styles'],
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
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True if you want a debug terminal window to stay open
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
