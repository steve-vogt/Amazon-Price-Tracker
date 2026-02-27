# -*- mode: python ; coding: utf-8 -*-
# amazon_tracker.spec — PyInstaller build config for Amazon Price Tracker V33
# Usage: pyinstaller amazon_tracker.spec --clean --noconfirm

block_cipher = None

a = Analysis(
    ['amazon_price_tracker.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'sqlalchemy',
        'sqlalchemy.orm',
        'sqlalchemy.ext.declarative',
        'flask',
        'flask.json',
        'jinja2',
        'jinja2.ext',
        'bs4',
        'requests',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'pystray',
        'pystray._win32',
        'greenlet',
        'email',
        'email.mime',
        'email.mime.text',
        'email.mime.multipart',
        'email.mime.image',
        'email.header',
        'email.utils',
        'imaplib',
        'smtplib',
        'sqlite3',
        'concurrent.futures',
        'asyncio',
        'logging',
        'webbrowser',
        'urllib.parse',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas'],
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
    a.datas,
    [],
    name='AmazonPriceTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # No console window — runs in system tray
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',               # App icon for the EXE
)
