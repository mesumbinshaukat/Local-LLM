# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['MeAI_app.py'],
    pathex=[],
    binaries=[],
    datas=[('models', 'models'), ('knowledge', 'knowledge'), ('plugins', 'plugins')],
    hiddenimports=['PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'requests', 'llama_cpp', 'chromadb', 'fastapi', 'uvicorn', 'rich', 'typer', 'pyttsx3', 'vosk', 'duckduckgo_search'],
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
    name='MeAI',
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
)
