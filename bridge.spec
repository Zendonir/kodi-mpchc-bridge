# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec — baut eine einzige bridge.exe (one-file, no console).
#
# Bauen:
#   pip install pyinstaller
#   pyinstaller bridge.spec
#
# Die fertige Datei liegt unter:  dist\bridge.exe

import sys
from PyInstaller.building.build_main import Analysis, PYZ, EXE

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=[
        # asyncio internals
        "asyncio",
        "asyncio.windows_events",
        # aiohttp
        "aiohttp",
        "aiohttp.connector",
        "aiohttp.client",
        "aiohttp.web",
        # yarl / multidict
        "yarl",
        "multidict",
        # bridge modules
        "bridge",
        "bridge.config",
        "bridge.hub",
        "bridge.kodi_client",
        "bridge.mpchc_client",
        "bridge.mkv_parser",
        "bridge.router",
        "bridge.server",
        "bridge.state",
        # GUI modules
        "gui",
        "service",
        "test_client",
        # tkinter (may need explicit inclusion on some systems)
        "tkinter",
        "tkinter.ttk",
        "tkinter.scrolledtext",
        "tkinter.messagebox",
        # Windows
        "winreg",
        "ctypes",
        "ctypes.wintypes",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pystray", "PIL", "Pillow"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="bridge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # Kein Konsolenfenster
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="bridge.ico",     # Optional: .ico Datei hier eintragen
    uac_admin=False,          # GUI startet ohne Admin; Admin nur für Firewall/Service via UAC
)
