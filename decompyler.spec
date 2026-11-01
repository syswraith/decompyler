# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect all PySide6 binaries, datas, and hidden imports
pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all('PySide6')

platform_name = sys.platform
if platform_name.startswith('win'):
    bin_folder = 'src/decompyler/bin/windows'
    dest_sub = 'decompyler/bin/windows'
    bin_names = ['pycdc.exe', 'pycdas.exe']
elif platform_name.startswith('darwin'):
    bin_folder = 'src/decompyler/bin/macos'
    dest_sub = 'decompyler/bin/macos'
    bin_names = ['pycdc', 'pycdas']
else:
    bin_folder = 'src/decompyler/bin/linux'
    dest_sub = 'decompyler/bin/linux'
    bin_names = ['pycdc', 'pycdas']

bundled_tools = [(f'{bin_folder}/{name}', dest_sub) for name in bin_names]

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=bundled_tools + pyside6_binaries,
    datas=[] + pyside6_datas,
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
