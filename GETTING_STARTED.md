# Getting Started — Amazon Price Tracker

Welcome! This guide walks you through everything from first launch to getting price drop alerts in your inbox.

## Step 1: Launch the App

**Windows EXE:** Double-click `AmazonPriceTracker.exe`. It appears in your system tray (orange box icon, bottom-right corner of your taskbar). Right-click the icon to open the dashboard or quit.

**Windows Python:** Double-click `amazon_price_tracker.py`. Everything installs automatically the first time.

**Mac:** Double-click `run_mac.command`. If it says "permission denied", open Terminal once and run: `chmod +x run_mac.command`

Your browser will open to the dashboard automatically. If it doesn't, go to **http://localhost:8088**

The very first launch takes 1-2 minutes to install the screenshot browser. You'll see the dashboard while this happens in the background. After the first time, the app starts in seconds.

## Step 2: Set Up Your Email

The app uses your Gmail to do two things: (1) read your Amazon order confirmation emails to find what you bought, and (2) send you price drop alert emails.

1. Click **Settings** in the top navigation bar
2. Fill in:
   - **Email Address:** Your Gmail address (e.g. `you@gmail.com`)
   - **Email Password:** A Gmail App Password (NOT your regular password — see below)
   - **SMTP Server:** `smtp.gmail.com` (already filled in)
   - **SMTP Port:** `587` (already filled in)
3. Click **Save**

### How to Create a Gmail App Password

1. Go to https://myaccount.google.com/apppasswords
2. You may need to sign in and have 2-Factor Authentication enabled
3. In the "App name" field, type `Price Tracker` and click **Create**
4. Google shows you a 16-character password (like `abcd efgh ijkl mnop`)
5. Copy that password and paste it into the **Email Password** field in Settings
6. Click **Send Test Email** to verify it works — you should get a test email in your inbox

### Enable IMAP in Gmail

The app needs IMAP access to read your Amazon order emails:

1. Go to https://mail.google.com/mail/u/0/#settings/fwdandpop
2. Under "IMAP access", select **Enable IMAP**
3. Click **Save Changes**

## Step 3: Import Your Amazon Orders

1. Go back to the **Dashboard** (click "Dashboard" in the nav bar)
2. Click the blue **Import Orders** button
3. The app scans your Gmail for Amazon order confirmation emails from the last 30 days
4. Each item found gets added to your tracker with the price you paid

Products show up as "Amazon Order Item B0XXXXX" at first. The title and current price update automatically on the next price check cycle (or click "Check Now" on any product).

### Auto-Import

In **Settings**, you can turn on **Auto-Import** so the app scans for new orders daily without you clicking anything.

## Step 4: Set Your Alert Thresholds

For each product on the dashboard, click **Alert Thresholds** to expand the settings:

- **New Price Drop %** — Get alerted if the new price drops by this percentage (e.g., 10%)
- **New Price Drop $** — Get alerted if the new price drops by this dollar amount (e.g., $5.00)
- **Used Price Drop %** and **$** — Same but for used/renewed listings
- **Target Price** — Get alerted when the price hits this specific number or lower

Leave any field blank to skip that alert type. All fields are optional.

### Global Thresholds

In **Settings**, you can enable **Global Thresholds** that apply the same % and $ rules to all products at once, overriding individual settings.

## Step 5: Let It Run

That's it! The app now runs in the background and:

- Checks prices every **2-4 hours** (randomized to avoid Amazon bot detection)
- Sends you email alerts when prices drop past your thresholds
- Scans for product recalls daily (CPSC + FDA databases)
- Auto-imports new orders daily (if enabled)

### Dashboard Features

- **Price history charts** — Each product shows a visual history of price changes
- **Screenshots** — Click "View Screenshots" to see what the Amazon page looked like at each check
- **Sort options** — Sort by name, price, drop %, date added, and more
- **Archive** — Products auto-archive after 35 days (configurable). View archived items in the Archive tab.

## Recall Monitoring

The app automatically scans the CPSC (Consumer Product Safety Commission) and FDA databases for recalls matching your products. If a recall is found:

- A red banner appears on the product card
- You get an email alert
- Click "Full Details" for the official recall page

If you've reviewed a recall and don't need the alert anymore, click **Dismiss**. Dismissed recalls won't notify you again.

## Updating the App

When a new version is available, a blue banner appears at the top of your dashboard with a link to download the update. Just replace the old EXE or .py file with the new one. Your database (`tracker.db`) and settings carry over automatically.

## Troubleshooting

**Dashboard won't open:** Try going to http://localhost:8088 manually in your browser.

**Import Orders finds nothing:** Make sure IMAP is enabled in Gmail settings and you're using an App Password (not your regular password). Check `import_log.txt` in the app folder for details.

**Price check shows errors:** Amazon occasionally triggers CAPTCHA/bot detection. The app randomizes timing to avoid this, but it can happen. It usually resolves on its own within a cycle or two.

**EXE flagged by antivirus:** Normal for PyInstaller-built EXEs. Add an exception in your antivirus software.

**Screenshots not appearing:** Screenshots require Playwright + Chromium, which install automatically on first launch. If they didn't install, check `tracker_setup.log` for details. Price tracking works without screenshots.

## Files Created by the App

The app creates these files in the same folder where it runs:

| File | Purpose |
|------|---------|
| `tracker.db` | Your database (products, settings, price history) |
| `tracker.log` | App activity log (when running as EXE) |
| `tracker_setup.log` | First-time setup log |
| `import_log.txt` | Email import activity log |
| `check_log.txt` | Price check activity log |
| `recall_log.txt` | Recall scan activity log |
| `static/screenshots/` | Product page screenshots |
| `.playwright_installed` | Marker file (first-time setup complete) |
| `.tracker.pid` | Prevents running two copies at once |

## Run at Windows Startup

In **Settings**, turn on **Run at Windows Startup**. The app will automatically start when you log into Windows, running silently in the system tray. Turn it off to remove it from startup.

## Privacy and Security

- The app runs **entirely on your local machine** — no data is sent to any server except Amazon (for price checks), CPSC/FDA (for recall scans), Gmail (for email import/alerts), and GitHub (for update checks)
- Your Gmail App Password is stored locally in `tracker.db` and never transmitted anywhere except to Gmail's SMTP/IMAP servers
- The dashboard is only accessible at `localhost` — not from other devices on your network
