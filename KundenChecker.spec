# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

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
    excludes=["playwright"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="KundenChecker", debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False)
app = BUNDLE(exe, name="KundenChecker.app", bundle_identifier="de.mssoftware.kundenchecker", info_plist={"CFBundleShortVersionString": "1.0.0", "CFBundleVersion": "1.0.0", "NSHighResolutionCapable": True})
