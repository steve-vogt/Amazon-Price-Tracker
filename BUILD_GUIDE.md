# Build Guide — Compiling the EXE

This is for building the Windows EXE yourself. If you just want to run the app, see [GETTING_STARTED.md](GETTING_STARTED.md).

## Prerequisites

- **Python 3.10+** installed with "Add to PATH" checked
- **Windows 10 or 11**

## Build Steps

### 1. Create a project folder

Create a folder (e.g. `C:\AmazonTracker`) and put these two files in it:
- `amazon_price_tracker.py`
- `amazon_tracker.spec`

### 2. Open Command Prompt in that folder

Open File Explorer, navigate to the folder, click the **address bar**, type `cmd`, press **Enter**.

### 3. Install build dependencies

```
pip install pyinstaller flask sqlalchemy beautifulsoup4 requests pystray Pillow
```

### 4. Build the EXE

```
pyinstaller amazon_tracker.spec --clean --noconfirm
```

Wait 1-2 minutes. Your EXE appears at: `dist\AmazonPriceTracker.exe`

### 5. Test it

Double-click `dist\AmazonPriceTracker.exe`. The orange tray icon should appear and your browser should open.

## Releasing a New Version

1. In `amazon_price_tracker.py`, bump the version number on the `APP_VERSION` line (e.g. `APP_VERSION = 34`)
2. Rebuild the EXE with the command above
3. On GitHub, go to **Releases** > **Create a new release**
4. Tag: `v34` (match the version number)
5. Drag the new EXE into "Attach binaries"
6. Click **Publish release**

Users running the old version will see an "Update available" banner on their dashboard.

## What the Spec File Does

`amazon_tracker.spec` tells PyInstaller:
- Bundle all Python dependencies into one EXE
- Set `console=False` so no command prompt window appears (runs in system tray)
- Exclude unnecessary libraries (tkinter, matplotlib, etc.) to keep the EXE smaller
- Include all required hidden imports for Flask, SQLAlchemy, pystray, etc.

## Notes

- The EXE automatically installs Playwright + Chromium on first run using the system Python
- The EXE size is roughly 30-50MB depending on your Python environment
- Antivirus software may flag PyInstaller EXEs — this is a known false positive
