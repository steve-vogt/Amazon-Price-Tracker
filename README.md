# Amazon Price Tracker

Automatically monitors Amazon prices on items you've purchased and alerts you when prices drop so you can request a price adjustment or time your next buy.

## What It Does

- **Auto-imports orders from Gmail** - Scans your Amazon order confirmation emails and adds items to tracking automatically
- **Tracks new and used prices** - Checks both new and used/renewed prices on Amazon
- **Email alerts** - Sends you an email when prices drop below your thresholds
- **Recall monitoring** - Scans CPSC and FDA databases for product recalls on everything you've purchased
- **Per-product or global thresholds** - Set alert rules per item (% drop, $ drop, target price) or apply global thresholds
- **Screenshots** - Captures Amazon product page screenshots with each price check (requires Playwright)
- **Auto-update notifications** - Dashboard shows a banner when a newer version is available
- **Run at startup** - Toggle in Settings to auto-launch when Windows boots (system tray, no console window)

## Quick Start

### Windows (EXE)

1. Download `AmazonPriceTracker.exe` from the [latest release](https://github.com/steve-vogt/amazon-price-tracker/releases/latest)
2. Double-click to run
3. The app appears in your **system tray** (orange box icon, bottom-right of taskbar)
4. Your browser opens to the dashboard automatically

First launch takes 1-2 minutes to set up Playwright (screenshot support). After that it starts instantly.

### Windows (Python script)

1. Make sure [Python 3](https://www.python.org/downloads/) is installed (check "Add to PATH" during install)
2. Download `amazon_price_tracker.py`
3. Double-click it - all dependencies install automatically on first run

### Mac

1. Download `amazon_price_tracker.py` and `run_mac.command`
2. Open Terminal and run: `chmod +x run_mac.command`
3. Double-click `run_mac.command` in Finder

## Setup (First Time)

Once the dashboard opens:

1. Click **Settings** in the nav bar
2. Enter your **Gmail address** and a [Gmail App Password](https://myaccount.google.com/apppasswords)
3. Set SMTP to `smtp.gmail.com` port `587` (pre-filled)
4. Click **Save**
5. Click **Import Orders** on the dashboard to pull in your Amazon purchases
6. The app will check prices automatically every 2-4 hours (randomized to avoid detection)

## How Alerts Work

You can set thresholds per product or globally:

- **% drop** - Alert when price drops by this percentage from what you paid
- **$ drop** - Alert when price drops by this dollar amount
- **Target price** - Alert when price falls to or below this amount

Alerts are sent as emails with the product name, old price, new price, percentage change, Amazon link, and optional screenshots.

## Files

| File | What It Is |
|------|------------|
| `amazon_price_tracker.py` | The application (run directly or build into EXE) |
| `amazon_tracker.spec` | PyInstaller config for building the Windows EXE |
| `run_mac.command` | Double-clickable Mac launcher |
| `GETTING_STARTED.md` | Detailed user guide |
| `BUILD_GUIDE.md` | How to build the EXE yourself |
| `app_icon.ico` | Application icon (used by the EXE and system tray) |

## Building the EXE Yourself

See [BUILD_GUIDE.md](BUILD_GUIDE.md) for step-by-step instructions.

Quick version

pip install pyinstaller flask sqlalchemy beautifulsoup4 requests pystray Pillow
pyinstaller amazon_tracker.spec --clean --noconfirm

Your EXE appears in `dist/AmazonPriceTracker.exe`.

## Requirements

- **Python 3.10+** (for running the .py script or building the EXE)
- **Gmail account** with an [App Password](https://myaccount.google.com/apppasswords) (for email import and alerts)
- **IMAP enabled** in Gmail settings

The app auto-installs all Python dependencies on first run. No manual pip commands needed.

## 💝 Support

If this tool saves you money, consider buying me a coffee!

[![Cash App](https://img.shields.io/badge/Cash_App-$SteveVogt-00D632?style=for-the-badge)](https://cash.app/$SteveVogt)
[![PayPal](https://img.shields.io/badge/PayPal-SteveVogt-0070BA?style=for-the-badge)](https://paypal.me/SteveVogt)
[![Venmo](https://img.shields.io/badge/Venmo-SteveVogt-008CFF?style=for-the-badge)](https://venmo.com/u/SteveVogt)

<details>
<summary>Bitcoin</summary>

`bc1qpdex8jrvyj3lh7q56av2k53nrh7u63s6t65uer`

</details>

## License

Personal use. Not affiliated with Amazon.
