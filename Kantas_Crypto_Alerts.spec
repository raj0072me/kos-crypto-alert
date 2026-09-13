# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

block_cipher = None

# Collect all necessary package resources
ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all('customtkinter')
mpf_datas, mpf_binaries, mpf_hiddenimports = collect_all('mplfinance')

datas = [
    ('assets', 'assets'),
    ('kos-crypto-alert-icon.png', '.'),
] + ctk_datas + mpf_datas

binaries = ctk_binaries + mpf_binaries

hiddenimports = [
    'plyer.platforms.win.notification',
    'PIL._tkinter_finder',
    'requests',
    'pygame',
    'pygame.mixer',
    'pandas',
    'matplotlib',
    'matplotlib.backends.backend_tkagg',
] + ctk_hiddenimports + mpf_hiddenimports

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['test.MD', 'update.MD'],
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
    name="Kantas_Crypto_Alerts",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI application, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/app_icon.ico',
)
