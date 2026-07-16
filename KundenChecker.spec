# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
datas = [(str(root / "resources"), "resources")]
hiddenimports = [
    "openpyxl", "xlrd", "lxml", "bs4", "ddgs", "rapidfuzz", "certifi",
]

a = Analysis(
    [str(root / "app.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["playwright", "pytest", "_pytest", "sqlalchemy"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KundenChecker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
collection = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="KundenChecker",
)
app = BUNDLE(collection, name="KundenChecker.app", bundle_identifier="de.mssoftware.kundenchecker", info_plist={"CFBundleShortVersionString": "1.3.0", "CFBundleVersion": "1.3.0", "NSHighResolutionCapable": True})
