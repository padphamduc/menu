# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

_datas = []
_binaries = []
_hiddenimports = []

_datas += [("assets/duc_logo.png", "assets"), ("assets/duc_logo.ico", "assets")]
_datas += [("tools", "tools_seed")]

for pkg in ["google.genai", "pydantic", "pyautogui", "keyboard", "colorama", "PIL", "pystray", "cv2", "requests", "py7zr"]:
    try:
        d, b, h = collect_all(pkg)
        _datas += d
        _binaries += b
        _hiddenimports += h
    except Exception:
        try:
            _hiddenimports += collect_submodules(pkg)
        except Exception:
            pass

# Common transitive packages used by google-genai/httpx/websocket paths.
for pkg in ["httpx", "httpcore", "anyio", "sniffio", "websockets", "google.auth", "certifi"]:
    try:
        _hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

a = Analysis(
    ["launcher_exe.py"],
    pathex=[],
    binaries=_binaries,
    datas=_datas,
    hiddenimports=list(dict.fromkeys(_hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DucTool",
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
    icon="assets/duc_logo.ico",
)
