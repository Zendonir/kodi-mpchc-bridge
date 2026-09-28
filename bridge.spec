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

#
# Virenscanner / Microsoft Defender
#   * upx=False — UPX-gepackte Binaries sind ein klassisches Fehlalarm-Muster.
#   * Versionsinfo + Icon — eine .exe ohne Herausgeber/Version wirkt verdächtig.
#   * Der Release-Workflow kompiliert zusätzlich den PyInstaller-Bootloader
#     selbst (PYINSTALLER_COMPILE_BOOTLOADER=1), statt den vorkompilierten zu
#     nutzen, den auch viel Schadsoftware verwendet.
#   Die Version kommt aus der Umgebungsvariable BRIDGE_VERSION (z. B. "1.2.3").

import os
import re
import sys
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

APP_NAME = "Kodi-MPC-HC Bridge"
APP_VERSION = os.environ.get("BRIDGE_VERSION", "0.0.0").strip() or "0.0.0"


def _version_tuple(version: str) -> tuple:
    """'1.2.3-dev-abc' → (1, 2, 3, 0) — Windows version resources are numeric."""
    nums = [int(n) for n in re.findall(r"\d+", version.split("-")[0])][:4]
    return tuple(nums + [0] * (4 - len(nums)))


def _version_info():
    """Windows version resource (Eigenschaften → Details der .exe)."""
    if sys.platform != "win32":
        return None
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable,
        VarFileInfo, VarStruct, VSVersionInfo,
    )
    vt = _version_tuple(APP_VERSION)
    return VSVersionInfo(
        ffi=FixedFileInfo(filevers=vt, prodvers=vt),
        kids=[
            StringFileInfo([StringTable("040904B0", [
                StringStruct("CompanyName", "kodi-mpchc-bridge"),
                StringStruct("FileDescription", f"{APP_NAME} — Kodi / MPC-HC remote control hub"),
                StringStruct("FileVersion", APP_VERSION),
                StringStruct("InternalName", "kodi-bridge"),
                StringStruct("LegalCopyright", "Zendonir — https://github.com/Zendonir/kodi-mpchc-bridge"),
                StringStruct("OriginalFilename", "kodi-bridge.exe"),
                StringStruct("ProductName", APP_NAME),
                StringStruct("ProductVersion", APP_VERSION),
            ])]),
            VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
        ],
    )


a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[('bridge/static', 'bridge/static')],
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
        "bridge.browse",
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
    upx=False,               # UPX löst Virenscanner-Fehlalarme aus
    upx_exclude=[],
    console=False,           # kein Konsolenfenster
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="bridge.ico",
    version=_version_info(),
    uac_admin=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,               # UPX löst Virenscanner-Fehlalarme aus
    upx_exclude=[],
    name="kodi-bridge",      # → dist\kodi-bridge\
)
