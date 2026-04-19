# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec — baut ein onedir-Paket (dist\kodi-bridge\).
#
# Bauen:
#   pip install pyinstaller
#   pyinstaller bridge.spec
#
# Die fertigen Dateien liegen unter:  dist\kodi-bridge\*
# Der Installer kopiert dist\kodi-bridge\* → {app}\
#
# Warum onedir statt onefile?
#   onefile extrahiert bei jedem Start alle DLLs in einen neuen _MEI*-
#   Temp-Ordner.  Da die Bridge im Kiosk-Modus per "taskkill /f" abgewürgt
#   wird, räumt PyInstaller diesen Ordner nie auf → massenhaft _MEI*-Müll
#   in %LOCALAPPDATA%.  onedir legt alle Dateien einmalig beim Install ab
#   und braucht keinerlei Temp-Extraktion.

import sys
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

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
        "bridge.i18n",
        "bridge.kodi_client",
        "bridge.mpchc_client",
        "bridge.mkv_parser",
        "bridge.router",
        "bridge.server",
        "bridge.state",
        # GUI modules
        "gui",
        "service",
        # tkinter (may need explicit inclusion on some systems)
        "tkinter",
        "tkinter.ttk",
        "tkinter.scrolledtext",
        "tkinter.messagebox",
        # Pillow — cover art, tray icon
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageTk",
        "PIL.PngImagePlugin",
        "PIL.JpegImagePlugin",
        # pystray — system-tray icon
        "pystray",
        "pystray._util.win32",
        # Windows
        "winreg",
        "ctypes",
        "ctypes.wintypes",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],                      # binaries go into COLLECT, not into the exe
    exclude_binaries=True,   # onedir: DLLs liegen neben der .exe
    name="kodi-bridge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,           # kein Konsolenfenster
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="bridge.ico",     # Optional: .ico Datei hier eintragen
    uac_admin=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="kodi-bridge",      # → dist\kodi-bridge\
)
