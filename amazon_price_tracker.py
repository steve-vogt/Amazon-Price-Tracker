# amazon_price_tracker.py - V33 (EXE Packaging Fix)
#
# ZERO-SETUP: Just run this file. It auto-installs everything it needs.
#   Windows: Double-click this file (or run: python amazon_price_tracker.py)
#   Mac/Linux: Run: python3 amazon_price_tracker.py

import os, sys, subprocess

# ============================================================
# AUTO-INSTALLER — Runs once on first launch, then skips
# Only runs when launched as a .py script (not as a frozen EXE)
# ============================================================
# AUTO-INSTALLER — Ensures Playwright + Chromium are available
# Works from both .py scripts AND frozen EXEs
# ============================================================
_SETUP_MARKER = '.playwright_installed'

def _ensure_dependencies():
    """Check for and install all required packages automatically."""
    is_frozen = getattr(sys, 'frozen', False)
    
    # For .py mode: install missing pip packages
    if not is_frozen:
        required = {
            'flask': 'flask',
            'sqlalchemy': 'sqlalchemy',
            'bs4': 'beautifulsoup4',
            'requests': 'requests',
            'pystray': 'pystray',
            'PIL': 'Pillow',
        }
        missing = []
        for import_name, pip_name in required.items():
            try:
                __import__(import_name)
            except ImportError:
                missing.append(pip_name)
        
        if missing:
            _safe_print(f"[Setup] Installing {', '.join(missing)}...")
            try:
                subprocess.check_call(
                    [sys.executable, '-m', 'pip', 'install', '--quiet'] + missing,
                    stdout=subprocess.DEVNULL if len(missing) < 3 else None
                )
            except subprocess.CalledProcessError:
                try:
                    subprocess.check_call(
                        [sys.executable, '-m', 'pip', 'install', '--user', '--quiet'] + missing
                    )
                except subprocess.CalledProcessError:
                    _safe_print(f"[Setup] ERROR: pip install failed. Run: pip install {' '.join(missing)}")
                    sys.exit(1)
    
    # For BOTH .py and EXE: ensure Playwright + Chromium are installed
    # Skip if we already did this successfully (marker file)
    if os.path.exists(_SETUP_MARKER):
        return
    
    _install_playwright(is_frozen)

def _install_playwright(is_frozen):
    """Install Playwright + Chromium browser. Works from .py or EXE."""
    # Find a working Python executable on the system
    python_cmd = _find_system_python()
    
    if not python_cmd:
        _log_setup("No system Python found - screenshots will use requests fallback")
        return
    
    # Step 1: Ensure playwright pip package is installed
    try:
        subprocess.run(
            [python_cmd, '-c', 'import playwright'],
            capture_output=True, timeout=10
        ).check_returncode()
    except Exception:
        _log_setup("Installing Playwright package...")
        try:
            subprocess.run(
                [python_cmd, '-m', 'pip', 'install', 'playwright'],
                capture_output=True, timeout=120
            ).check_returncode()
            _log_setup("Playwright package installed.")
        except Exception:
            _log_setup("Could not install Playwright - screenshots will use requests fallback")
            return
    
    # Step 2: Ensure Chromium browser is installed
    try:
        subprocess.run(
            [python_cmd, '-c', 
             'from playwright.sync_api import sync_playwright\n'
             'with sync_playwright() as p:\n'
             '  b = p.chromium.launch(headless=True)\n'
             '  b.close()'],
            capture_output=True, timeout=30
        ).check_returncode()
        _log_setup("Playwright + Chromium verified.")
    except Exception:
        _log_setup("Installing Chromium browser (one-time, takes ~1-2 minutes)...")
        try:
            subprocess.run(
                [python_cmd, '-m', 'playwright', 'install', 'chromium'],
                capture_output=True, timeout=300
            ).check_returncode()
            _log_setup("Chromium browser installed!")
        except Exception:
            _log_setup("Chromium install failed - screenshots will use requests fallback")
            return
    
    # Mark as done so we don't re-check every launch
    try:
        with open(_SETUP_MARKER, 'w') as f:
            f.write('ok')
    except Exception:
        pass

def _find_system_python():
    """Find a working Python 3 executable on the system PATH."""
    import shutil
    # Try common names in order of preference
    for name in ['python', 'python3', 'py']:
        path = shutil.which(name)
        if path:
            try:
                result = subprocess.run(
                    [path, '--version'], capture_output=True, timeout=5, text=True
                )
                if result.returncode == 0 and 'Python 3' in result.stdout:
                    return path
            except Exception:
                continue
    # If running as .py, sys.executable is always valid
    if not getattr(sys, 'frozen', False):
        return sys.executable
    return None

def _log_setup(msg):
    """Log setup messages to file (safe for windowless EXE)."""
    try:
        with open('tracker_setup.log', 'a', encoding='utf-8') as f:
            f.write(f"[{__import__('datetime').datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
    except Exception:
        pass
    _safe_print(f"[Setup] {msg}")

def _safe_print(msg):
    """Print that won't crash on Windows with encoding issues."""
    try:
        print(msg)
    except (UnicodeEncodeError, OSError):
        try:
            print(msg.encode('ascii', errors='replace').decode('ascii'))
        except Exception:
            pass  # Truly can't print — running as silent EXE, that's fine

if __name__ == "__main__":
    _ensure_dependencies()

# ============================================================
# IMPORTS (all safe now — dependencies guaranteed above)
# ============================================================
import time, random, threading, smtplib, re, signal, logging, json, asyncio, sqlite3, webbrowser, imaplib, requests
import email as email_lib  # Renamed to avoid conflicts
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta
from contextlib import contextmanager
from urllib.parse import unquote, quote
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from flask import Flask, render_template_string, request, redirect, flash, send_from_directory, jsonify
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from bs4 import BeautifulSoup

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from pystray import Icon, Menu, MenuItem
    from PIL import Image, ImageDraw, ImageFont
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

DB_NAME = 'tracker.db'
APP_VERSION = 33
GITHUB_REPO = 'steve-vogt/amazon-price-tracker'
TITLE_MAX_LENGTH = 77
ALERT_COOLDOWN_HOURS = 12
DEFAULT_EXPIRATION_DAYS = 35
MAX_PRICE_HISTORY = 90
SCRAPE_TIMEOUT = 90
DEFAULT_INTERVAL_MINUTES = 180
INTERVAL_JITTER_MINUTES = 45
DEFAULT_PORT = 8088  # Avoids macOS AirPlay conflict on port 5000
PID_FILE = '.tracker.pid'
APP_NAME = 'amazon-tracker'  # Used for friendly URL

# Safe logging setup — writes to file when running as EXE (no console available)
if getattr(sys, 'frozen', False):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        filename='tracker.log', filemode='a', encoding='utf-8')
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=2)

# ============================================================
# UPDATE CHECKER — Checks GitHub for newer versions
# ============================================================
_latest_version_cache = {'version': None, 'url': None, 'checked': None}

def check_for_updates():
    """Check GitHub for a newer version. Returns (latest_version, download_url) or (None, None)."""
    if not GITHUB_REPO:
        return None, None
    # Only check once per day
    if _latest_version_cache['checked'] and (datetime.now() - _latest_version_cache['checked']).total_seconds() < 86400:
        return _latest_version_cache['version'], _latest_version_cache['url']
    try:
        resp = requests.get(
            f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest',
            timeout=10,
            headers={'Accept': 'application/vnd.github.v3+json'}
        )
        if resp.status_code == 200:
            data = resp.json()
            tag = data.get('tag_name', '').lstrip('vV')
            try:
                remote_ver = int(tag)
            except ValueError:
                remote_ver = 0
            url = data.get('html_url', f'https://github.com/{GITHUB_REPO}/releases/latest')
            _latest_version_cache['version'] = remote_ver
            _latest_version_cache['url'] = url
            _latest_version_cache['checked'] = datetime.now()
            if remote_ver > APP_VERSION:
                logger.info(f"Update available: v{remote_ver} (current: v{APP_VERSION})")
                return remote_ver, url
    except Exception:
        pass  # Silently fail — update checks are optional
    _latest_version_cache['checked'] = datetime.now()
    return None, None

def migrate_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    settings_columns = [
        ('email_address', 'TEXT', '""'),
        ('email_password', 'TEXT', '""'),
        ('smtp_server', 'TEXT', '"smtp.gmail.com"'),
        ('smtp_port', 'INTEGER', '587'),
        ('default_expiration_days', 'INTEGER', '35'),
        ('auto_archive', 'BOOLEAN', '1'),
        ('check_interval_minutes', 'INTEGER', str(DEFAULT_INTERVAL_MINUTES)),
        ('auto_import_orders', 'BOOLEAN', '1'),
        ('import_frequency', 'TEXT', '"every_12h"'),
        ('last_email_scan', 'DATETIME', 'NULL'),
        ('global_alerts_enabled', 'BOOLEAN', '0'),
        ('global_new_pct', 'REAL', 'NULL'),
        ('global_used_pct', 'REAL', 'NULL'),
        ('global_new_dollars', 'REAL', 'NULL'),
        ('global_used_dollars', 'REAL', 'NULL'),
        ('batch_email_alerts', 'BOOLEAN', '0'),
        ('recall_scan_enabled', 'BOOLEAN', '1'),
        ('recall_scan_frequency', 'TEXT', '"daily"'),
        ('last_recall_scan', 'DATETIME', 'NULL'),
        ('run_at_startup', 'BOOLEAN', '0'),
    ]
    
    products_columns = [
        ('asin', 'TEXT', '""'),
        ('title', 'TEXT', '""'),
        ('url', 'TEXT', '""'),
        ('screenshot_main', 'TEXT', 'NULL'),
        ('screenshot_offers', 'TEXT', 'NULL'),
        ('target_price', 'REAL', 'NULL'),
        ('current_new_price', 'REAL', 'NULL'),
        ('current_used_price', 'REAL', 'NULL'),
        ('prev_new_price', 'REAL', '0.0'),
        ('prev_used_price', 'REAL', '0.0'),
        ('lowest_new_price', 'REAL', 'NULL'),
        ('highest_new_price', 'REAL', 'NULL'),
        ('lowest_used_price', 'REAL', 'NULL'),
        ('highest_used_price', 'REAL', 'NULL'),
        ('price_history_json', 'TEXT', '"[]"'),
        ('created_at', 'DATETIME', 'NULL'),
        ('expires_at', 'DATETIME', 'NULL'),
        ('last_checked', 'DATETIME', 'NULL'),
        ('last_alert_sent', 'DATETIME', 'NULL'),
        ('archived_at', 'DATETIME', 'NULL'),
        ('is_active', 'BOOLEAN', '1'),
        ('is_archived', 'BOOLEAN', '0'),
        ('source', 'TEXT', '""'),
        ('alert_new_pct', 'REAL', 'NULL'),
        ('alert_new_dollars', 'REAL', 'NULL'),
        ('alert_used_pct', 'REAL', 'NULL'),
        ('alert_used_dollars', 'REAL', 'NULL'),
        ('order_date', 'DATETIME', 'NULL'),
        ('order_id', 'TEXT', 'NULL'),
        ('purchase_price', 'REAL', 'NULL'),
        ('recall_status', 'TEXT', '"none"'),
        ('recall_id', 'INTEGER', 'NULL'),
        ('recall_number', 'TEXT', 'NULL'),
        ('recall_title', 'TEXT', 'NULL'),
        ('recall_description', 'TEXT', 'NULL'),
        ('recall_url', 'TEXT', 'NULL'),
        ('recall_hazard', 'TEXT', 'NULL'),
        ('recall_remedy', 'TEXT', 'NULL'),
        ('recall_date', 'TEXT', 'NULL'),
        ('recall_consumer_contact', 'TEXT', 'NULL'),
        ('last_recall_check', 'DATETIME', 'NULL'),
    ]
    
    def add_missing_columns(table_name, columns):
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing = {row[1] for row in cursor.fetchall()}
        for col_name, col_type, default in columns:
            if col_name not in existing:
                try:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} DEFAULT {default}")
                    logger.info(f"Migration: Added {table_name}.{col_name}")
                except: pass
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
    if cursor.fetchone(): add_missing_columns('settings', settings_columns)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
    if cursor.fetchone(): add_missing_columns('products', products_columns)
    
    # V25 migration: Fix expiration dates for email imports (runs once)
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations'")
        if not cursor.fetchone():
            cursor.execute("CREATE TABLE _migrations (name TEXT PRIMARY KEY, applied_at TEXT)")
        cursor.execute("SELECT 1 FROM _migrations WHERE name='v25_fix_expiration'")
        if not cursor.fetchone():
            cursor.execute("SELECT default_expiration_days FROM settings LIMIT 1")
            row = cursor.fetchone()
            exp_days = row[0] if row else DEFAULT_EXPIRATION_DAYS
            if exp_days and exp_days > 0:
                cursor.execute("""
                    UPDATE products 
                    SET expires_at = datetime(order_date, '+' || ? || ' days')
                    WHERE source = 'email' AND order_date IS NOT NULL AND is_archived = 0
                """, (exp_days,))
                if cursor.rowcount > 0:
                    logger.info(f"Migration V25: Recalculated expiration for {cursor.rowcount} email-imported products (order_date + {exp_days}d)")
            cursor.execute("INSERT INTO _migrations VALUES ('v25_fix_expiration', ?)", (datetime.now().isoformat(),))
    except Exception as e:
        logger.warning(f"Migration note: {e}")
    
    conn.commit()
    conn.close()

LAYOUT_TPL = """
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Amazon Price Tracker</title>
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect x='6' y='22' width='52' height='36' rx='4' fill='%23e87400'/><rect x='6' y='22' width='52' height='36' rx='4' fill='none' stroke='%23b35900' stroke-width='2'/><path d='M20 22V14a12 12 0 0 1 24 0v8' fill='none' stroke='%23b35900' stroke-width='3' stroke-linecap='round'/><rect x='22' y='32' width='20' height='4' rx='2' fill='white' opacity='0.6'/><rect x='28' y='28' width='8' height='12' rx='2' fill='white' opacity='0.4'/><text x='32' y='50' text-anchor='middle' font-size='12' fill='white' font-weight='bold'>$</text></svg>">
    <link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root{--bg:#fafbfc;--text:#1a1d21;--card:#ffffff;--border:#e1e4e8;--accent:#e87400;--accent-glow:rgba(232,116,0,0.12);--success:#1a7f37;--danger:#cf222e;--warning:#bf8700;--info:#0969da;--muted:#656d76;--surface:#f6f8fa;--shadow:0 1px 3px rgba(0,0,0,0.06),0 1px 2px rgba(0,0,0,0.04);--shadow-lg:0 4px 24px rgba(0,0,0,0.08);--radius:12px;--radius-sm:8px}
        [data-theme="dark"]{--bg:#0d1117;--text:#e6edf3;--card:#161b22;--border:#30363d;--accent:#f0883e;--accent-glow:rgba(240,136,62,0.1);--success:#3fb950;--danger:#f85149;--warning:#d29922;--info:#58a6ff;--muted:#7d8590;--surface:#21262d;--shadow:0 1px 3px rgba(0,0,0,0.25);--shadow-lg:0 8px 32px rgba(0,0,0,0.35)}
        *{box-sizing:border-box;margin:0;padding:0}
        body{background:var(--bg);color:var(--text);font-family:'DM Sans',system-ui,-apple-system,sans-serif;line-height:1.6;min-height:100vh}
        .app-container{max-width:1400px;margin:0 auto;padding:0 24px 40px}
        /* ─── Navigation ─── */
        .nav{display:flex;justify-content:space-between;align-items:center;padding:16px 24px;margin:0 -24px 28px;border-bottom:1px solid var(--border);background:var(--card);position:sticky;top:0;z-index:50;backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
        .nav-brand{font-size:1.15em;font-weight:700;color:var(--text);display:flex;align-items:center;gap:10px;letter-spacing:-0.02em}
        .nav-brand .brand-icon{width:32px;height:32px;background:linear-gradient(135deg,var(--accent),#ff6b00);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:0.85em;box-shadow:0 2px 8px rgba(232,116,0,0.3)}
        .nav-links{display:flex;align-items:center;gap:4px}
        .nav a{color:var(--muted);text-decoration:none;font-weight:500;font-size:0.9em;padding:6px 14px;border-radius:var(--radius-sm);transition:all 0.15s ease}
        .nav a:hover{color:var(--text);background:var(--surface)}.nav a.active{color:var(--accent);background:var(--accent-glow);font-weight:600}
        .theme-toggle{width:34px;height:34px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--surface);color:var(--muted);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:1em;transition:all 0.15s ease;margin-left:8px}.theme-toggle:hover{border-color:var(--accent);color:var(--accent)}
        /* ─── Buttons ─── */
        .btn{padding:8px 16px;cursor:pointer;border-radius:var(--radius-sm);border:1px solid transparent;font-weight:600;font-size:0.85em;transition:all 0.15s ease;display:inline-flex;align-items:center;gap:6px;font-family:inherit;letter-spacing:-0.01em}
        .btn:hover{transform:translateY(-1px);box-shadow:var(--shadow)}.btn:active{transform:translateY(0)}.btn:disabled{opacity:0.5;cursor:not-allowed;transform:none;box-shadow:none}
        .btn-primary{background:var(--accent);color:#fff;border-color:var(--accent)}.btn-primary:hover{box-shadow:0 4px 12px rgba(232,116,0,0.35)}
        .btn-secondary{background:var(--surface);color:var(--text);border-color:var(--border)}.btn-secondary:hover{border-color:var(--accent);color:var(--accent)}
        .btn-danger{background:var(--danger);color:#fff}.btn-success{background:var(--success);color:#fff}
        .btn-sm{padding:6px 12px;font-size:0.8em;border-radius:6px}.btn-info{background:var(--info);color:#fff}
        /* ─── Forms ─── */
        input,textarea,select{background:var(--surface);color:var(--text);border:1px solid var(--border);padding:10px 14px;border-radius:var(--radius-sm);width:100%;font-size:0.9em;font-family:inherit;transition:border-color 0.15s ease}
        input:focus,textarea:focus,select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-glow)}
        /* ─── Cards ─── */
        .card{background:var(--card);border:1px solid var(--border);padding:22px;border-radius:var(--radius);margin-bottom:20px;box-shadow:var(--shadow);transition:box-shadow 0.2s ease}
        .card:hover{box-shadow:var(--shadow-lg)}
        .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:20px}
        /* ─── Stats ─── */
        .stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:24px}
        .stat-card{background:var(--card);border:1px solid var(--border);padding:16px 14px;border-radius:var(--radius);text-align:center;box-shadow:var(--shadow);transition:all 0.2s ease}
        .stat-card:hover{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}
        .stat-value{font-size:1.75em;font-weight:700;color:var(--accent);font-family:'JetBrains Mono','DM Sans',monospace;letter-spacing:-0.03em}.stat-label{font-size:0.8em;color:var(--muted);margin-top:4px;font-weight:500}
        /* ─── Product Cards ─── */
        .price-display{font-size:1.4em;font-weight:700;font-family:'JetBrains Mono','DM Sans',monospace;letter-spacing:-0.02em}.price-new{color:var(--text)}.price-used{color:var(--info)}.price-hit{color:var(--success)!important}.price-na{color:var(--muted);font-size:0.9em;font-family:'DM Sans',sans-serif}
        .badge{display:inline-flex;align-items:center;padding:3px 10px;border-radius:20px;font-size:0.72em;font-weight:600;letter-spacing:0.02em}
        .badge-success{background:rgba(26,127,55,0.12);color:var(--success)}.badge-warning{background:rgba(191,135,0,0.12);color:var(--warning)}.badge-danger{background:rgba(207,34,46,0.12);color:var(--danger)}.badge-info{background:rgba(9,105,218,0.12);color:var(--info)}.badge-muted{background:var(--surface);color:var(--muted)}
        .product-card{position:relative;transition:transform 0.15s ease}.product-card:hover{transform:translateY(-2px)}
        .product-topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--border)}
        .product-title{font-weight:600;height:42px;overflow:hidden;line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;font-size:0.95em}
        .product-title a{color:var(--text);text-decoration:none;transition:color 0.15s}.product-title a:hover{color:var(--accent)}
        .product-meta{display:flex;justify-content:space-between;align-items:center;font-size:0.8em;color:var(--muted);margin-top:12px;padding-top:12px;border-top:1px solid var(--border)}
        .prices-row{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:14px 0}
        .price-col label{font-size:0.7em;color:var(--muted);text-transform:uppercase;letter-spacing:0.08em;font-weight:600}
        .actions-row{display:flex;gap:8px;margin-top:14px;padding-top:14px;border-top:1px solid var(--border)}.actions-row .btn{flex:1;justify-content:center}
        .delete-btn{background:transparent;color:var(--muted);border:1px solid var(--border);border-radius:6px;width:28px;height:28px;cursor:pointer;font-size:14px;font-weight:bold;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:all 0.15s}
        .delete-btn:hover{background:var(--danger);color:#fff;border-color:var(--danger)}
        /* ─── Flash Messages ─── */
        .flash{padding:12px 18px;margin-bottom:16px;border-radius:var(--radius-sm);font-size:0.9em;font-weight:500;animation:slideDown 0.3s ease}
        @keyframes slideDown{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
        .flash.success{background:rgba(26,127,55,0.1);border:1px solid rgba(26,127,55,0.25);color:var(--success)}.flash.error{background:rgba(207,34,46,0.1);border:1px solid rgba(207,34,46,0.25);color:var(--danger)}
        /* ─── Loading ─── */
        .loader{border:2px solid var(--border);border-top:2px solid var(--accent);border-radius:50%;width:14px;height:14px;animation:spin 0.8s linear infinite;display:inline-block}
        @keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
        /* ─── Section Headers ─── */
        .section-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;flex-wrap:wrap;gap:10px}.section-header h2{margin:0;font-size:1.15em;font-weight:700;letter-spacing:-0.02em}
        .empty-state{text-align:center;padding:48px 24px;color:var(--muted)}.empty-state-icon{font-size:3em;margin-bottom:12px}
        /* ─── Price History ─── */
        .history-row{display:flex;justify-content:space-between;font-size:0.72em;padding:2px 0;color:var(--muted);font-family:'JetBrains Mono','DM Sans',monospace}.history-row .low{color:var(--success)}.history-row .high{color:var(--danger)}
        .drop-indicator{font-size:0.78em;color:var(--success);font-weight:600;margin-top:3px}.up-indicator{font-size:0.78em;color:var(--danger);font-weight:500;margin-top:3px}
        .global-override-notice{background:rgba(191,135,0,0.1);color:var(--warning);padding:10px 14px;border-radius:var(--radius-sm);font-size:0.85em;margin-bottom:12px;display:flex;align-items:center;gap:8px;border:1px solid rgba(191,135,0,0.2)}
        .price-chart{margin-top:14px;padding:14px;background:var(--surface);border-radius:var(--radius-sm);border:1px solid var(--border)}
        .chart-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
        .chart-title{font-size:0.72em;color:var(--muted);text-transform:uppercase;letter-spacing:0.08em;font-weight:600}
        .screenshot-btn{background:var(--surface);color:var(--info);border:1px solid var(--border);padding:4px 10px;border-radius:6px;font-size:0.72em;cursor:pointer;display:flex;align-items:center;gap:5px;font-weight:600;transition:all 0.15s}
        .screenshot-btn:hover{border-color:var(--info);background:rgba(9,105,218,0.08)}
        .chart-wrapper{position:relative;height:60px;display:flex;align-items:flex-end;gap:2px;padding:0 28px}
        .chart-bar{flex:1;min-width:4px;max-width:14px;border-radius:3px 3px 0 0;cursor:pointer;transition:opacity 0.15s}
        .chart-bar:hover{opacity:0.75}
        .chart-bar.new{background:linear-gradient(to top,var(--accent),rgba(240,136,62,0.6))}.chart-bar.used{background:linear-gradient(to top,var(--info),rgba(88,166,255,0.6))}
        .chart-y-axis{position:absolute;left:0;top:0;bottom:0;width:26px;display:flex;flex-direction:column;justify-content:space-between;font-size:0.55em;color:var(--muted);text-align:right;padding-right:4px;font-family:'JetBrains Mono',monospace}
        .chart-baseline{position:absolute;bottom:0;left:28px;right:0;height:1px;background:var(--border)}
        .chart-legend{display:flex;gap:15px;margin-top:8px;font-size:0.68em;justify-content:center;color:var(--muted)}
        .chart-legend span{display:flex;align-items:center;gap:4px}.chart-legend .dot{width:8px;height:8px;border-radius:2px}.chart-legend .dot.new{background:var(--accent)}.chart-legend .dot.used{background:var(--info)}
        .no-chart{height:60px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:0.85em}
        .check-status{font-size:0.85em;padding:10px;margin-top:12px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);display:none;text-align:center}
        .check-status.show{display:block}.check-status.checking{color:var(--info);border-color:var(--info)}.check-status.success{color:var(--success);border-color:var(--success)}.check-status.error{color:var(--danger);border-color:var(--danger)}
        /* ─── Modals ─── */
        .modal{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.88);backdrop-filter:blur(4px);z-index:1000;padding:20px;overflow-y:auto}
        .modal.show{display:flex;align-items:flex-start;justify-content:center}
        .modal-close{position:fixed;top:15px;right:20px;font-size:2.5em;color:#fff;cursor:pointer;z-index:1001;line-height:1;opacity:0.7;transition:opacity 0.15s}.modal-close:hover{opacity:1}
        .modal-content{max-width:1200px;margin:40px auto;padding:20px}
        .modal-content img{max-width:100%;border:2px solid rgba(255,255,255,0.1);border-radius:var(--radius);margin-bottom:20px}
        .modal-content h3{color:#fff;margin-bottom:25px;font-size:1.3em}.modal-content h4{color:var(--accent);margin:25px 0 12px;font-size:1em}
        /* ─── Tooltips & Settings ─── */
        .info-icon{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:var(--info);color:#fff;font-size:0.6em;font-weight:bold;cursor:help;margin-left:4px;flex-shrink:0}
        .tooltip{position:relative;display:inline-block}
        .tooltip .tooltip-text{visibility:hidden;width:280px;background:var(--card);color:var(--text);text-align:left;border-radius:var(--radius-sm);padding:12px 14px;position:absolute;z-index:100;bottom:125%;left:50%;margin-left:-140px;opacity:0;transition:opacity 0.2s;font-size:0.85em;line-height:1.4;border:1px solid var(--border);box-shadow:var(--shadow-lg)}
        .tooltip:hover .tooltip-text{visibility:visible;opacity:1}
        .product-settings{display:none;margin-top:14px;padding:16px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm)}
        .product-settings.show{display:block}
        .product-settings h4{margin:0 0 14px 0;font-size:0.9em;color:var(--accent);display:flex;align-items:center;gap:6px;font-weight:600}
        .threshold-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
        .threshold-group{margin-bottom:10px}
        .threshold-group label{font-size:0.72em;color:var(--muted);display:flex;align-items:center;gap:4px;margin-bottom:5px;font-weight:600;text-transform:uppercase;letter-spacing:0.04em}
        .threshold-inputs{display:flex;gap:8px}
        .threshold-inputs input{flex:1;min-width:0;padding:8px 10px;font-size:0.85em}
        .threshold-inputs input::placeholder{font-size:0.85em;opacity:0.5}
        .settings-note{font-size:0.75em;color:var(--muted);margin-top:12px;font-style:italic}
        .settings-toggle{background:var(--surface);border:1px solid var(--border);color:var(--muted);padding:4px 10px;border-radius:6px;font-size:0.72em;cursor:pointer;font-weight:600;transition:all 0.15s}
        .settings-toggle:hover{border-color:var(--accent);color:var(--accent)}
        .auto-save-indicator{font-size:0.75em;color:var(--success);margin-left:10px;opacity:0;transition:opacity 0.3s}
        .auto-save-indicator.show{opacity:1}
        .source-badge{font-size:0.68em;padding:2px 8px;border-radius:20px;margin-left:6px;font-weight:600}
        .source-badge.email{background:rgba(9,105,218,0.12);color:var(--info)}
        .source-badge.manual{background:var(--surface);color:var(--muted)}
        /* ─── Recall Banners ─── */
        .recall-banner{background:linear-gradient(135deg,rgba(207,34,46,0.12),rgba(207,34,46,0.06));border:1px solid rgba(207,34,46,0.25);color:var(--text);padding:14px 16px;border-radius:var(--radius-sm);margin:10px 0;font-size:0.85em;line-height:1.5}
        .recall-banner strong{font-size:1em;color:var(--danger)}.recall-banner a{color:var(--info);text-decoration:underline}.recall-banner a:hover{opacity:0.8}
        .recall-banner .recall-details{margin-top:8px;padding-top:8px;border-top:1px solid rgba(207,34,46,0.15);font-size:0.9em}
        .recall-banner .recall-actions{margin-top:12px;display:flex;gap:8px}
        .recall-banner .recall-btn{padding:5px 12px;border-radius:6px;font-size:0.8em;cursor:pointer;border:1px solid var(--border);font-weight:600;transition:all 0.15s;font-family:inherit}
        .recall-btn-dismiss{background:transparent;color:var(--muted)}.recall-btn-dismiss:hover{border-color:var(--muted);background:var(--surface)}
        .recall-btn-link{background:rgba(9,105,218,0.1);color:var(--info);border-color:rgba(9,105,218,0.25)}.recall-btn-link:hover{background:rgba(9,105,218,0.18)}
        /* ─── Responsive ─── */
        @media(max-width:768px){.stats-grid{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}.threshold-grid{grid-template-columns:1fr}.nav{flex-wrap:wrap;gap:10px}.nav-links{gap:2px}.app-container{padding:0 16px 32px}.nav{padding:12px 16px;margin:0 -16px 20px}}
    </style>
</head>
<body>
    <div class="app-container">
    <div class="nav">
        <div class="nav-brand"><div class="brand-icon">📦</div>Price Tracker</div>
        <div class="nav-links">
            <a href="/" class="{{ 'active' if request.path == '/' else '' }}">Dashboard</a>
            <a href="/archive" class="{{ 'active' if request.path == '/archive' else '' }}">Archive</a>
            <a href="/recalls" class="{{ 'active' if request.path == '/recalls' else '' }}">Recalls</a>
            <a href="/settings" class="{{ 'active' if request.path == '/settings' else '' }}">Settings</a>
            <a href="#" onclick="document.querySelector('footer').scrollIntoView({behavior:'smooth'});return false;" style="color:var(--accent);font-size:0.82em;">☕ Donate</a>
            <button class="theme-toggle" onclick="document.documentElement.setAttribute('data-theme',document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark');try{localStorage.setItem('theme',document.documentElement.getAttribute('data-theme'))}catch(e){}" title="Toggle theme">🌗</button>
        </div>
    </div>
    {% with messages = get_flashed_messages(with_categories=true) %}{% for cat, msg in messages %}<div class="flash {{ cat }}">{{ msg }}</div>{% endfor %}{% endwith %}
    {% block content %}{% endblock %}
    
    <!-- Footer: Donate + Terms -->
    <footer style="margin-top:48px;border-top:1px solid var(--border);padding-top:32px;">
        <!-- Donation Section -->
        <div style="background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:20px 24px;margin-bottom:24px;">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:1.2em;">☕</span>
                    <span style="font-weight:600;color:var(--text);">Saved money? Buy me a coffee!</span>
                </div>
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                    <a href="https://cash.app/$SteveVogt" target="_blank" rel="noopener" style="text-decoration:none;display:inline-flex;align-items:center;gap:5px;background:linear-gradient(135deg,#00D632,#00B828);color:white;padding:8px 14px;border-radius:8px;font-size:0.82em;font-weight:600;transition:transform 0.2s,box-shadow 0.2s;">💵 Cash App</a>
                    <a href="https://paypal.me/SteveVogt" target="_blank" rel="noopener" style="text-decoration:none;display:inline-flex;align-items:center;gap:5px;background:linear-gradient(135deg,#0070BA,#003087);color:white;padding:8px 14px;border-radius:8px;font-size:0.82em;font-weight:600;transition:transform 0.2s,box-shadow 0.2s;">🅿️ PayPal</a>
                    <a href="https://venmo.com/u/SteveVogt" target="_blank" rel="noopener" style="text-decoration:none;display:inline-flex;align-items:center;gap:5px;background:linear-gradient(135deg,#3D95CE,#008CFF);color:white;padding:8px 14px;border-radius:8px;font-size:0.82em;font-weight:600;transition:transform 0.2s,box-shadow 0.2s;">💜 Venmo</a>
                    <button onclick="document.getElementById('btc-section').style.display=document.getElementById('btc-section').style.display==='none'?'block':'none'" style="display:inline-flex;align-items:center;gap:5px;background:linear-gradient(135deg,#F7931A,#E2820A);color:white;padding:8px 14px;border-radius:8px;font-size:0.82em;font-weight:600;border:none;cursor:pointer;transition:transform 0.2s,box-shadow 0.2s;">₿ Bitcoin</button>
                </div>
            </div>
            <div id="btc-section" style="display:none;margin-top:12px;padding:12px;background:var(--surface);border-radius:var(--radius-sm);border:1px solid rgba(247,147,26,0.2);">
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                    <code id="btc-addr" style="font-size:0.78em;word-break:break-all;color:var(--text);background:var(--bg);padding:8px 12px;border-radius:var(--radius-sm);flex:1;font-family:'JetBrains Mono',monospace;">bc1qpdex8jrvyj3lh7q56av2k53nrh7u63s6t65uer</code>
                    <button onclick="navigator.clipboard.writeText(document.getElementById('btc-addr').textContent).then(()=>this.textContent='✓ Copied!').catch(()=>{})" style="padding:6px 12px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);color:var(--text);cursor:pointer;font-size:0.8em;font-family:inherit;">📋 Copy</button>
                </div>
            </div>
        </div>

        <!-- Terms, Privacy, Contact -->
        <div style="background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:24px;text-align:center;">
            <h3 style="font-size:0.95em;font-weight:600;margin-bottom:16px;color:var(--text);">Terms of Use & Privacy</h3>
            <div style="font-size:0.82em;color:var(--muted);line-height:1.8;max-width:800px;margin:0 auto;text-align:left;">
                <p style="margin-bottom:10px;"><strong>Disclaimer:</strong> This software is provided "AS IS" without warranty of any kind, express or implied. The author shall not be liable for any damages, losses, or consequences arising from the use of this software. Use at your own risk.</p>
                <p style="margin-bottom:10px;"><strong>Not Affiliated:</strong> This tool is an independent, personal project and is <strong>not affiliated with, endorsed by, or connected to Amazon.com, Inc.</strong> in any way. Amazon and all related trademarks are the property of Amazon.com, Inc.</p>
                <p style="margin-bottom:10px;"><strong>Terms of Service:</strong> Automated access to retail websites may violate their terms of service. This tool is provided for personal, educational purposes only. By using this software, you accept full responsibility for compliance with all applicable terms of service, laws, and regulations. The author is not responsible for any account restrictions, legal issues, or other consequences resulting from use.</p>
                <p style="margin-bottom:10px;"><strong>Privacy:</strong> All data is stored locally on your computer. No information is collected, shared, or transmitted to external servers by this application. For email alerts, we require a Google App Password (not your regular Gmail password) — this can be revoked anytime from your Google Account without affecting your main password.</p>
                <p style="margin-bottom:10px;"><strong>Security:</strong> This application runs only on your local machine (localhost) and is not accessible from the network. No external connections are made except to Amazon.com for price checks, CPSC/FDA for recall data, and your configured email server for alerts.</p>
            </div>
            <div style="margin-top:20px;padding-top:16px;border-top:1px solid var(--border);font-size:0.75em;color:var(--muted);">
                <div style="margin-bottom:6px;">© 2025 Amazon Price Tracker v{{ app_version }}</div>
                <div>Developed by <a href="mailto:steve@stevevogt.com" style="color:var(--muted);text-decoration:underline;">Steve Vogt</a> · <a href="mailto:steve@stevevogt.com" style="color:var(--muted);text-decoration:underline;">Contact / Support</a></div>
                <div style="margin-top:6px;font-style:italic;">Not affiliated with Amazon.com, Inc.</div>
            </div>
        </div>
    </footer>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded',()=>{try{const t=localStorage.getItem('theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}document.querySelectorAll('.flash').forEach(f=>{setTimeout(()=>{f.style.transition='opacity 0.4s';f.style.opacity='0';setTimeout(()=>f.remove(),400)},6000)})});
        async function checkProduct(id,btn){
            const status=document.getElementById('status-'+id),orig=btn.innerHTML;
            btn.disabled=true;btn.innerHTML='<div class="loader"></div>';
            if(status){status.className='check-status show checking';status.innerHTML='🔄 Scraping Amazon (30-60s)...';}
            try{
                const r=await fetch('/api/check/'+id,{method:'POST'});
                const d=await r.json();
                if(d.success){if(status){status.className='check-status show success';status.innerHTML='✅ '+d.message;}setTimeout(()=>location.reload(),1500);}
                else{if(status){status.className='check-status show error';status.innerHTML='❌ '+(d.error||'Failed');}btn.disabled=false;btn.innerHTML=orig;}
            }catch(e){if(status){status.className='check-status show error';status.innerHTML='❌ '+e.message;}btn.disabled=false;btn.innerHTML=orig;}
        }
        async function testEmail(btn){
            const orig=btn.innerHTML;btn.disabled=true;btn.innerHTML='<div class="loader"></div> Sending...';
            try{const r=await fetch('/api/test-email',{method:'POST'});const d=await r.json();alert(d.success?'✅ Test email sent!':'❌ '+d.error);}
            catch(e){alert('❌ '+e.message);}
            btn.disabled=false;btn.innerHTML=orig;
        }
        async function scanOrders(btn){
            const orig=btn.innerHTML;btn.disabled=true;btn.innerHTML='<div class="loader"></div> Importing from email...';
            try{
                const r=await fetch('/api/scan-orders',{method:'POST'});
                const d=await r.json();
                if(d.success){alert('✅ '+d.message + (d.debug ? '\\n\\nDebug: ' + d.debug : ''));if(d.added>0)location.reload();}
                else{alert('❌ '+d.error + (d.debug ? '\\n\\nDebug: ' + d.debug : ''));}
            }catch(e){alert('❌ '+e.message);}
            btn.disabled=false;btn.innerHTML=orig;
        }
        async function autoSaveEmail(){
            const email=document.getElementById('email-input').value;
            const password=document.getElementById('password-input').value;
            const indicator=document.getElementById('auto-save-indicator');
            const testBtn=document.getElementById('test-email-btn');
            const scanBtn=document.getElementById('scan-orders-btn');
            if(email && password){
                try{
                    const r=await fetch('/api/save-email',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});
                    const d=await r.json();
                    if(d.success){indicator.textContent='✓ Saved';indicator.classList.add('show');setTimeout(()=>indicator.classList.remove('show'),2000);testBtn.disabled=false;if(scanBtn)scanBtn.disabled=false;}
                }catch(e){}
            }
        }
        async function saveProductSettings(id){
            const form=document.getElementById('settings-form-'+id);
            const data=new FormData(form);
            const indicator=document.getElementById('save-indicator-'+id);
            try{
                const r=await fetch('/api/product/'+id+'/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(data))});
                const d=await r.json();
                if(d.success){indicator.textContent='✓ Saved';indicator.classList.add('show');setTimeout(()=>indicator.classList.remove('show'),2000);}
            }catch(e){}
        }
        function toggleSettings(id){const el=document.getElementById('settings-'+id);el.classList.toggle('show');}
        function openModal(id){document.getElementById('modal-'+id).classList.add('show');document.body.style.overflow='hidden';}
        function closeModal(id){document.getElementById('modal-'+id).classList.remove('show');document.body.style.overflow='auto';}
        let emailTimeout;
        function debounceEmailSave(){clearTimeout(emailTimeout);emailTimeout=setTimeout(autoSaveEmail,1000);}
        async function scanRecalls(btn){
            const orig=btn.innerHTML;btn.disabled=true;btn.innerHTML='<div class="loader"></div> Scanning CPSC...';
            try{const r=await fetch('/api/scan-recalls',{method:'POST'});const d=await r.json();alert(d.success?'✅ '+d.message:'❌ '+(d.error||'Failed'));if(d.success)location.reload();}
            catch(e){alert('❌ '+e.message);}
            btn.disabled=false;btn.innerHTML=orig;
        }
        async function dismissRecall(pid){
            if(!confirm('Dismiss this recall permanently?\\n\\nYou will NOT be notified about this recall again.\\nTo undo, click Re-check on the product card.'))return;
            try{const r=await fetch('/api/dismiss-recall/'+pid,{method:'POST'});const d=await r.json();if(d.success)location.reload();}
            catch(e){alert('❌ '+e.message);}
        }
    </script>
</body>
</html>
"""

INDEX_TPL = """
{% extends "layout" %}
{% block content %}
{% if update_available %}
<div style="background:linear-gradient(135deg,rgba(9,105,218,0.12),rgba(9,105,218,0.06));border:1px solid rgba(9,105,218,0.25);color:var(--text);padding:12px 18px;border-radius:8px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;font-size:0.88em;">
    <span>🆕 <strong>Update available:</strong> v{{ update_version }} (you have v{{ current_version }})</span>
    <a href="{{ update_url }}" target="_blank" style="background:rgba(9,105,218,0.15);color:var(--info);padding:6px 14px;border-radius:6px;text-decoration:none;font-weight:600;font-size:0.9em;border:1px solid rgba(9,105,218,0.3);">Download Update</a>
</div>
{% endif %}
<div class="stats-grid">
    <div class="stat-card"><div class="stat-value">{{ stats.active }}</div><div class="stat-label">Active</div></div>
    <div class="stat-card"><div class="stat-value">{{ stats.alerts_today }}</div><div class="stat-label">Alerts Today</div></div>
    <div class="stat-card"><div class="stat-value">{{ stats.at_target }}</div><div class="stat-label">At Target</div></div>
    <div class="stat-card"><div class="stat-value">{{ stats.from_orders }}</div><div class="stat-label">From Orders</div></div>
    <div class="stat-card"><div class="stat-value" style="color:{{ 'var(--danger)' if stats.recalls > 0 else 'var(--success)' }}">{{ stats.recalls }}</div><div class="stat-label">⚠️ Recalls</div></div>
</div>
<div class="card" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;padding:14px 22px;">
    <div style="font-size:0.88em;color:var(--muted);display:flex;align-items:center;gap:8px;">
        <span style="width:8px;height:8px;border-radius:50%;background:var(--success);display:inline-block;"></span>
        <span>Last: <strong style="color:var(--text);">{{ last_run_time }}</strong></span>
        {% if next_run_time %}<span style="opacity:0.5;">·</span><span>Next: ~{{ next_run_time }}</span>{% endif %}
    </div>
    <div style="display:flex;gap:8px;">
        <button class="btn btn-info btn-sm" onclick="scanOrders(this)" {% if not email_configured %}disabled title="Configure email in Settings first"{% endif %}>📧 Import</button>
        <button class="btn btn-danger btn-sm" onclick="scanRecalls(this)">🛡️ Recalls</button>
        <form action="/check-all" method="POST" style="margin:0;"><button class="btn btn-primary btn-sm" onclick="if(!confirm('Check all products? This scrapes each one (30-60s each) and may take a while.'))return false;this.innerHTML='<div class=\\'loader\\'></div> Running...'">⚡ Check All</button></form>
    </div>
</div>
<div class="card">
    <div class="section-header"><h2 style="font-size:1em;">➕ Add Items</h2></div>
    <form action="/add" method="POST">
        <textarea name="urls" placeholder="Paste Amazon product URLs or ASINs — one per line. Examples:&#10;https://www.amazon.com/dp/B08N5WRWNW&#10;B08N5WRWNW" rows="3" style="font-size:0.9em;resize:vertical;"></textarea>
        <div style="margin-top:12px;display:flex;gap:10px;flex-wrap:wrap;align-items:center;">
            <input type="number" name="price" placeholder="Target $" step="0.01" min="0" style="width:120px;font-size:0.88em;">
            <select name="expiration" style="width:170px;font-size:0.88em;"><option value="">Default ({{ settings.default_expiration_days }}d)</option><option value="7">7 days</option><option value="14">14 days</option><option value="30">30 days</option><option value="60">60 days</option><option value="0">Never expire</option></select>
            <div style="flex:1;"></div><button class="btn btn-primary">Track</button>
        </div>
    </form>
</div>
{% if products %}
<div class="section-header"><h2 style="font-size:1em;">📋 Tracked ({{ products|length }})</h2><div style="display:flex;gap:8px;align-items:center;"><select onchange="window.location='/?sort='+this.value" style="padding:7px 12px;border-radius:var(--radius-sm);background:var(--surface);color:var(--text);border:1px solid var(--border);font-size:0.82em;font-family:inherit;"><option value="newest" {{'selected' if current_sort=='newest' else ''}}>Newest Added</option><option value="oldest" {{'selected' if current_sort=='oldest' else ''}}>Oldest Added</option><option value="order_date" {{'selected' if current_sort=='order_date' else ''}}>Order Date</option><option value="last_checked" {{'selected' if current_sort=='last_checked' else ''}}>Last Checked</option><option value="price_low" {{'selected' if current_sort=='price_low' else ''}}>Price: Low→High</option><option value="price_high" {{'selected' if current_sort=='price_high' else ''}}>Price: High→Low</option><option value="biggest_drop" {{'selected' if current_sort=='biggest_drop' else ''}}>Biggest $ Drop</option><option value="pct_drop" {{'selected' if current_sort=='pct_drop' else ''}}>Biggest % Drop</option><option value="name" {{'selected' if current_sort=='name' else ''}}>Name A-Z</option></select><form action="/archive-expired" method="POST" style="margin:0;"><button class="btn btn-sm" style="background:var(--surface);color:var(--muted);border:1px solid var(--border);">📁 Archive Expired</button></form><form action="/clear-all" method="POST" style="margin:0;"><button class="btn btn-sm" style="background:transparent;color:var(--danger);border:1px solid var(--danger);padding:6px 10px;" onclick="return confirm('Delete ALL tracked products?')">🗑️</button></form></div></div>
<div class="grid">
{% for p in products %}
<div class="card product-card">
    <div class="product-topbar">
        <div style="display:flex;align-items:center;gap:8px;">
            {% if p.expires_at %}
                {% set days_left = ((p.expires_at - now).days) %}
                {% if days_left <= 0 %}<span class="badge badge-danger">Expired</span>
                {% elif days_left <= 3 %}<span class="badge badge-warning">{{ days_left }}d left</span>
                {% elif days_left <= 7 %}<span class="badge badge-info">{{ days_left }}d left</span>
                {% else %}<span class="badge badge-muted">{{ days_left }}d left</span>{% endif %}
            {% else %}<span class="badge badge-muted">No expiry</span>{% endif %}
            {% if p.source == 'email' %}<span class="source-badge email">📧 Order{% if p.purchase_price %} ${{ "%.2f"|format(p.purchase_price) }}{% endif %}</span>{% endif %}
            <button class="settings-toggle" onclick="toggleSettings({{p.id}})" title="Alert Settings">⚙️</button>
        </div>
        <form action="/delete/{{p.id}}" method="POST" style="margin:0;">
            <button class="delete-btn" onclick="return confirm('Delete this item?')" title="Delete">✕</button>
        </form>
    </div>
    <div class="product-title"><a href="{{p.url}}" target="_blank">{{ p.title }}</a></div>
    {% if p.recall_status == 'matched' %}
    <div class="recall-banner">
        <strong>⚠️ RECALL ALERT</strong>{% if p.recall_date %} <span style="opacity:0.7;font-size:0.85em;">· Recalled {{ p.recall_date[:10] }}</span>{% endif %}
        <div class="recall-details">
            {{ p.recall_title or 'Product recall detected' }}
            {% if p.recall_hazard %}<br>🔴 <strong>Hazard:</strong> {{ p.recall_hazard[:200] }}{% endif %}
            {% if p.recall_remedy %}<br>✅ <strong>Remedy:</strong> {{ p.recall_remedy[:200] }}{% endif %}
        </div>
        <div class="recall-actions">
            {% if p.recall_url %}<a href="{{ p.recall_url }}" target="_blank" class="recall-btn recall-btn-link">📋 Full Details</a>{% endif %}
            <button class="recall-btn recall-btn-dismiss" onclick="dismissRecall({{p.id}})">✕ Dismiss</button>
        </div>
    </div>
    {% elif p.recall_status == 'dismissed' %}
    <div style="font-size:0.75em;color:var(--muted);margin:4px 0;">ℹ️ Recall dismissed <button class="recall-btn recall-btn-dismiss" style="font-size:0.9em;padding:2px 6px;border:1px solid var(--border);border-radius:3px;cursor:pointer;color:var(--muted);background:transparent" onclick="dismissRecall({{p.id}})">Re-check</button></div>
    {% elif p.last_recall_check %}
    <div style="font-size:0.7em;color:var(--success);margin:2px 0;">✅ No recalls found ({{ p.last_recall_check.strftime('%m/%d') }})</div>
    {% endif %}
    <div class="prices-row">
        <div class="price-col">
            <label>New</label>
            <div class="price-display price-new {{ 'price-hit' if p.current_new_price and p.target_price and p.current_new_price <= p.target_price }}">
                {% if p.current_new_price %}${{ "%.2f"|format(p.current_new_price) }}{% else %}<span class="price-na">--</span>{% endif %}
            </div>
            {% if p.current_new_price and p.purchase_price and p.current_new_price < p.purchase_price %}
            {% set new_drop_pct = ((p.purchase_price - p.current_new_price) / p.purchase_price * 100) %}
            {% set new_drop_amt = p.purchase_price - p.current_new_price %}
            <div class="drop-indicator">⬇️ {{ "%.1f"|format(new_drop_pct) }}% (${{ "%.2f"|format(new_drop_amt) }})</div>
            {% elif p.current_new_price and p.purchase_price and p.current_new_price > p.purchase_price %}
            {% set new_up_pct = ((p.current_new_price - p.purchase_price) / p.purchase_price * 100) %}
            <div class="up-indicator">⬆️ {{ "%.1f"|format(new_up_pct) }}%</div>
            {% endif %}
            {% if p.lowest_new_price %}<div class="history-row"><span class="low">Low: ${{ "%.2f"|format(p.lowest_new_price) }}</span>{% if p.highest_new_price %}<span class="high">High: ${{ "%.2f"|format(p.highest_new_price) }}</span>{% endif %}</div>{% endif %}
        </div>
        <div class="price-col" style="text-align:right;">
            <label>Used</label>
            <div class="price-display price-used {{ 'price-hit' if p.current_used_price and p.target_price and p.current_used_price <= p.target_price }}">
                {% if p.current_used_price %}${{ "%.2f"|format(p.current_used_price) }}{% else %}<span class="price-na">--</span>{% endif %}
            </div>
            {% if p.current_used_price and (p.highest_used_price or p.purchase_price) and p.current_used_price < (p.highest_used_price or p.purchase_price) %}
            {% set used_ref = p.highest_used_price or p.purchase_price %}
            {% set used_drop_pct = ((used_ref - p.current_used_price) / used_ref * 100) %}
            {% set used_drop_amt = used_ref - p.current_used_price %}
            <div class="drop-indicator">⬇️ {{ "%.1f"|format(used_drop_pct) }}% (${{ "%.2f"|format(used_drop_amt) }})</div>
            {% endif %}
            {% if p.lowest_used_price %}<div class="history-row"><span class="low">Low: ${{ "%.2f"|format(p.lowest_used_price) }}</span>{% if p.highest_used_price %}<span class="high">High: ${{ "%.2f"|format(p.highest_used_price) }}</span>{% endif %}</div>{% endif %}
        </div>
    </div>
    <div id="settings-{{p.id}}" class="product-settings">
        <h4>🔔 Alert Thresholds <span id="save-indicator-{{p.id}}" class="auto-save-indicator"></span></h4>
        {% if settings.global_alerts_enabled %}
        <div class="global-override-notice">⚠️ Global thresholds are ON - these individual settings are disabled. <a href="/settings" style="color:#000;text-decoration:underline;">Edit Global Settings</a></div>
        {% endif %}
        <form id="settings-form-{{p.id}}" onchange="saveProductSettings({{p.id}})">
            <div class="threshold-grid">
                <div class="threshold-group">
                    <label>New Price Drop
                        <span class="tooltip"><span class="info-icon">i</span>
                            <span class="tooltip-text"><strong>New Price Alerts</strong><br><br>Get notified when the NEW price drops by this % or $ amount from purchase price. Leave blank to disable.</span>
                        </span>
                    </label>
                    <div class="threshold-inputs">
                        <input type="number" name="alert_new_pct" value="{{ p.alert_new_pct if p.alert_new_pct else '' }}" placeholder="% drop" step="0.1" min="0" {{ 'disabled' if settings.global_alerts_enabled }}>
                        <input type="number" name="alert_new_dollars" value="{{ p.alert_new_dollars if p.alert_new_dollars else '' }}" placeholder="$ drop" step="0.01" min="0" {{ 'disabled' if settings.global_alerts_enabled }}>
                    </div>
                </div>
                <div class="threshold-group">
                    <label>Used Price Drop
                        <span class="tooltip"><span class="info-icon">i</span>
                            <span class="tooltip-text"><strong>Used Price Alerts</strong><br><br>Get notified when the USED price drops by this % or $ amount from purchase price. Leave blank to disable.</span>
                        </span>
                    </label>
                    <div class="threshold-inputs">
                        <input type="number" name="alert_used_pct" value="{{ p.alert_used_pct if p.alert_used_pct else '' }}" placeholder="% drop" step="0.1" min="0" {{ 'disabled' if settings.global_alerts_enabled }}>
                        <input type="number" name="alert_used_dollars" value="{{ p.alert_used_dollars if p.alert_used_dollars else '' }}" placeholder="$ drop" step="0.01" min="0" {{ 'disabled' if settings.global_alerts_enabled }}>
                    </div>
                </div>
            </div>
            <div class="threshold-grid" style="margin-top:10px;">
                <div class="threshold-group">
                    <label>Target Price</label>
                    <input type="number" name="target_price" value="{{ p.target_price if p.target_price else '' }}" placeholder="Alert when price ≤ this" step="0.01" min="0" style="width:100%;">
                </div>
                <div class="threshold-group">
                    <label>Purchase Price <span style="font-size:0.8em;color:var(--muted);">(edit if incorrect)</span></label>
                    <input type="number" name="purchase_price" value="{{ p.purchase_price if p.purchase_price else '' }}" placeholder="What you paid" step="0.01" min="0" style="width:100%;">
                </div>
            </div>
            <div class="settings-note">💡 All fields optional. Leave blank = no alert for that condition. Alerts trigger if ANY condition is met.</div>
        </form>
    </div>
    <div class="price-chart">
        <div class="chart-header">
            <span class="chart-title">📈 History ({{ p.get_price_history()|length }} checks)</span>
            {% if p.screenshot_main or p.screenshot_offers %}
                <button class="screenshot-btn" onclick="openModal({{p.id}})">📷 View Screenshots</button>
            {% else %}
                <span style="font-size:0.7em;color:var(--muted);">No screenshots yet</span>
            {% endif %}
        </div>
        {% set history = p.get_price_history() %}
        {% if history|length > 1 %}
            {% set prices = [] %}{% for h in history %}{% if h.new %}{% set _ = prices.append(h.new) %}{% endif %}{% if h.used %}{% set _ = prices.append(h.used) %}{% endif %}{% endfor %}
            {% if prices %}
                {% set minp = prices|min %}{% set maxp = prices|max %}{% set rng = maxp - minp if maxp != minp else 1 %}
                <div class="chart-wrapper">
                    <div class="chart-y-axis"><span>${{ "%.0f"|format(maxp) }}</span><span>${{ "%.0f"|format(minp) }}</span></div>
                    <div class="chart-baseline"></div>
                    {% for h in history %}
                        {% if h.new %}{% set ht = ((h.new - minp) / rng * 100) %}<div class="chart-bar new" style="height:{{ [ht,8]|max }}%;" title="{{ h.date }}: New ${{ '%.2f'|format(h.new) }}"></div>{% endif %}
                        {% if h.used %}{% set ht = ((h.used - minp) / rng * 100) %}<div class="chart-bar used" style="height:{{ [ht,8]|max }}%;" title="{{ h.date }}: Used ${{ '%.2f'|format(h.used) }}"></div>{% endif %}
                    {% endfor %}
                </div>
                <div class="chart-legend"><span><div class="dot new"></div>New</span>{% if history|selectattr('used')|list %}<span><div class="dot used"></div>Used</span>{% endif %}</div>
            {% else %}<div class="no-chart">Waiting for price data...</div>{% endif %}
        {% else %}<div class="no-chart">Chart appears after 2+ checks</div>{% endif %}
    </div>
    <div class="product-meta">
        <span>🎯 Target: {{ "$%.2f"|format(p.target_price) if p.target_price else 'Not set' }}</span>
        <span>🕐 {{ p.last_checked.strftime('%m/%d %I:%M%p').lower() if p.last_checked else 'Never checked' }}</span>
    </div>
    <div id="status-{{p.id}}" class="check-status"></div>
    <div class="actions-row">
        <button class="btn btn-secondary btn-sm" onclick="checkProduct({{p.id}},this)">⚡ Check Now</button>
        <form action="/archive/{{p.id}}" method="POST" style="margin:0;flex:1;"><button class="btn btn-secondary btn-sm" style="width:100%;">📁 Archive</button></form>
    </div>
</div>
{% if p.screenshot_main or p.screenshot_offers %}
<div id="modal-{{p.id}}" class="modal" onclick="if(event.target===this)closeModal({{p.id}})">
    <span class="modal-close" onclick="closeModal({{p.id}})">&times;</span>
    <div class="modal-content">
        <h3>📷 {{ p.title }}</h3>
        {% if p.screenshot_main %}<h4>Main Product Page</h4><img src="/static/screenshots/{{p.screenshot_main}}" alt="Main page screenshot">{% endif %}
        {% if p.screenshot_offers %}<h4>All Offers Page (New & Used)</h4><img src="/static/screenshots/{{p.screenshot_offers}}" alt="Offers page screenshot">{% endif %}
    </div>
</div>
{% endif %}
{% endfor %}
</div>
{% else %}
<div class="card empty-state"><div class="empty-state-icon">📦</div><h3>No products tracked yet</h3><p style="margin-top:8px;">Paste Amazon URLs or ASINs above to start tracking prices.<br><span style="font-size:0.9em;">Or configure your email in <a href="/settings" style="color:var(--accent);">Settings</a> to auto-import orders from Gmail.</span></p></div>
{% endif %}
{% endblock %}
"""

ARCHIVE_TPL = """
{% extends "layout" %}
{% block content %}
<div class="section-header"><h2>📁 Archived ({{ products|length }})</h2>{% if products %}<form action="/delete-all-archived" method="POST" style="margin:0;"><button class="btn btn-danger btn-sm" onclick="return confirm('Delete all?')">🗑️ Delete All</button></form>{% endif %}</div>
{% if products %}
<div class="grid">
{% for p in products %}
<div class="card product-card">
    <div class="product-topbar">
        <span class="badge badge-muted">Archived {{ p.archived_at.strftime('%m/%d/%y') if p.archived_at else '' }}</span>
        <form action="/delete/{{p.id}}" method="POST" style="margin:0;"><button class="delete-btn" onclick="return confirm('Delete?')" title="Delete">✕</button></form>
    </div>
    <div class="product-title"><a href="{{p.url}}" target="_blank">{{ p.title }}</a></div>
    <div class="prices-row">
        <div class="price-col"><label>Last New</label><div class="price-display price-new">{% if p.current_new_price %}${{ "%.2f"|format(p.current_new_price) }}{% else %}<span class="price-na">--</span>{% endif %}</div></div>
        <div class="price-col" style="text-align:right;"><label>Last Used</label><div class="price-display price-used">{% if p.current_used_price %}${{ "%.2f"|format(p.current_used_price) }}{% else %}<span class="price-na">--</span>{% endif %}</div></div>
    </div>
    <div class="actions-row">
        <form action="/restore/{{p.id}}" method="POST" style="margin:0;flex:1;"><button class="btn btn-success btn-sm" style="width:100%;">↩️ Restore</button></form>
        <form action="/delete/{{p.id}}" method="POST" style="margin:0;flex:1;"><button class="btn btn-danger btn-sm" style="width:100%;" onclick="return confirm('Delete?')">🗑️ Delete</button></form>
    </div>
</div>
{% endfor %}
</div>
{% else %}
<div class="card empty-state"><div class="empty-state-icon">📁</div><h3>No archived products</h3></div>
{% endif %}
{% endblock %}
"""

SETTINGS_TPL = """
{% extends "layout" %}
{% block content %}
<div style="max-width:640px;margin:0 auto;">
    <div style="margin-bottom:24px;">
        <h1 style="margin:0;font-size:1.4em;font-weight:700;letter-spacing:-0.02em;">Settings</h1>
        <p style="color:var(--muted);font-size:0.9em;margin-top:4px;">Configure email, tracking, alerts, and recall monitoring.</p>
    </div>
    <form method="POST">
        <!-- Email Configuration -->
        <div class="card">
            <h3 style="margin:0 0 4px;font-size:1em;font-weight:700;display:flex;align-items:center;gap:8px;">📧 Email <span id="auto-save-indicator" class="auto-save-indicator">✓ Saved</span></h3>
            <p style="font-size:0.82em;color:var(--muted);margin:0 0 16px;">Used for price drop alerts and importing your Amazon orders.</p>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div><label style="font-size:0.78em;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;display:block;margin-bottom:6px;">Gmail Address</label>
                <input type="email" id="email-input" name="email" value="{{ settings.email_address }}" placeholder="you@gmail.com" oninput="debounceEmailSave()"></div>
                <div><label style="font-size:0.78em;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;display:block;margin-bottom:6px;">App Password <span class="tooltip"><span class="info-icon">i</span><span class="tooltip-text"><strong>Gmail App Password</strong><br><br>This is NOT your regular Gmail password. Go to Google Account → Security → 2-Step Verification → App Passwords, then generate one for "Mail". It looks like "xxxx xxxx xxxx xxxx".</span></span> <a href="https://myaccount.google.com/apppasswords" target="_blank" style="font-size:0.9em;color:var(--info);text-decoration:none;">↗ Get one</a></label>
                <input type="password" id="password-input" name="password" value="{{ settings.email_password }}" placeholder="xxxx xxxx xxxx xxxx" oninput="debounceEmailSave()"></div>
            </div>
            <div style="display:flex;gap:8px;margin-top:14px;">
                <button type="button" id="test-email-btn" class="btn btn-secondary btn-sm" onclick="testEmail(this)" {% if not settings.email_address or not settings.email_password %}disabled{% endif %}>📬 Test Email</button>
                <button type="button" id="scan-orders-btn" class="btn btn-info btn-sm" onclick="scanOrders(this)" {% if not settings.email_address or not settings.email_password %}disabled{% endif %}>📧 Import Orders Now</button>
            </div>
            <p style="font-size:0.78em;color:var(--muted);margin:10px 0 0;">Credentials auto-save as you type.</p>
        </div>
        
        <!-- Order Import -->
        <div class="card">
            <h3 style="margin:0 0 4px;font-size:1em;font-weight:700;display:flex;align-items:center;gap:8px;">📦 Order Auto-Import
                <span class="tooltip"><span class="info-icon">i</span>
                    <span class="tooltip-text"><strong>Amazon Order Import</strong><br><br>Scans your Gmail for Amazon order confirmation emails and auto-tracks those products. Extracts ASINs directly from email links for 100% accuracy. Runs automatically based on your chosen frequency.</span>
                </span>
            </h3>
            <p style="font-size:0.82em;color:var(--muted);margin:0 0 16px;">Automatically imports new Amazon orders from your Gmail.</p>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;align-items:end;">
                <div>
                    <label style="font-size:0.78em;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;display:block;margin-bottom:6px;">Auto-Import</label>
                    <select name="auto_import">
                        <option value="1" {{ 'selected' if settings.auto_import_orders }}>On</option>
                        <option value="0" {{ 'selected' if not settings.auto_import_orders }}>Off</option>
                    </select>
                </div>
                <div>
                    <label style="font-size:0.78em;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;display:block;margin-bottom:6px;">Check Frequency</label>
                    <select name="import_frequency">
                        <option value="every_6h" {{ 'selected' if (settings.import_frequency or '') == 'every_6h' }}>Every 6 hours</option>
                        <option value="every_12h" {{ 'selected' if (settings.import_frequency or 'every_12h') == 'every_12h' }}>Every 12 hours</option>
                        <option value="daily" {{ 'selected' if (settings.import_frequency or '') == 'daily' }}>Once daily</option>
                    </select>
                </div>
            </div>
            <p style="font-size:0.78em;color:var(--muted);margin:10px 0 0;">Last import: {{ settings.last_email_scan.strftime('%b %d, %I:%M %p') if settings.last_email_scan else 'Never' }} · Recommended: every 12 hours catches orders within the same day.</p>
        </div>
        
        <!-- Tracking Duration -->
        <div class="card">
            <h3 style="margin:0 0 4px;font-size:1em;font-weight:700;">⏱️ Tracking Duration</h3>
            <p style="font-size:0.82em;color:var(--muted);margin:0 0 16px;">How long to monitor prices after purchase.</p>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div>
                    <label style="font-size:0.78em;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;display:block;margin-bottom:6px;">Track for (days)</label>
                    <input type="number" name="expiration_days" value="{{ settings.default_expiration_days }}" min="0" max="365">
                </div>
                <div>
                    <label style="font-size:0.78em;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;display:block;margin-bottom:6px;">Auto-Archive Expired</label>
                    <select name="auto_archive"><option value="1" {{ 'selected' if settings.auto_archive }}>On</option><option value="0" {{ 'selected' if not settings.auto_archive }}>Off</option></select>
                </div>
            </div>
            <p style="font-size:0.78em;color:var(--muted);margin:10px 0 0;">For email-imported orders: expires X days from <strong>order date</strong> (covers the return window). For manual items: X days from when added. Set 0 for no expiration.</p>
        </div>
        
        <!-- Check Interval -->
        <div class="card">
            <h3 style="margin:0 0 4px;font-size:1em;font-weight:700;display:flex;align-items:center;gap:8px;">🔄 Price Check Interval
                <span class="tooltip"><span class="info-icon">i</span>
                    <span class="tooltip-text"><strong>Bot Detection Prevention</strong><br><br>The actual check time is randomized by ±{{ jitter }} minutes around your base interval. This creates a {{ min_hours }}-{{ max_hours }} hour window that looks more human-like to Amazon.</span>
                </span>
            </h3>
            <p style="font-size:0.82em;color:var(--muted);margin:0 0 16px;">How often to scrape Amazon for price changes.</p>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;align-items:end;">
                <div>
                    <label style="font-size:0.78em;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;display:block;margin-bottom:6px;">Base Interval (minutes)</label>
                    <input type="number" name="check_interval" value="{{ settings.check_interval_minutes }}" min="60" max="1440">
                </div>
                <div style="font-size:0.82em;color:var(--muted);padding-bottom:12px;font-family:'JetBrains Mono','DM Sans',monospace;">{{ min_hours }}–{{ max_hours }} hrs<br><span style="font-size:0.9em;">randomized</span></div>
            </div>
        </div>
        
        <!-- Global Alerts -->
        <div class="card">
            <h3 style="margin:0 0 4px;font-size:1em;font-weight:700;display:flex;align-items:center;gap:8px;">🔔 Global Alert Thresholds
                <span class="tooltip"><span class="info-icon">i</span>
                    <span class="tooltip-text"><strong>Global Thresholds</strong><br><br>When enabled, these thresholds apply to ALL products, overriding individual settings. Great for "alert me if anything drops 10%".</span>
                </span>
            </h3>
            <p style="font-size:0.82em;color:var(--muted);margin:0 0 16px;">Apply the same alert rules to every tracked product.</p>
            <div style="display:flex;gap:12px;align-items:center;margin-bottom:16px;">
                <label style="margin:0;font-size:0.85em;font-weight:600;white-space:nowrap;">Enable</label>
                <select name="global_alerts_enabled" style="width:80px;"><option value="0" {{ 'selected' if not settings.global_alerts_enabled }}>Off</option><option value="1" {{ 'selected' if settings.global_alerts_enabled }}>On</option></select>
            </div>
            <div style="opacity:{{ '1' if settings.global_alerts_enabled else '0.45' }};transition:opacity 0.2s;">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                    <div><label style="font-size:0.78em;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;display:block;margin-bottom:6px;">New Drop %</label>
                    <input type="number" name="global_new_pct" value="{{ settings.global_new_pct if settings.global_new_pct else '' }}" placeholder="e.g. 10" step="0.1" min="0"></div>
                    <div><label style="font-size:0.78em;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;display:block;margin-bottom:6px;">New Drop $</label>
                    <input type="number" name="global_new_dollars" value="{{ settings.global_new_dollars if settings.global_new_dollars else '' }}" placeholder="e.g. 5.00" step="0.01" min="0"></div>
                    <div><label style="font-size:0.78em;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;display:block;margin-bottom:6px;">Used Drop %</label>
                    <input type="number" name="global_used_pct" value="{{ settings.global_used_pct if settings.global_used_pct else '' }}" placeholder="e.g. 15" step="0.1" min="0"></div>
                    <div><label style="font-size:0.78em;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;display:block;margin-bottom:6px;">Used Drop $</label>
                    <input type="number" name="global_used_dollars" value="{{ settings.global_used_dollars if settings.global_used_dollars else '' }}" placeholder="e.g. 10.00" step="0.01" min="0"></div>
                </div>
                <p style="font-size:0.78em;color:var(--muted);margin:10px 0 0;">Drop calculated from purchase price (or highest tracked price if none set). Alert fires if ANY condition is met.</p>
            </div>
        </div>
        
        <!-- Recall Scanner -->
        <div class="card">
            <h3 style="margin:0 0 4px;font-size:1em;font-weight:700;display:flex;align-items:center;gap:8px;">🛡️ Recall Monitor
                <span class="tooltip"><span class="info-icon">i</span>
                    <span class="tooltip-text"><strong>Multi-Source Recall Monitoring</strong><br><br>Checks two federal databases: CPSC (consumer products) and openFDA (food, drugs, health devices) for recalls matching your tracked products. Checks ALL products including archived — recalls don't expire.</span>
                </span>
            </h3>
            <p style="font-size:0.82em;color:var(--muted);margin:0 0 16px;">Checks CPSC + FDA databases for safety recalls on all your purchases.</p>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div>
                    <label style="font-size:0.78em;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;display:block;margin-bottom:6px;">Recall Scanning</label>
                    <select name="recall_scan_enabled"><option value="1" {{ 'selected' if settings.recall_scan_enabled }}>On</option><option value="0" {{ 'selected' if not settings.recall_scan_enabled }}>Off</option></select>
                </div>
                <div>
                    <label style="font-size:0.78em;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:0.04em;display:block;margin-bottom:6px;">Scan Frequency</label>
                    <select name="recall_scan_frequency">
                        <option value="every_check" {{ 'selected' if settings.recall_scan_frequency == 'every_check' }}>Every price check</option>
                        <option value="daily" {{ 'selected' if settings.recall_scan_frequency == 'daily' }}>Daily</option>
                        <option value="weekly" {{ 'selected' if settings.recall_scan_frequency == 'weekly' }}>Weekly</option>
                    </select>
                </div>
            </div>
            <p style="font-size:0.78em;color:var(--muted);margin:10px 0 0;">Last scan: {{ settings.last_recall_scan.strftime('%b %d, %I:%M %p') if settings.last_recall_scan else 'Never' }} · Monitors indefinitely, even archived products.</p>
        </div>
        
        <!-- Email Options -->
        <div class="card">
            <h3 style="margin:0 0 4px;font-size:1em;font-weight:700;">📬 Email Options</h3>
            <div style="display:flex;gap:12px;align-items:center;">
                <label style="margin:0;font-size:0.85em;font-weight:600;white-space:nowrap;">Batch Alerts</label>
                <select name="batch_email_alerts" style="width:80px;"><option value="0" {{ 'selected' if not settings.batch_email_alerts }}>Off</option><option value="1" {{ 'selected' if settings.batch_email_alerts }}>On</option></select>
            </div>
            <p style="font-size:0.78em;color:var(--muted);margin:10px 0 0;">When on, groups multiple price drops into a single email instead of one per product.</p>
        </div>
        
        <!-- Startup -->
        <div class="card">
            <h3 style="margin:0 0 4px;font-size:1em;font-weight:700;">🚀 System</h3>
            <div style="display:flex;gap:12px;align-items:center;">
                <label style="margin:0;font-size:0.85em;font-weight:600;white-space:nowrap;">Run at Windows Startup</label>
                <select name="run_at_startup" style="width:80px;"><option value="0" {{ 'selected' if not settings.run_at_startup }}>Off</option><option value="1" {{ 'selected' if settings.run_at_startup }}>On</option></select>
            </div>
            <p style="font-size:0.78em;color:var(--muted);margin:10px 0 0;">When on, the tracker starts automatically when you log into Windows. Runs silently in the system tray.</p>
        </div>
        
        <button class="btn btn-primary" style="width:100%;padding:12px;font-size:0.95em;">💾 Save All Settings</button>
    </form>
</div>
{% endblock %}
"""

RECALLS_TPL = """
{% extends "layout" %}
{% block content %}
<div class="section-header">
    <h2>🛡️ Product Recall Monitor</h2>
    <div style="display:flex;gap:8px;align-items:center;">
        <span style="font-size:0.85em;color:var(--muted);">Last scan: {{ settings.last_recall_scan.strftime('%m/%d %I:%M%p') if settings.last_recall_scan else 'Never' }} · {{ total_products }} products monitored</span>
        <button class="btn btn-danger btn-sm" onclick="scanRecalls(this)">🔍 Scan Now</button>
    </div>
</div>
<div class="card" style="margin-bottom:20px;">
    <p style="color:var(--muted);margin:0;font-size:0.9em;">
        🛡️ Checks <strong>two federal databases</strong> for recalls on ALL your Amazon purchases (including archived items):
    </p>
    <div style="display:flex;gap:20px;margin-top:10px;flex-wrap:wrap;">
        <div style="font-size:0.85em;"><strong style="color:var(--accent);">CPSC</strong> — <a href="https://www.cpsc.gov/Recalls" target="_blank" style="color:var(--info);">Consumer Product Safety Commission</a><br><span style="color:var(--muted);">Electronics, furniture, toys, kitchen, clothing, etc.</span></div>
        <div style="font-size:0.85em;"><strong style="color:var(--accent);">FDA</strong> — <a href="https://open.fda.gov" target="_blank" style="color:var(--info);">Food & Drug Administration</a><br><span style="color:var(--muted);">Food, supplements, OTC drugs, health devices, cosmetics</span></div>
    </div>
    <p style="color:var(--muted);margin:10px 0 0;font-size:0.85em;">
        ⏰ Scans run {{ settings.recall_scan_frequency if settings.recall_scan_enabled else '<strong style="color:var(--danger);">(disabled)</strong>' }} — recalls are checked <strong>indefinitely</strong>, even after price tracking expires.
    </p>
</div>
{% if matched %}
<h3 style="color:var(--danger);">⚠️ Active Recalls ({{ matched|length }})</h3>
<div class="grid">
{% for p in matched %}
<div class="card" style="border-color:var(--danger);border-width:2px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <div class="product-title" style="height:auto;"><a href="{{p.url}}" target="_blank">{{ p.title }}</a></div>
        {% if p.is_archived %}<span class="badge badge-muted" style="flex-shrink:0;">Archived</span>{% endif %}
    </div>
    <div class="recall-banner">
        <strong>{{ p.recall_title or 'Product recall detected' }}</strong>
        {% if p.recall_date %}<br><span style="opacity:0.8;">Recall Date: {{ p.recall_date[:10] }}</span>{% endif %}
        {% if p.recall_hazard %}<div style="margin-top:8px;"><strong>🔴 Hazard:</strong> {{ p.recall_hazard[:400] }}</div>{% endif %}
        {% if p.recall_remedy %}<div style="margin-top:5px;"><strong>✅ Remedy:</strong> {{ p.recall_remedy[:400] }}</div>{% endif %}
        {% if p.recall_consumer_contact %}<div style="margin-top:5px;"><strong>📞 Contact:</strong> {{ p.recall_consumer_contact[:300] }}</div>{% endif %}
        <div class="recall-actions">
            {% if p.recall_url %}<a href="{{ p.recall_url }}" target="_blank" class="recall-btn recall-btn-link">📋 Full Details</a>{% endif %}
            <button class="recall-btn recall-btn-dismiss" onclick="dismissRecall({{p.id}})">✕ Dismiss</button>
        </div>
    </div>
</div>
{% endfor %}
</div>
{% else %}
<div class="card" style="text-align:center;padding:30px;">
    <div style="font-size:2em;margin-bottom:10px;">✅</div>
    <h3 style="margin:0;color:var(--success);">No Active Recalls</h3>
    <p style="color:var(--muted);margin-top:8px;">None of your {{ total_products }} tracked products have CPSC or FDA recall matches.</p>
</div>
{% endif %}
{% if dismissed %}
<h3 style="color:var(--muted);margin-top:30px;">Dismissed ({{ dismissed|length }})</h3>
<div class="grid">
{% for p in dismissed %}
<div class="card" style="opacity:0.6;">
    <div class="product-title" style="height:auto;"><a href="{{p.url}}" target="_blank">{{ p.title }}</a></div>
    <div style="font-size:0.85em;color:var(--muted);margin-top:8px;">{{ p.recall_title or 'Recall dismissed' }}</div>
    <button class="recall-btn recall-btn-dismiss" style="margin-top:8px;font-size:0.8em;padding:4px 10px;border:1px solid var(--border);border-radius:4px;cursor:pointer;color:var(--muted);background:transparent" onclick="dismissRecall({{p.id}})">🔄 Re-check</button>
</div>
{% endfor %}
</div>
{% endif %}
{% endblock %}
"""

Base = declarative_base()

class Settings(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    email_address = Column(String, default="")
    email_password = Column(String, default="")
    smtp_server = Column(String, default="smtp.gmail.com")
    smtp_port = Column(Integer, default=587)
    default_expiration_days = Column(Integer, default=DEFAULT_EXPIRATION_DAYS)
    auto_archive = Column(Boolean, default=True)
    check_interval_minutes = Column(Integer, default=DEFAULT_INTERVAL_MINUTES)
    auto_import_orders = Column(Boolean, default=True)
    import_frequency = Column(String, default="every_12h")
    last_email_scan = Column(DateTime, nullable=True)
    global_alerts_enabled = Column(Boolean, default=False)
    global_new_pct = Column(Float, nullable=True)
    global_used_pct = Column(Float, nullable=True)
    global_new_dollars = Column(Float, nullable=True)
    global_used_dollars = Column(Float, nullable=True)
    batch_email_alerts = Column(Boolean, default=False)
    recall_scan_enabled = Column(Boolean, default=True)
    recall_scan_frequency = Column(String, default="daily")
    last_recall_scan = Column(DateTime, nullable=True)
    run_at_startup = Column(Boolean, default=False)

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    asin = Column(String, unique=True, nullable=False)
    title = Column(String)
    url = Column(String)
    screenshot_main = Column(String, nullable=True)
    screenshot_offers = Column(String, nullable=True)
    target_price = Column(Float, nullable=True)
    current_new_price = Column(Float)
    current_used_price = Column(Float)
    prev_new_price = Column(Float, default=0.0)
    prev_used_price = Column(Float, default=0.0)
    lowest_new_price = Column(Float, nullable=True)
    highest_new_price = Column(Float, nullable=True)
    lowest_used_price = Column(Float, nullable=True)
    highest_used_price = Column(Float, nullable=True)
    price_history_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=True)
    last_checked = Column(DateTime)
    last_alert_sent = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    source = Column(String)
    alert_new_pct = Column(Float, nullable=True)
    alert_new_dollars = Column(Float, nullable=True)
    alert_used_pct = Column(Float, nullable=True)
    alert_used_dollars = Column(Float, nullable=True)
    order_date = Column(DateTime, nullable=True)
    order_id = Column(String, nullable=True)
    purchase_price = Column(Float, nullable=True)
    recall_status = Column(String, default="none")  # none, matched, dismissed
    recall_id = Column(Integer, nullable=True)
    recall_number = Column(String, nullable=True)
    recall_title = Column(String, nullable=True)
    recall_description = Column(Text, nullable=True)
    recall_url = Column(String, nullable=True)
    recall_hazard = Column(String, nullable=True)
    recall_remedy = Column(String, nullable=True)
    recall_date = Column(String, nullable=True)
    recall_consumer_contact = Column(String, nullable=True)
    last_recall_check = Column(DateTime, nullable=True)
    
    def get_price_history(self):
        try: return json.loads(self.price_history_json or "[]")
        except: return []
    
    def add_price_point(self, new_price=None, used_price=None):
        h = self.get_price_history()
        h.append({'date': datetime.now().strftime('%m/%d %H:%M'), 'new': new_price, 'used': used_price})
        if len(h) > MAX_PRICE_HISTORY: h = h[-MAX_PRICE_HISTORY:]
        self.price_history_json = json.dumps(h)
    
    def should_alert_new(self, new_price, global_pct=None, global_dollars=None):
        """Check if new price drop should trigger alert. Uses purchase_price as reference, falls back to highest_new_price.
        Requires at least one prior price check to prevent false positives on first scrape."""
        if not new_price: return False
        # Must have a previous check to compare against — first scrape establishes baseline only
        if not self.last_checked: return False
        # Reference price: purchase price, or highest tracked price, or previous price
        ref_price = self.purchase_price or self.highest_new_price or self.prev_new_price
        if not ref_price or ref_price <= 0: return False
        
        # Use global thresholds if provided, otherwise use per-item
        pct_threshold = global_pct if global_pct is not None else self.alert_new_pct
        dollars_threshold = global_dollars if global_dollars is not None else self.alert_new_dollars
        
        if pct_threshold:
            drop_pct = (ref_price - new_price) / ref_price * 100
            if drop_pct >= pct_threshold: return True
        if dollars_threshold:
            if ref_price - new_price >= dollars_threshold: return True
        return False
    
    def should_alert_used(self, used_price, global_pct=None, global_dollars=None):
        """Check if used price drop should trigger alert. 
        Reference: highest_used_price (tracks actual used market), then purchase_price, then prev."""
        if not used_price: return False
        # Must have a previous check to compare against — first scrape establishes baseline only
        if not self.last_checked: return False
        # For used prices, reference the used price history first — purchase_price was for NEW condition
        ref_price = self.highest_used_price or self.purchase_price or self.prev_used_price
        if not ref_price or ref_price <= 0: return False
        
        # Use global thresholds if provided, otherwise use per-item
        pct_threshold = global_pct if global_pct is not None else self.alert_used_pct
        dollars_threshold = global_dollars if global_dollars is not None else self.alert_used_dollars
        
        if pct_threshold:
            drop_pct = (ref_price - used_price) / ref_price * 100
            if drop_pct >= pct_threshold: return True
        if dollars_threshold:
            if ref_price - used_price >= dollars_threshold: return True
        return False
    
    def get_drop_info(self, price_type='new'):
        """Get drop info (pct, dollars) for display. Returns (drop_pct, drop_dollars, ref_price) or (None, None, None)"""
        if price_type == 'new':
            current = self.current_new_price
            ref = self.purchase_price or self.highest_new_price
        else:
            current = self.current_used_price
            # For used, reference the used market first (purchase_price was new condition)
            ref = self.highest_used_price or self.purchase_price
        
        if not current or not ref or ref <= 0:
            return None, None, None
        
        drop_dollars = ref - current
        drop_pct = drop_dollars / ref * 100
        return drop_pct, drop_dollars, ref
    
    def update_from_scrape(self, data):
        """Apply scraped price data to this product. Returns True if any data was updated."""
        updated = False
        if data.get('title'):
            current = self.title or ''
            scraped = data['title']
            # Update if: placeholder title, OR Amazon changed the title significantly
            is_placeholder = 'Loading' in current or 'Order Item' in current or len(current) < 5
            is_different = scraped.lower() != current.lower() and len(scraped) >= 10
            if is_placeholder or is_different:
                self.title = scraped
                updated = True
        if data.get('screenshot_main'): self.screenshot_main = data['screenshot_main']; updated = True
        if data.get('screenshot_offers'): self.screenshot_offers = data['screenshot_offers']; updated = True
        if data.get('new_price'):
            self.prev_new_price = self.current_new_price or data['new_price']
            self.current_new_price = data['new_price']
            if not self.lowest_new_price or data['new_price'] < self.lowest_new_price: self.lowest_new_price = data['new_price']
            if not self.highest_new_price or data['new_price'] > self.highest_new_price: self.highest_new_price = data['new_price']
            updated = True
        if data.get('used_price'):
            self.prev_used_price = self.current_used_price or data['used_price']
            self.current_used_price = data['used_price']
            if not self.lowest_used_price or data['used_price'] < self.lowest_used_price: self.lowest_used_price = data['used_price']
            if not self.highest_used_price or data['used_price'] > self.highest_used_price: self.highest_used_price = data['used_price']
            updated = True
        if updated:
            self.add_price_point(data.get('new_price'), data.get('used_price'))
            self.last_checked = datetime.now()
        return updated

engine = create_engine(f'sqlite:///{DB_NAME}', echo=False)
Base.metadata.create_all(engine)  # Create tables first
migrate_database()  # Then add missing columns to existing tables
os.makedirs(os.path.join(os.getcwd(), 'static', 'screenshots'), exist_ok=True)
# Ensure default settings row exists
ScopedSession = scoped_session(sessionmaker(bind=engine))
with ScopedSession() as _init_s:
    if not _init_s.query(Settings).first():
        _init_s.add(Settings())
        _init_s.commit()

@contextmanager
def get_session():
    s = ScopedSession()
    try: yield s; s.commit()
    except: s.rollback(); raise
    finally: ScopedSession.remove()

def init_db():
    """Legacy init — settings row now created at module load. Kept for compatibility."""
    pass

ASIN_RE = re.compile(r'/(?:dp|gp/product|gp/aw/d)/([A-Z0-9]{10})(?:[/?]|$)', re.I)
BARE_ASIN_RE = re.compile(r'^[A-Z0-9]{10}$', re.I)
def extract_asin(url):
    if not url: return None
    url = url.strip()
    # Accept bare ASINs like "B08N5WRWNW"
    if BARE_ASIN_RE.match(url):
        return url.upper()
    m = ASIN_RE.search(url)
    return m.group(1).upper() if m else None

def parse_price(text):
    if not text: return None
    m = re.search(r'\$(\d{1,3}(?:,\d{3})*\.\d{2})', text)
    if m:
        try:
            p = float(m.group(1).replace(',', ''))
            if 1.00 <= p <= 100000: return p
        except: pass
    return None

MAX_LOG_SIZE = 1_000_000  # 1MB per log file

def _rotate_log(log_file):
    """Rotate log file if it exceeds MAX_LOG_SIZE. Keeps one backup."""
    try:
        if os.path.exists(log_file) and os.path.getsize(log_file) > MAX_LOG_SIZE:
            backup = log_file + '.old'
            if os.path.exists(backup):
                os.remove(backup)
            os.rename(log_file, backup)
    except: pass

# ============================================================
# GMAIL ORDER SCANNER - FIXED
# ============================================================

def scan_amazon_orders(email_address, email_password, days_back=32):
    """Scan Gmail for Amazon order confirmations - extracts ASIN directly from email (no Amazon search needed)"""
    found_products = []
    debug_info = []
    seen_order_ids = set()
    
    # Create import log
    log_file = os.path.join(os.getcwd(), 'import_log.txt')
    _rotate_log(log_file)
    
    def log(msg):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{timestamp}] {msg}"
        logger.info(msg)
        try:
            with open(log_file, 'a') as f:
                f.write(line + '\n')
        except:
            pass
    
    log("="*60)
    log("STARTING EMAIL IMPORT")
    log("="*60)
    
    try:
        log("Connecting to Gmail IMAP...")
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(email_address, email_password)
        log("Login successful")
        
        status, count = mail.select('INBOX')
        inbox_count = count[0].decode() if count else '?'
        log(f"INBOX has {inbox_count} messages")
        debug_info.append("Connected")
        
        since_date = (datetime.now() - timedelta(days=days_back)).strftime('%d-%b-%Y')
        log(f"Searching for orders since {since_date}")
        
        # Search for order confirmation emails
        # "Ordered:" = shipment/processing emails (arrive hours/days later)
        # "Your Amazon.com order" = immediate order confirmation (arrives instantly)
        search_queries = [
            f'(SUBJECT "Ordered:" FROM "amazon" SINCE {since_date})',
            f'(FROM "auto-confirm@amazon.com" SUBJECT "Ordered" SINCE {since_date})',
            f'(SUBJECT "Your Amazon.com order" FROM "amazon" SINCE {since_date})',
            f'(FROM "auto-confirm@amazon.com" SUBJECT "order of" SINCE {since_date})',
        ]
        
        all_email_ids = set()
        for query in search_queries:
            try:
                status, data = mail.search(None, query)
                if status == 'OK' and data[0]:
                    ids = data[0].split()
                    log(f"Query found {len(ids)} emails")
                    all_email_ids.update(ids)
            except Exception as e:
                log(f"Query error: {e}")
        
        log(f"Total unique emails to process: {len(all_email_ids)}")
        debug_info.append(f"Emails={len(all_email_ids)}")
        
        orders_found = 0
        no_asin = 0
        duplicates = 0
        
        for msg_id in list(all_email_ids)[:200]:
            try:
                _, msg_data = mail.fetch(msg_id, '(RFC822)')
                raw_email = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw_email)
                
                # Get and decode subject
                subject_raw = msg.get('Subject', '')
                subject = ''
                try:
                    decoded_parts = decode_header(subject_raw)
                    for part, encoding in decoded_parts:
                        if isinstance(part, bytes):
                            subject += part.decode(encoding or 'utf-8', errors='ignore')
                        else:
                            subject += str(part)
                except:
                    subject = str(subject_raw)
                
                subject_lower = subject.lower()
                
                # Skip if no order-related keyword in subject
                # "Ordered:" = shipment confirmation, "Your Amazon.com order" = instant confirmation
                if 'ordered' not in subject_lower and 'your amazon.com order' not in subject_lower:
                    continue
                
                # Skip shipment/delivery/refund notifications
                skip_keywords = ['shipped', 'delivered', 'refund', 'return', 'cancel', 'arriving', 'problem']
                if any(kw in subject_lower for kw in skip_keywords):
                    continue
                
                log(f"\n--- Processing: {subject[:60]}...")
                
                # Get email date
                date_str = msg.get('Date', '')
                email_date = datetime.now()
                try:
                    email_date = parsedate_to_datetime(date_str).replace(tzinfo=None)
                except:
                    pass
                
                # Get raw email content
                raw_text = raw_email.decode('utf-8', errors='ignore')
                
                # Extract plain text body for price/quantity parsing
                plain_text = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain':
                            try:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    plain_text = payload.decode('utf-8', errors='ignore')
                                    break
                            except:
                                pass
                
                # Get order ID - check for duplicates
                order_id = None
                order_match = re.search(r'(\d{3}-\d{7}-\d{7})', raw_text)
                if order_match:
                    order_id = order_match.group(1)
                    log(f"  Order ID: {order_id}")
                    if order_id in seen_order_ids:
                        log(f"  SKIPPED: Duplicate order ID")
                        duplicates += 1
                        continue
                    seen_order_ids.add(order_id)
                
                # Extract product name from subject
                product_name = None
                # Pattern 1: "Ordered: [product]" (shipment confirmation)
                match = re.search(r'Ordered:\s*(.+)', subject, re.I)
                if match:
                    raw_name = match.group(1).strip()
                # Pattern 2: "Your Amazon.com order of [product]" (instant confirmation)
                elif 'your amazon.com order' in subject_lower:
                    match = re.search(r'order\s+of\s+(.+)', subject, re.I)
                    if match:
                        raw_name = match.group(1).strip()
                    else:
                        raw_name = None
                else:
                    raw_name = None
                
                if raw_name:
                    raw_name = re.sub(r'^\d+\s+', '', raw_name)
                    raw_name = raw_name.strip('"\'""''`')
                    raw_name = re.sub(r'\s*and\s+\d+\s+more\s+items?.*$', '', raw_name, flags=re.I)
                    raw_name = re.sub(r'\.{2,}$', '', raw_name).strip()
                    raw_name = raw_name.strip('"\'""''`')
                    if len(raw_name) >= 3:
                        product_name = raw_name
                        log(f"  Product name: {product_name[:50]}")
                
                # CRITICAL: Extract ASIN directly from email redirect URLs
                # Pattern: dp%2F{ASIN}...fed_asin = ordered item (NOT recommendation)
                # Recommendations have AGH3Col or dealz_cs patterns
                
                found_asins = set()
                
                # Method 1: Look for ordered item pattern (fed_asin in ref) — most reliable
                # URL-encoded: dp%2F{ASIN}%3Fref_%3D...fed_asin
                for m in re.finditer(r'dp%2F([A-Z0-9]{10})%3F[^&]*fed_asin', raw_text, re.I):
                    found_asins.add(m.group(1).upper())
                
                # Method 2: Look for i_fed or t_fed patterns (image/text links to ordered item)
                for m in re.finditer(r'dp%2F([A-Z0-9]{10})%3F[^&]*[it]_fed', raw_text, re.I):
                    found_asins.add(m.group(1).upper())
                
                # Method 3: Look for non-encoded dp/ pattern in order section only
                if not found_asins:
                    order_section = raw_text.split('Continue shopping')[0] if 'Continue shopping' in raw_text else raw_text[:len(raw_text)//2]
                    for m in re.finditer(r'/dp/([A-Z0-9]{10})', order_section, re.I):
                        found_asins.add(m.group(1).upper())
                
                # Method 4: Decode URL-encoded links and find ASIN
                if not found_asins:
                    decoded = unquote(raw_text)
                    order_section = decoded.split('Continue shopping')[0] if 'Continue shopping' in decoded else decoded[:len(decoded)//2]
                    for m in re.finditer(r'/dp/([A-Z0-9]{10})', order_section, re.I):
                        found_asins.add(m.group(1).upper())
                
                if not found_asins:
                    log(f"  ERROR: Could not extract ASIN from email")
                    no_asin += 1
                    continue
                
                log(f"  ASINs found: {len(found_asins)} — {', '.join(found_asins)}")
                
                # Extract quantity and item price
                quantity = 1
                item_price = None
                
                qty_price_match = re.search(r'Quantity:\s*(\d+)\s+([\d.]+)\s*USD', plain_text)
                if qty_price_match:
                    quantity = int(qty_price_match.group(1))
                    item_price = float(qty_price_match.group(2))
                    log(f"  Quantity: {quantity}, Price: ${item_price}")
                else:
                    qty_match = re.search(r'Quantity:\s*(\d+)', plain_text)
                    if qty_match:
                        quantity = int(qty_match.group(1))
                    
                    # Only use price if single item (multi-item Grand Total is misleading)
                    if len(found_asins) == 1:
                        price_match = re.search(r'([\d.]+)\s*USD\s*Grand\s*Total', plain_text)
                        if price_match:
                            item_price = float(price_match.group(1))
                        else:
                            price_matches = re.findall(r'\$\s*([\d.]+)', plain_text)
                            for p in price_matches:
                                try:
                                    val = float(p)
                                    if val > 0:
                                        item_price = val
                                        break
                                except:
                                    pass
                    if item_price:
                        log(f"  Quantity: {quantity}, Price: ${item_price}")
                
                # Add each ASIN as a separate product
                for asin in found_asins:
                    orders_found += 1
                    found_products.append({
                        'asin': asin,
                        'product_name': product_name or f"Order Item {asin}",
                        'order_date': email_date,
                        'order_id': order_id,
                        'quantity': quantity,
                        # Only assign price if single item (multi-item price is total, not per-item)
                        'item_price': item_price if len(found_asins) == 1 else None
                    })
                    log(f"  SUCCESS: Added ASIN {asin}{'  (price omitted — multi-item order)' if len(found_asins) > 1 else ''}")
                        
            except Exception as e:
                log(f"  EXCEPTION: {str(e)}")
                continue
        
        log(f"\n{'='*60}")
        log(f"IMPORT COMPLETE: {orders_found} orders, {duplicates} duplicates, {no_asin} missing ASINs")
        log(f"{'='*60}\n")
        
        debug_info.append(f"Found={orders_found}")
        if duplicates: debug_info.append(f"Dupes={duplicates}")
        if no_asin: debug_info.append(f"NoASIN={no_asin}")
        
        mail.close()
        mail.logout()
        
    except imaplib.IMAP4.error as e:
        error_msg = str(e)
        log(f"IMAP ERROR: {error_msg}")
        if 'AUTHENTICATIONFAILED' in error_msg:
            raise Exception("Login failed - use App Password")
        raise Exception(f"IMAP: {error_msg[:40]}")
    except Exception as e:
        log(f"ERROR: {str(e)}")
        raise Exception(f"Error: {str(e)[:50]}")
    
    return found_products, '; '.join(debug_info)

async def scrape_with_playwright(asin):
    result = {'new_price': None, 'used_price': None, 'title': None, 'screenshot_main': None, 'screenshot_offers': None, 'error': None}
    ss_dir = os.path.join(os.getcwd(), 'static', 'screenshots')
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Clean up old screenshots for this ASIN (keep only 2 newest of each type)
    try:
        for prefix in [f'{asin}_main_', f'{asin}_offers_']:
            existing = sorted([f for f in os.listdir(ss_dir) if f.startswith(prefix)], reverse=True)
            for old_file in existing[2:]:  # Keep 2 most recent
                os.remove(os.path.join(ss_dir, old_file))
    except: pass
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(viewport={'width': 1920, 'height': 1080}, user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
            page = await ctx.new_page()
            
            url = f"https://www.amazon.com/dp/{asin}"
            logger.info(f"[{asin}] Loading main page...")
            await page.goto(url, timeout=40000, wait_until='domcontentloaded')
            await page.wait_for_timeout(2500)
            
            ss_main = f"{asin}_main_{ts}.png"
            await page.screenshot(path=os.path.join(ss_dir, ss_main), full_page=False)
            result['screenshot_main'] = ss_main
            
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Detect bot/CAPTCHA blocks
            page_text_check = html.lower()
            if 'captcha' in page_text_check or 'robot' in page_text_check and 'are you a human' in page_text_check:
                result['error'] = 'Amazon bot detection triggered (CAPTCHA). Try again later.'
                await browser.close()
                return result
            if soup.select_one('#captchacharacters'):
                result['error'] = 'Amazon CAPTCHA page detected. Try again later.'
                await browser.close()
                return result
            
            t = soup.select_one('#productTitle')
            if t: result['title'] = t.get_text().strip()[:TITLE_MAX_LENGTH]
            
            for sel in ['#corePrice_feature_div .a-offscreen', '.reinventPricePriceToPayMargin .a-offscreen', '#priceblock_ourprice', '#priceblock_dealprice', '#apex_offerDisplay_desktop .a-offscreen']:
                el = soup.select_one(sel)
                if el:
                    pr = parse_price(el.get_text())
                    if pr:
                        result['new_price'] = pr
                        break
            
            offers_url = f"https://www.amazon.com/gp/offer-listing/{asin}/ref=dp_olp_all_mbc?ie=UTF8&condition=all"
            await page.goto(offers_url, timeout=40000, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            ss_offers = f"{asin}_offers_{ts}.png"
            await page.screenshot(path=os.path.join(ss_dir, ss_offers), full_page=False)
            result['screenshot_offers'] = ss_offers
            
            offers_html = await page.content()
            offers_soup = BeautifulSoup(offers_html, 'html.parser')
            
            used_prices = []
            new_prices_from_offers = []
            
            pinned = offers_soup.select_one('#aod-pinned-offer')
            if pinned:
                price_el = pinned.select_one('.a-price .a-offscreen')
                condition_el = pinned.select_one('#aod-offer-heading')
                if price_el:
                    pr = parse_price(price_el.get_text())
                    condition_text = condition_el.get_text().lower() if condition_el else ''
                    if pr:
                        if 'used' in condition_text or 'renewed' in condition_text:
                            used_prices.append(pr)
                        else:
                            new_prices_from_offers.append(pr)
            
            for offer in offers_soup.select('#aod-offer-list #aod-offer'):
                heading = offer.select_one('#aod-offer-heading')
                heading_text = heading.get_text().lower().strip() if heading else ''
                price_el = offer.select_one('.a-price .a-offscreen')
                if not price_el: continue
                pr = parse_price(price_el.get_text())
                if not pr: continue
                is_used = any(w in heading_text for w in ['used', 'renewed', 'refurbished', 'acceptable', 'good', 'very good', 'like new'])
                if is_used:
                    used_prices.append(pr)
                elif 'new' in heading_text or heading_text == '':
                    new_prices_from_offers.append(pr)
            
            page_text = await page.inner_text('body')
            for pattern in [r'Used\s*\([^)]*\)\s*from\s*\$(\d+\.\d{2})', r'Used\s+from\s+\$(\d+\.\d{2})']:
                for match in re.findall(pattern, page_text, re.I):
                    price_str = match[-1] if isinstance(match, tuple) else match
                    try:
                        pr = float(price_str)
                        if 1.00 <= pr <= 100000: used_prices.append(pr)
                    except: pass
            
            if new_prices_from_offers:
                best_new = min(new_prices_from_offers)
                if result['new_price'] is None or best_new < result['new_price']:
                    result['new_price'] = best_new
            
            if used_prices:
                result['used_price'] = min(used_prices)
            
            await browser.close()
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"[{asin}] Error: {e}")
    
    return result

def scrape_with_requests(asin):
    """Lightweight scraper using requests + BeautifulSoup. No browser needed.
    Works in the EXE without any external installs. No screenshots."""
    result = {'new_price': None, 'used_price': None, 'title': None, 'screenshot_main': None, 'screenshot_offers': None, 'error': None}
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    try:
        # Main product page
        url = f"https://www.amazon.com/dp/{asin}"
        logger.info(f"[{asin}] Fetching main page (requests)...")
        resp = session.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # Bot detection check
        page_lower = html.lower()
        if 'captcha' in page_lower or soup.select_one('#captchacharacters'):
            result['error'] = 'Amazon bot detection triggered (CAPTCHA). Try again later.'
            return result
        if len(html) < 5000 and 'robot' in page_lower:
            result['error'] = 'Amazon returned a minimal page (possible block). Try again later.'
            return result
        
        # Title
        t = soup.select_one('#productTitle')
        if t: result['title'] = t.get_text().strip()[:TITLE_MAX_LENGTH]
        
        # New price - try multiple selectors (Amazon changes these frequently)
        price_selectors = [
            '#corePrice_feature_div .a-offscreen',
            '.reinventPricePriceToPayMargin .a-offscreen',
            '#priceblock_ourprice',
            '#priceblock_dealprice',
            '#apex_offerDisplay_desktop .a-offscreen',
            '.a-price .a-offscreen',
            '#tp_price_block_total_price_ww .a-offscreen',
            '#price_inside_buybox',
            '#newBuyBoxPrice',
        ]
        for sel in price_selectors:
            el = soup.select_one(sel)
            if el:
                pr = parse_price(el.get_text())
                if pr:
                    result['new_price'] = pr
                    break
        
        # Regex fallback for new price if selectors missed
        if not result['new_price']:
            for pattern in [r'"priceAmount":\s*(\d+\.?\d*)', r'\$(\d{1,5}\.\d{2})\s*</span>']:
                m = re.search(pattern, html)
                if m:
                    try:
                        pr = float(m.group(1))
                        if 0.50 <= pr <= 100000:
                            result['new_price'] = pr
                            break
                    except: pass
        
        # Offers page for used prices
        import time as _time
        _time.sleep(random.uniform(2, 4))  # Polite delay
        offers_url = f"https://www.amazon.com/gp/offer-listing/{asin}/ref=dp_olp_all_mbc?ie=UTF8&condition=all"
        logger.info(f"[{asin}] Fetching offers page (requests)...")
        resp2 = session.get(offers_url, timeout=30, allow_redirects=True)
        
        if resp2.status_code == 200:
            offers_html = resp2.text
            offers_soup = BeautifulSoup(offers_html, 'html.parser')
            used_prices = []
            new_prices_from_offers = []
            
            pinned = offers_soup.select_one('#aod-pinned-offer')
            if pinned:
                price_el = pinned.select_one('.a-price .a-offscreen')
                condition_el = pinned.select_one('#aod-offer-heading')
                if price_el:
                    pr = parse_price(price_el.get_text())
                    condition_text = condition_el.get_text().lower() if condition_el else ''
                    if pr:
                        if 'used' in condition_text or 'renewed' in condition_text:
                            used_prices.append(pr)
                        else:
                            new_prices_from_offers.append(pr)
            
            for offer in offers_soup.select('#aod-offer-list #aod-offer'):
                heading = offer.select_one('#aod-offer-heading')
                heading_text = heading.get_text().lower().strip() if heading else ''
                price_el = offer.select_one('.a-price .a-offscreen')
                if not price_el: continue
                pr = parse_price(price_el.get_text())
                if not pr: continue
                is_used = any(w in heading_text for w in ['used', 'renewed', 'refurbished', 'acceptable', 'good', 'very good', 'like new'])
                if is_used:
                    used_prices.append(pr)
                elif 'new' in heading_text or heading_text == '':
                    new_prices_from_offers.append(pr)
            
            # Regex fallback for used prices
            for pattern in [r'Used\s*\([^)]*\)\s*from\s*\$(\d+\.\d{2})', r'Used\s+from\s+\$(\d+\.\d{2})']:
                for match in re.findall(pattern, offers_html, re.I):
                    price_str = match[-1] if isinstance(match, tuple) else match
                    try:
                        pr = float(price_str)
                        if 1.00 <= pr <= 100000: used_prices.append(pr)
                    except: pass
            
            if new_prices_from_offers:
                best_new = min(new_prices_from_offers)
                if result['new_price'] is None or best_new < result['new_price']:
                    result['new_price'] = best_new
            
            if used_prices:
                result['used_price'] = min(used_prices)
    
    except requests.exceptions.Timeout:
        result['error'] = 'Request timed out. Amazon may be slow or blocking.'
    except requests.exceptions.ConnectionError:
        result['error'] = 'Connection failed. Check your internet.'
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"[{asin}] Requests scraper error: {e}")
    
    return result

def _playwright_available():
    """Check if Playwright + Chromium are actually usable."""
    # Try importing fresh — the EXE may have just installed it at startup
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False

# Cache the check so we only do it once per session
_pw_checked = None

def run_scraper(asin):
    """Smart scraper: uses Playwright if available (screenshots + prices), 
    falls back to requests (prices only, no screenshots). 
    EXE always works — Playwright is a bonus."""
    global _pw_checked
    
    # Check Playwright availability once per session
    if _pw_checked is None:
        _pw_checked = _playwright_available()
        if _pw_checked:
            logger.info("Scraper mode: Playwright (full screenshots + prices)")
        else:
            logger.info("Scraper mode: Requests-only (prices only, no screenshots). Install Playwright for screenshots.")
    
    if _pw_checked:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(scrape_with_playwright(asin))
            finally:
                loop.close()
            # If Playwright succeeded, return its result
            if result.get('error') is None or result.get('new_price') or result.get('used_price'):
                return result
        except Exception as e:
            logger.warning(f"[{asin}] Playwright failed ({e}), falling back to requests")
    
    # Fallback: requests-based scraper (always works)
    return scrape_with_requests(asin)

# ============================================================
# MULTI-SOURCE RECALL SCANNER (CPSC + openFDA)
# ============================================================

CPSC_API_URL = "https://www.saferproducts.gov/RestWebServices/Recall"
FDA_API_URL = "https://api.fda.gov"

def extract_recall_keywords(title):
    """Extract meaningful search keywords from a product title for recall API lookups.
    Returns dict with 'brand', 'product_type', and 'queries' (list of (query_string, weight) tuples)."""
    if not title:
        return {'brand': '', 'product_type': '', 'queries': []}
    
    # Clean up title
    clean = re.sub(r'\b(Loading|Order Item|B[0-9][A-Z0-9]{8})\b', '', title, flags=re.I)
    clean = re.sub(r'[,\-–—|/\\()\[\]{}]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    # Common words to skip (NOT brand names — amazon/basics/essentials removed to support Amazon Basics)
    stop_words = {'the','a','an','and','or','for','with','in','on','of','to','by','from','is','it',
                  'that','this','be','at','as','pack','set','count','piece','inch','inches','ft',
                  'oz','lb','lbs','ml','size','color','new','edition','version','updated','latest',
                  'prime','brand','item','best','seller','great',
                  'value','premium','professional','ultra','super','pro','plus','max','mini','deluxe'}
    
    words = [w for w in clean.split() if w.lower() not in stop_words and len(w) > 1 and re.search(r'[a-zA-Z]', w)]
    
    if not words:
        return {'brand': '', 'product_type': '', 'queries': []}
    
    # Brand = first word (e.g., "Weber", "Instant", "Nature")
    brand = words[0] if words else ''
    
    # Product type = the core noun(s) describing what the product IS
    # Skip brand name, numbers, and short words to find the product type
    type_words = [w for w in words[1:] if len(w) > 3 and not w[0].isdigit() and not re.match(r'^[A-Z0-9]{2,}$', w)]
    product_type = ' '.join(type_words[:3]) if type_words else ''
    
    queries = []
    
    # Strategy 1: Brand + first 2 product type words (most specific)
    if brand and type_words:
        queries.append((f"{brand} {' '.join(type_words[:2])}", 3))
    
    # Strategy 2: Brand alone (broad catch)
    if brand:
        queries.append((brand, 1))
    
    # Strategy 3: Brand + first type word
    if brand and type_words:
        queries.append((f"{brand} {type_words[0]}", 2))
    
    return {'brand': brand.lower(), 'product_type': product_type.lower(), 'queries': queries}


def score_recall_match(product_title, recall_data, source='cpsc'):
    """Score how well a recall matches our tracked product. 
    Returns 0-100. Requires brand match AND product-type overlap to score above threshold.
    This is intentionally strict — false negatives are better than false positives."""
    if not product_title or not recall_data:
        return 0
    
    title_lower = product_title.lower()
    kw = extract_recall_keywords(product_title)
    brand = kw['brand']
    product_type = kw['product_type']
    # Use 4+ letter words as baseline to avoid connector words (and, the, why, etc.)
    # Also include 3-letter words that appear product-specific:
    #   - Contains a digit (D3, G65, etc.) 
    #   - Capitalized in original title (Pot, Gem, Pro, Max — product names, not grammar words)
    base_words = set(re.findall(r'\b[a-z]{4,}\b', title_lower))
    # Add short product-specific words
    for m in re.finditer(r'\b([a-zA-Z0-9]{2,3})\b', product_title):
        word = m.group(1)
        # Include if: contains digit, OR is capitalized (proper noun / product name)
        if any(c.isdigit() for c in word) or (word[0].isupper() and word.lower() not in (
                'the','and','for','but','not','are','was','has','its','you','can','may','all',
                'any','who','why','how','did','get','got','had','him','her','his','our','own',
                'new','old','one','two','big','few','set','use','say','see','try','day','way',
                'end','yet','now','let','put','run','cut','off','ask','add','men','per')):
            base_words.add(word.lower())
    title_words = base_words
    # Product-specific words (excluding very common ones)
    generic_words = {'product','item','model','number','about','units','sold','stores',
                     'between','through','from','were','with','that','this','have','been',
                     'consumers','should','contact','company','free','replacement','refund',
                     'risk','injury','hazard','recall','recalled','due','poses','posing',
                     'also','each','made','make','more','most','much','only','over','some',
                     'such','than','them','then','they','very','when','will','your','used',
                     'like','does','just','into','back','after','could','would','which',
                     'first','other','where','still','every','under','while','these','being',
                     'there','those','might','comes','including','contains','found'}
    product_words = title_words - generic_words
    # Remove brand word from product_words — brand match is scored separately
    # This prevents brand names like "amazon", "basics" from inflating the product type overlap
    if brand:
        product_words.discard(brand)
    
    score = 0
    brand_found = False
    product_type_match = False
    
    if source == 'cpsc':
        # --- BRAND CHECK (required) ---
        # Check if brand appears in recall product names, title, or manufacturers
        recall_text_parts = []
        for prod in recall_data.get('Products', []):
            recall_text_parts.append((prod.get('Name', '') or '').lower())
            recall_text_parts.append((prod.get('Description', '') or '').lower())
        recall_text_parts.append((recall_data.get('Title', '') or '').lower())
        for mfg in recall_data.get('Manufacturers', []):
            recall_text_parts.append((mfg.get('Name', '') or '').lower())
        recall_text = ' '.join(recall_text_parts)
        
        if brand and len(brand) >= 2 and re.search(r'\b' + re.escape(brand) + r'\b', recall_text):
            brand_found = True
            score += 30
        
        # --- PRODUCT TYPE CHECK (required) ---
        # The actual product type words must overlap with the recall product name
        # Take the BEST single-product match (don't accumulate across Products[])
        best_product_score = 0
        for prod in recall_data.get('Products', []):
            this_product_score = 0
            prod_name = (prod.get('Name', '') or '').lower()
            prod_desc = (prod.get('Description', '') or '').lower()
            prod_combined = prod_name + ' ' + prod_desc
            # Same hybrid extraction as product title
            prod_words = set(re.findall(r'\b[a-z]{4,}\b', prod_combined)) - generic_words
            # Include short capitalized/numeric words from original recall name
            orig_combined = (prod.get('Name', '') or '') + ' ' + (prod.get('Description', '') or '')
            for m2 in re.finditer(r'\b([a-zA-Z0-9]{2,3})\b', orig_combined):
                w = m2.group(1)
                if any(c.isdigit() for c in w) or (w[0].isupper() and w.lower() not in (
                    'the','and','for','but','not','are','was','has','its','you','can','may','all',
                    'any','who','why','how','did','get','got','had','him','her','his','our','own',
                    'new','old','one','two','big','few','set','use','say','see','try','day','way',
                    'end','yet','now','let','put','run','cut','off','ask','add','men','per')):
                    prod_words.add(w.lower())
            prod_words -= generic_words
            
            # Count meaningful word overlap (not just any 3-letter word)
            overlap = product_words & prod_words
            if len(overlap) >= 2:
                this_product_score += min(len(overlap) * 12, 40)
            
            # Model number match (very strong signal)
            model = (prod.get('Model', '') or '').strip()
            if model and len(model) >= 3 and model.lower() in title_lower:
                this_product_score += 25
            
            if this_product_score > best_product_score:
                best_product_score = this_product_score
        
        if best_product_score > 0:
            product_type_match = True
            score += best_product_score
        
        # --- RECALL TITLE OVERLAP ---
        recall_title = (recall_data.get('Title', '') or '').lower()
        recall_title_words = set(re.findall(r'\b[a-z]{4,}\b', recall_title)) - generic_words
        title_overlap = product_words & recall_title_words
        if len(title_overlap) >= 2:
            score += min(len(title_overlap) * 8, 20)
        
        # Amazon retailer bonus
        for retailer in recall_data.get('Retailers', []):
            if 'amazon' in (retailer.get('Name', '') or '').lower():
                score += 5
        
        # UPC match would be definitive
        for upc in recall_data.get('ProductUPCs', []):
            upc_val = (upc.get('UPC', '') or '').strip()
            if upc_val and upc_val in product_title:
                score = 100  # Definitive match
        
        # HARD RULE: If brand doesn't match, cap score at 15 (never triggers alert)
        if not brand_found:
            score = min(score, 15)
        
        # HARD RULE: If product type doesn't overlap, cap score at 30 (below threshold)
        if not product_type_match:
            score = min(score, 30)
    
    elif source == 'fda':
        product_desc = (recall_data.get('product_description', '') or '').lower()
        reason = (recall_data.get('reason_for_recall', '') or '').lower()
        recalling_firm = (recall_data.get('recalling_firm', '') or '').lower()
        
        # Brand check — stricter for FDA:
        # 1. Brand in firm name (word boundary match), OR
        # 2. Brand is the FIRST significant word in the product description (actual brand position)
        # This prevents "unicorn" sweater matching "UNICORN BLOOD" supplement
        if brand and len(brand) >= 2:
            brand_in_firm = bool(re.search(r'\b' + re.escape(brand) + r'\b', recalling_firm))
            # Check if brand is leading word in product description (where brands actually appear)
            desc_first_words = product_desc.strip().split()[:3]  # First 3 words
            brand_leads_desc = any(brand == w.strip(',-()') for w in desc_first_words)
            
            if brand_in_firm or brand_leads_desc:
                brand_found = True
                score += 30
        
        # Product type overlap with description — same hybrid extraction
        desc_words = set(re.findall(r'\b[a-z]{4,}\b', product_desc)) - generic_words
        orig_desc = recall_data.get('product_description', '') or ''
        for m3 in re.finditer(r'\b([a-zA-Z0-9]{2,3})\b', orig_desc):
            w3 = m3.group(1)
            if any(c.isdigit() for c in w3) or (w3[0].isupper() and w3.lower() not in (
                'the','and','for','but','not','are','was','has','its','you','can','may','all',
                'any','who','why','how','did','get','got','had','him','her','his','our','own',
                'new','old','one','two','big','few','set','use','say','see','try','day','way',
                'end','yet','now','let','put','run','cut','off','ask','add','men','per')):
                desc_words.add(w3.lower())
        desc_words -= generic_words
        overlap = product_words & desc_words
        if len(overlap) >= 2:
            product_type_match = True
            score += min(len(overlap) * 12, 40)
        
        # Reason overlap (weak signal, capped)
        reason_words = set(re.findall(r'\b[a-z]{4,}\b', reason)) - generic_words
        reason_overlap = product_words & reason_words
        if reason_overlap:
            score += min(len(reason_overlap) * 3, 10)
        
        # HARD RULE: Brand must match
        if not brand_found:
            score = min(score, 15)
        
        # HARD RULE: Product type must overlap
        if not product_type_match:
            score = min(score, 30)
    
    return min(score, 100)


def check_cpsc_recalls_for_product(product_title, min_score=55):
    """Check CPSC API for recalls matching a product. Returns best match or None.
    min_score=55 requires brand match (30) + meaningful product overlap (25+)."""
    kw_data = extract_recall_keywords(product_title)
    keywords = kw_data.get('queries', [])
    if not keywords:
        return None
    
    best_match = None
    best_score = 0
    
    for query, weight in keywords:
        try:
            params = {'format': 'json', 'ProductName': query}
            resp = requests.get(CPSC_API_URL, params=params, timeout=15)
            if resp.status_code != 200:
                continue
            
            recalls = resp.json()
            if not isinstance(recalls, list):
                continue
            
            for recall in recalls[:25]:
                score = score_recall_match(product_title, recall, source='cpsc')
                
                if score > best_score:
                    best_score = score
                    best_match = recall
                
                # Short-circuit: if we found a very strong match, stop searching
                if best_score >= 85:
                    break
            
            time.sleep(0.5)
            
            # If we found a strong match, skip remaining queries
            if best_score >= 85:
                break
            
        except Exception as e:
            logger.warning(f"CPSC API error for '{query}': {e}")
            continue
    
    if best_match and best_score >= min_score:
        return best_match
    return None


def check_fda_recalls_for_product(product_title, min_score=55):
    """Check openFDA enforcement APIs for recalls matching a product.
    Searches food, drug, and device enforcement endpoints.
    min_score=55 requires brand match (30) + product type overlap (25+)."""
    kw_data = extract_recall_keywords(product_title)
    keywords = kw_data.get('queries', [])
    if not keywords:
        return None
    
    # openFDA endpoints relevant to Amazon purchases
    fda_endpoints = [
        f"{FDA_API_URL}/food/enforcement.json",
        f"{FDA_API_URL}/drug/enforcement.json",
        f"{FDA_API_URL}/device/enforcement.json",
    ]
    
    best_match = None
    best_score = 0
    
    for query, weight in keywords[:2]:
        # openFDA uses Elasticsearch syntax: spaces = OR, quotes = exact phrase
        encoded_query = quote(query)
        
        for endpoint in fda_endpoints:
            try:
                url = f"{endpoint}?search=product_description:{encoded_query}&limit=5"
                resp = requests.get(url, timeout=15)
                
                # openFDA returns 404 when no results found — that's normal, not an error
                if resp.status_code == 404:
                    continue
                if resp.status_code != 200:
                    continue
                
                data = resp.json()
                results = data.get('results', [])
                
                for recall in results:
                    score = score_recall_match(product_title, recall, source='fda')
                    
                    if score > best_score:
                        best_score = score
                        best_match = recall
                        best_match['_fda_endpoint'] = endpoint
                
                time.sleep(0.3)
                
            except Exception as e:
                logger.warning(f"openFDA error for '{query}' at {endpoint}: {e}")
                continue
    
    if best_match and best_score >= min_score:
        return best_match
    return None


def normalize_fda_to_recall_data(fda_result):
    """Convert openFDA enforcement report format to our standard recall data format."""
    if not fda_result:
        return None
    
    # Map FDA classification to severity description
    classification = fda_result.get('classification', '')
    severity = ''
    if classification == 'Class I':
        severity = 'SERIOUS: Reasonable probability of serious adverse health consequences or death'
    elif classification == 'Class II':
        severity = 'Moderate: May cause temporary or medically reversible adverse health consequences'
    elif classification == 'Class III':
        severity = 'Low: Not likely to cause adverse health consequences'
    
    hazard = fda_result.get('reason_for_recall', '')
    if severity:
        hazard = f"[{classification} - {severity}] {hazard}"
    
    # Parse the recall_initiation_date (format: YYYYMMDD) into readable format
    raw_date = fda_result.get('recall_initiation_date', '')
    recall_date = ''
    if raw_date and len(raw_date) >= 8:
        try:
            recall_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        except:
            recall_date = raw_date
    
    return {
        'recall_id': hash(fda_result.get('recall_number', '')) % 10**8,
        'recall_number': fda_result.get('recall_number', 'N/A'),
        'recall_title': f"FDA Recall: {fda_result.get('recalling_firm', 'Unknown')} - {fda_result.get('product_description', '')[:100]}",
        'recall_description': fda_result.get('product_description', '')[:1000],
        'recall_url': f"https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts",
        'recall_hazard': hazard[:500],
        'recall_remedy': f"Status: {fda_result.get('status', 'Unknown')}. {fda_result.get('voluntary_mandated', '')}",
        'recall_date': recall_date,
        'recall_consumer_contact': f"{fda_result.get('recalling_firm', '')} - {fda_result.get('city', '')}, {fda_result.get('state', '')}",
        'recall_source': 'fda',
    }


def run_recall_scan(products_to_check):
    """Scan CPSC + openFDA for recalls on a list of products. Returns dict of {product_id: recall_data}."""
    log_file = os.path.join(os.getcwd(), 'recall_log.txt')
    _rotate_log(log_file)
    def log(msg):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{timestamp}] {msg}"
        logger.info(msg)
        try:
            with open(log_file, 'a') as f:
                f.write(line + '\n')
        except:
            pass
    
    log("=" * 60)
    log("STARTING MULTI-SOURCE RECALL SCAN (Precision Mode)")
    log(f"Sources: CPSC (saferproducts.gov) + openFDA (api.fda.gov)")
    log(f"Products to check: {len(products_to_check)}")
    log(f"Matching rules: Brand MUST match + Product type MUST overlap")
    log(f"Minimum score: 55 (brand=30 + product overlap=25+)")
    log("=" * 60)
    
    results = {}
    matches_found = 0
    
    for prod_id, prod_title, prod_asin in products_to_check:
        log(f"\nChecking: [{prod_asin}] {prod_title[:60]}")
        kw = extract_recall_keywords(prod_title)
        log(f"  Brand: '{kw['brand']}' | Type: '{kw['product_type']}'")
        
        try:
            # Check CPSC first (most Amazon products)
            match = check_cpsc_recalls_for_product(prod_title)
            
            if match:
                matches_found += 1
                recall_title = match.get('Title', 'Unknown recall')
                recall_num = match.get('RecallNumber', '')
                recall_date = match.get('RecallDate', '')
                log(f"  ⚠️ CPSC MATCH: {recall_title[:60]} (#{recall_num})")
                log(f"     Recall Date: {recall_date[:10] if recall_date else 'N/A'}")
                
                hazard = ''
                for h in match.get('Hazards', []):
                    hazard = h.get('Name', '')[:500]
                    break
                
                remedy = ''
                for r in match.get('Remedies', []):
                    remedy = r.get('Name', '')[:500]
                    break
                
                contact = match.get('ConsumerContact', '')[:500]
                
                results[prod_id] = {
                    'recall_id': match.get('RecallID'),
                    'recall_number': recall_num,
                    'recall_title': recall_title[:500],
                    'recall_description': match.get('Description', '')[:1000],
                    'recall_url': match.get('URL', ''),
                    'recall_hazard': hazard,
                    'recall_remedy': remedy,
                    'recall_date': recall_date,
                    'recall_consumer_contact': contact,
                    'recall_source': 'cpsc',
                }
            else:
                # No CPSC match — try openFDA
                fda_match = check_fda_recalls_for_product(prod_title)
                if fda_match:
                    normalized = normalize_fda_to_recall_data(fda_match)
                    if normalized:
                        matches_found += 1
                        log(f"  ⚠️ FDA MATCH: {normalized['recall_title'][:60]}")
                        log(f"     Recall Date: {normalized.get('recall_date', 'N/A')}")
                        results[prod_id] = normalized
                else:
                    log(f"  ✅ No recalls found (CPSC + FDA)")
        except Exception as e:
            log(f"  ERROR: {e}")
        
        time.sleep(1)  # Rate limiting between products
    
    log(f"\n{'=' * 60}")
    log(f"RECALL SCAN COMPLETE: {matches_found} matches out of {len(products_to_check)} products")
    log(f"{'=' * 60}\n")
    
    return results, matches_found


def apply_recall_to_product(product, recall_data):
    """Apply recall scan results to a product record."""
    product.recall_status = 'matched'
    product.recall_id = recall_data.get('recall_id')
    product.recall_number = recall_data.get('recall_number')
    product.recall_title = recall_data.get('recall_title')
    product.recall_description = recall_data.get('recall_description')
    product.recall_url = recall_data.get('recall_url')
    product.recall_hazard = recall_data.get('recall_hazard')
    product.recall_remedy = recall_data.get('recall_remedy')
    product.recall_date = recall_data.get('recall_date')
    product.recall_consumer_contact = recall_data.get('recall_consumer_contact')
    product.last_recall_check = datetime.now()


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)
# Generate and persist a secret key for session security
_app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
_secret_key_file = os.path.join(_app_dir, '.flask_secret')
if os.path.exists(_secret_key_file):
    with open(_secret_key_file, 'r') as f: app.secret_key = f.read().strip()
else:
    import secrets
    app.secret_key = secrets.token_hex(32)
    try:
        with open(_secret_key_file, 'w') as f: f.write(app.secret_key)
    except: pass  # Fall back to ephemeral key if can't write
next_run_time_global = None

@app.route('/static/<path:f>')
def static_files(f): return send_from_directory('static', f)

@app.route('/')
def index():
    sort = request.args.get('sort', 'newest')
    with get_session() as s:
        products = s.query(Product).filter_by(is_archived=False).all()
        
        # Sort products based on parameter
        if sort == 'oldest':
            products.sort(key=lambda p: p.created_at or datetime.min)
        elif sort == 'order_date':
            products.sort(key=lambda p: p.order_date or datetime.min, reverse=True)
        elif sort == 'price_low':
            products.sort(key=lambda p: p.current_new_price or 99999)
        elif sort == 'price_high':
            products.sort(key=lambda p: p.current_new_price or 0, reverse=True)
        elif sort == 'last_checked':
            products.sort(key=lambda p: p.last_checked or datetime.min, reverse=True)
        elif sort == 'biggest_drop':
            # Sort by dollar drop from purchase/highest price
            def get_drop(p):
                if not p.current_new_price: return 0
                ref = p.purchase_price or p.highest_new_price or p.current_new_price
                return ref - p.current_new_price
            products.sort(key=get_drop, reverse=True)
        elif sort == 'pct_drop':
            # Sort by percent drop from purchase/highest price
            def get_pct(p):
                if not p.current_new_price: return 0
                ref = p.purchase_price or p.highest_new_price or p.current_new_price
                if ref <= 0: return 0
                return (ref - p.current_new_price) / ref * 100
            products.sort(key=get_pct, reverse=True)
        elif sort == 'name':
            products.sort(key=lambda p: (p.title or '').lower())
        else:  # newest (default)
            products.sort(key=lambda p: p.created_at or datetime.min, reverse=True)
        
        settings = s.query(Settings).first()
        now = datetime.now()
        today = now.replace(hour=0,minute=0,second=0,microsecond=0)
        stats = {
            'active': len(products),
            'alerts_today': sum(1 for p in products if p.last_alert_sent and p.last_alert_sent >= today),
            'at_target': sum(1 for p in products if p.target_price and ((p.current_new_price and p.current_new_price <= p.target_price) or (p.current_used_price and p.current_used_price <= p.target_price))),
            'from_orders': sum(1 for p in products if p.source == 'email'),
            'recalls': sum(1 for p in products if p.recall_status == 'matched')
        }
        last_run = max([p.last_checked for p in products if p.last_checked], default=None)
        email_configured = bool(settings.email_address and settings.email_password)
        update_ver, update_url = check_for_updates()
        return render_template_string(INDEX_TPL, products=products, settings=settings, stats=stats, 
            last_run_time=last_run.strftime("%m/%d %I:%M%p") if last_run else "Never",
            next_run_time=next_run_time_global.strftime("%I:%M%p") if next_run_time_global else None, 
            now=now, email_configured=email_configured, current_sort=sort,
            update_available=update_ver is not None, update_version=update_ver, update_url=update_url, current_version=APP_VERSION)

@app.route('/archive')
def archive_page():
    with get_session() as s:
        return render_template_string(ARCHIVE_TPL, products=s.query(Product).filter_by(is_archived=True).order_by(Product.archived_at.desc()).all(), now=datetime.now())

@app.route('/api/save-email', methods=['POST'])
def api_save_email():
    try:
        data = request.get_json()
        with get_session() as s:
            st = s.query(Settings).first()
            if data.get('email'): st.email_address = data['email'].strip()
            if data.get('password'): st.email_password = data['password']
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/scan-orders', methods=['POST'])
def api_scan_orders():
    """Import orders from email - ASIN extracted directly from email, no Amazon search needed"""
    try:
        with get_session() as s:
            st = s.query(Settings).first()
            if not st.email_address or not st.email_password:
                return jsonify({'success': False, 'error': 'Email not configured'})
            
            # Scan emails - now returns ASINs directly extracted from email
            orders, debug_info = scan_amazon_orders(st.email_address, st.email_password, days_back=32)
            
            if not orders:
                st.last_email_scan = datetime.now()
                return jsonify({
                    'success': True, 
                    'added': 0, 
                    'message': 'No new orders found (check import_log.txt for details)',
                    'debug': debug_info
                })
            
            added = 0
            already_tracked = 0
            
            for order in orders:
                asin = order.get('asin')
                if not asin:
                    continue
                
                # Check if ASIN already exists
                existing = s.query(Product).filter_by(asin=asin).first()
                if existing:
                    if existing.is_archived:
                        # Restore from archive
                        existing.is_archived = False
                        existing.archived_at = None
                        existing.source = 'email'
                        existing.order_id = order.get('order_id')
                        existing.order_date = order.get('order_date')
                        if order.get('item_price'):
                            existing.purchase_price = order['item_price']
                            existing.target_price = order['item_price'] - 0.01
                        # Expiration from order date (return window), not import date
                        if st.default_expiration_days > 0:
                            base_date = order.get('order_date') or datetime.now()
                            existing.expires_at = base_date + timedelta(days=st.default_expiration_days)
                        added += 1
                    else:
                        already_tracked += 1
                    continue
                
                # Get item price and set target price to 1 cent below purchase price
                item_price = order.get('item_price')
                target_price = None
                if item_price and item_price > 0:
                    target_price = item_price - 0.01
                
                # Expiration from order date (return window), not import date
                base_date = order.get('order_date') or datetime.now()
                exp = base_date + timedelta(days=st.default_expiration_days) if st.default_expiration_days > 0 else None
                s.add(Product(
                    asin=asin,
                    url=f"https://www.amazon.com/dp/{asin}",
                    title=order.get('product_name', f"Order Item {asin}")[:200],
                    source='email',
                    order_date=order.get('order_date'),
                    order_id=order.get('order_id'),
                    purchase_price=item_price,
                    target_price=target_price,
                    created_at=datetime.now(),
                    expires_at=exp
                ))
                added += 1
            
            st.last_email_scan = datetime.now()
            
            msg = f'Found {len(orders)} orders'
            if added: msg += f', added {added} new'
            if already_tracked: msg += f', {already_tracked} already tracked'
            msg += ' (see import_log.txt for details)'
            
            return jsonify({
                'success': True, 
                'added': added, 
                'message': msg,
                'debug': debug_info
            })
    except Exception as e:
        logger.error(f"Order scan error: {e}")
        return jsonify({'success': False, 'error': str(e)})
@app.route('/api/product/<int:pid>/settings', methods=['POST'])
def api_product_settings(pid):
    try:
        data = request.get_json()
        with get_session() as s:
            p = s.get(Product, pid)
            if not p: return jsonify({'success': False, 'error': 'Not found'})
            p.alert_new_pct = float(data['alert_new_pct']) if data.get('alert_new_pct') else None
            p.alert_new_dollars = float(data['alert_new_dollars']) if data.get('alert_new_dollars') else None
            p.alert_used_pct = float(data['alert_used_pct']) if data.get('alert_used_pct') else None
            p.alert_used_dollars = float(data['alert_used_dollars']) if data.get('alert_used_dollars') else None
            p.target_price = float(data['target_price']) if data.get('target_price') else None
            p.purchase_price = float(data['purchase_price']) if data.get('purchase_price') else None
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/check/<int:pid>', methods=['POST'])
def api_check(pid):
    # Log file for check operations
    log_file = os.path.join(os.getcwd(), 'check_log.txt')
    _rotate_log(log_file)
    def log(msg):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{timestamp}] {msg}"
        logger.info(msg)
        try:
            with open(log_file, 'a') as f:
                f.write(line + '\n')
        except:
            pass
    
    try:
        with get_session() as s:
            p = s.get(Product, pid)
            if not p: 
                log(f"CHECK FAILED: Product {pid} not found")
                return jsonify({'success': False, 'error': 'Not found'})
            asin = p.asin
            title = p.title[:40] if p.title else 'Unknown'
        
        log(f"CHECK START: {asin} - {title}")
        
        future = executor.submit(run_scraper, asin)
        try: 
            data = future.result(timeout=SCRAPE_TIMEOUT)
        except FuturesTimeout: 
            log(f"CHECK TIMEOUT: {asin} after {SCRAPE_TIMEOUT}s")
            return jsonify({'success': False, 'error': f'Timeout after {SCRAPE_TIMEOUT}s'})
        
        if data.get('error') and not data.get('new_price') and not data.get('used_price'):
            log(f"CHECK ERROR: {asin} - {data['error']}")
            return jsonify({'success': False, 'error': data['error']})
        
        log(f"CHECK RESULT: {asin} - New: {data.get('new_price')}, Used: {data.get('used_price')}, Title: {data.get('title', 'N/A')[:30]}")
        
        with get_session() as s:
            p = s.get(Product, pid)
            if p:
                p.update_from_scrape(data)
                if data.get('title') and p.title == data['title']:
                    log(f"CHECK UPDATED TITLE: {asin} -> {data['title'][:40]}")
                parts = []
                if data.get('new_price'): parts.append(f"New: ${data['new_price']:.2f}")
                if data.get('used_price'): parts.append(f"Used: ${data['used_price']:.2f}")
                result_msg = ' | '.join(parts) if parts else 'No prices found'
                log(f"CHECK COMPLETE: {asin} - {result_msg}")
                return jsonify({'success': True, 'message': result_msg})
        log(f"CHECK DB ERROR: {asin}")
        return jsonify({'success': False, 'error': 'DB error'})
    except Exception as e:
        log(f"CHECK EXCEPTION: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test-email', methods=['POST'])
def api_test_email():
    try:
        with get_session() as s:
            st = s.query(Settings).first()
            if not st.email_address or not st.email_password:
                return jsonify({'success': False, 'error': 'Email not configured'})
            p = s.query(Product).filter(Product.screenshot_main != None).first()
            msg = MIMEMultipart()
            msg['Subject'] = "🧪 Price Tracker - Test Email"
            msg['From'] = st.email_address
            msg['To'] = st.email_address
            body = f"Test email from Amazon Price Tracker! ✅\n\nYour email settings work correctly.\n\n--- Sample Alert ---\n📦 Product: {p.title if p else 'Example Product'}\n🔗 Link: {p.url if p else 'https://amazon.com/dp/B08N5WRWNW'}\n\n💰 Price Alert:\n   • NEW: $129.99 → $99.99 (23% drop!)\n   • USED: $79.99 (hit target $85.00)\n\nScreenshot attached (when available).\n---\nSettings: http://{APP_NAME}.localhost:{DEFAULT_PORT}/settings"
            msg.attach(MIMEText(body, 'plain'))
            if p and p.screenshot_main:
                path = os.path.join('static', 'screenshots', p.screenshot_main)
                if os.path.exists(path):
                    with open(path, 'rb') as f:
                        img = MIMEImage(f.read())
                        img.add_header('Content-Disposition', 'attachment', filename='screenshot.png')
                        msg.attach(img)
            with smtplib.SMTP(st.smtp_server, st.smtp_port, timeout=30) as srv:
                srv.starttls(); srv.login(st.email_address, st.email_password); srv.send_message(msg)
            return jsonify({'success': True})
    except smtplib.SMTPAuthenticationError: return jsonify({'success': False, 'error': 'Auth failed - check app password'})
    except Exception as e: return jsonify({'success': False, 'error': str(e)})

@app.route('/api/scan-recalls', methods=['POST'])
def api_scan_recalls():
    """Manually trigger a CPSC + FDA recall scan for ALL products (active AND archived)"""
    try:
        with get_session() as s:
            # Check ALL products — recalls apply forever, not just during tracking window
            products = s.query(Product).all()
            to_check = [(p.id, p.title, p.asin) for p in products 
                        if p.title and 'Loading' not in (p.title or '') and p.recall_status not in ('matched', 'dismissed')]
            
            if not to_check:
                return jsonify({'success': True, 'message': 'No products to scan (all loading, already matched, or dismissed)'})
            
            results, matches_found = run_recall_scan(to_check)
            
            # Apply results to database
            for prod_id, recall_data in results.items():
                prod = s.get(Product, prod_id)
                if prod:
                    apply_recall_to_product(prod, recall_data)
            
            # Mark checked products with no match
            for prod_id, _, _ in to_check:
                if prod_id not in results:
                    prod = s.get(Product, prod_id)
                    if prod and prod.recall_status not in ('matched', 'dismissed'):
                        prod.recall_status = 'none'
                        prod.last_recall_check = datetime.now()
            
            # Update last scan time
            st = s.query(Settings).first()
            if st:
                st.last_recall_scan = datetime.now()
            
            # Send email alert for new recalls
            if matches_found > 0 and st and st.email_address:
                send_recall_alert_email(results, s, st)
            
            return jsonify({
                'success': True, 
                'message': f'Scanned {len(to_check)} products, found {matches_found} recall(s). See recall_log.txt for details.'
            })
    except Exception as e:
        logger.error(f"Recall scan error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dismiss-recall/<int:pid>', methods=['POST'])
def api_dismiss_recall(pid):
    """Dismiss a recall alert for a product"""
    try:
        with get_session() as s:
            p = s.get(Product, pid)
            if not p:
                return jsonify({'success': False, 'error': 'Not found'})
            if p.recall_status == 'dismissed':
                # Re-check: clear recall data and re-scan
                p.recall_status = 'none'
                p.recall_id = None
                p.recall_number = None
                p.recall_title = None
                p.recall_description = None
                p.recall_url = None
                p.recall_hazard = None
                p.recall_remedy = None
                p.recall_date = None
                p.recall_consumer_contact = None
                p.last_recall_check = None
                return jsonify({'success': True, 'message': 'Recall cleared, will re-check on next scan'})
            else:
                p.recall_status = 'dismissed'
                return jsonify({'success': True, 'message': 'Recall dismissed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/recalls')
def recalls_page():
    """Dedicated page showing all recall information (includes archived products)"""
    with get_session() as s:
        matched = s.query(Product).filter_by(recall_status='matched').all()
        dismissed = s.query(Product).filter_by(recall_status='dismissed').all()
        st = s.query(Settings).first()
        total_products = s.query(Product).count()
        return render_template_string(RECALLS_TPL, matched=matched, dismissed=dismissed, settings=st, now=datetime.now(), total_products=total_products)

@app.route('/check-all', methods=['POST'])
def check_all():
    with get_session() as s:
        products = s.query(Product).filter_by(is_archived=False, is_active=True).all()
        checked = 0
        for prod in products:
            try:
                data = run_scraper(prod.asin)
                if not data.get('error'):
                    prod.update_from_scrape(data)
                    checked += 1
                    s.commit()
            except Exception as e: logger.error(f"Error {prod.asin}: {e}")
            time.sleep(random.uniform(4, 8))
        flash(f'Checked {checked}/{len(products)}', 'success')
    return redirect('/')

@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    with get_session() as s:
        st = s.query(Settings).first()
        if request.method == 'POST':
            st.email_address = request.form.get('email', '').strip()
            st.email_password = request.form.get('password', '')
            try:
                st.default_expiration_days = int(request.form.get('expiration_days', 32))
                st.auto_archive = request.form.get('auto_archive') == '1'
                st.auto_import_orders = request.form.get('auto_import') == '1'
                st.import_frequency = request.form.get('import_frequency', 'every_12h')
                st.check_interval_minutes = max(60, int(request.form.get('check_interval', DEFAULT_INTERVAL_MINUTES)))
                # Global alert settings
                st.global_alerts_enabled = request.form.get('global_alerts_enabled') == '1'
                st.global_new_pct = float(request.form.get('global_new_pct')) if request.form.get('global_new_pct', '').strip() else None
                st.global_used_pct = float(request.form.get('global_used_pct')) if request.form.get('global_used_pct', '').strip() else None
                st.global_new_dollars = float(request.form.get('global_new_dollars')) if request.form.get('global_new_dollars', '').strip() else None
                st.global_used_dollars = float(request.form.get('global_used_dollars')) if request.form.get('global_used_dollars', '').strip() else None
                st.batch_email_alerts = request.form.get('batch_email_alerts') == '1'
                st.recall_scan_enabled = request.form.get('recall_scan_enabled') == '1'
                st.recall_scan_frequency = request.form.get('recall_scan_frequency', 'daily')
                new_startup = request.form.get('run_at_startup') == '1'
                if new_startup != st.run_at_startup:
                    _manage_startup_shortcut(new_startup)
                    st.run_at_startup = new_startup
            except: flash('Invalid values', 'error'); return redirect('/settings')
            flash('Saved!', 'success'); return redirect('/settings')
        min_hours = (st.check_interval_minutes - INTERVAL_JITTER_MINUTES) / 60
        max_hours = (st.check_interval_minutes + INTERVAL_JITTER_MINUTES) / 60
        return render_template_string(SETTINGS_TPL, settings=st, jitter=INTERVAL_JITTER_MINUTES, min_hours=f"{min_hours:.1f}", max_hours=f"{max_hours:.1f}")

@app.route('/add', methods=['POST'])
def add_product():
    urls = request.form.get('urls', '').splitlines()
    target = float(request.form.get('price')) if request.form.get('price', '').strip() else None
    exp_str = request.form.get('expiration', '').strip()
    added = 0
    with get_session() as s:
        st = s.query(Settings).first()
        exp = None if exp_str == '0' else (datetime.now() + timedelta(days=int(exp_str))) if exp_str else (datetime.now() + timedelta(days=st.default_expiration_days)) if st.default_expiration_days > 0 else None
        for url in urls:
            asin = extract_asin(url.strip())
            if not asin: continue
            ex = s.query(Product).filter_by(asin=asin).first()
            if ex:
                if ex.is_archived:
                    ex.is_archived = False; ex.archived_at = None; ex.created_at = datetime.now(); ex.expires_at = exp
                    if target: ex.target_price = target
                    added += 1
                continue
            s.add(Product(asin=asin, url=f"https://www.amazon.com/dp/{asin}", target_price=target, title=f"Loading... {asin}", source='manual', created_at=datetime.now(), expires_at=exp))
            added += 1
    flash(f'Added {added}' if added else 'None added', 'success' if added else 'error')
    return redirect('/')

@app.route('/delete/<int:pid>', methods=['POST'])
def delete_product(pid):
    with get_session() as s:
        p = s.get(Product, pid)
        if p: s.delete(p); flash('Deleted', 'success')
    return redirect(request.referrer or '/')

@app.route('/archive/<int:pid>', methods=['POST'])
def archive_product(pid):
    with get_session() as s:
        p = s.get(Product, pid)
        if p: p.is_archived = True; p.archived_at = datetime.now(); flash('Archived', 'success')
    return redirect('/')

@app.route('/restore/<int:pid>', methods=['POST'])
def restore_product(pid):
    with get_session() as s:
        p = s.get(Product, pid)
        st = s.query(Settings).first()
        if p:
            p.is_archived = False; p.archived_at = None; p.created_at = datetime.now()
            if st.default_expiration_days > 0: p.expires_at = datetime.now() + timedelta(days=st.default_expiration_days)
            flash('Restored', 'success')
    return redirect('/archive')

@app.route('/archive-expired', methods=['POST'])
def archive_expired():
    c = 0
    with get_session() as s:
        now = datetime.now()
        for p in s.query(Product).filter(Product.is_archived == False, Product.expires_at != None, Product.expires_at < now).all():
            p.is_archived = True; p.archived_at = now; c += 1
    flash(f'Archived {c}', 'success')
    return redirect('/')

@app.route('/delete-all-archived', methods=['POST'])
def delete_all_archived():
    with get_session() as s:
        c = s.query(Product).filter_by(is_archived=True).delete()
        flash(f'Deleted {c}', 'success')
    return redirect('/archive')

@app.route('/clear-all', methods=['POST'])
def clear_all():
    with get_session() as s:
        c = s.query(Product).filter_by(is_archived=False).delete()
        flash(f'Cleared {c} products', 'success')
    return redirect('/')

def send_alert_email(subject, body, settings, screenshot_path=None):
    if not settings.email_address or not settings.email_password: return False
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = settings.email_address
        msg['To'] = settings.email_address
        msg.attach(MIMEText(body, 'plain'))
        if screenshot_path and os.path.exists(screenshot_path):
            with open(screenshot_path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-Disposition', 'attachment', filename='screenshot.png')
                msg.attach(img)
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port, timeout=30) as srv:
            srv.starttls(); srv.login(settings.email_address, settings.email_password); srv.send_message(msg)
        return True
    except: return False


def send_batched_alert_email(alerts_list, settings):
    """Send a single email containing multiple price drop alerts"""
    if not settings.email_address or not settings.email_password or not alerts_list:
        return False
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f"🔔 Price Alert: {len(alerts_list)} item(s) dropped!"
        msg['From'] = settings.email_address
        msg['To'] = settings.email_address
        
        # Build email body
        body_parts = [f"📊 Price Drop Summary - {len(alerts_list)} items\n" + "="*50 + "\n"]
        
        for alert in alerts_list:
            product = alert['product']
            alert_msgs = alert['alerts']
            
            body_parts.append(f"\n📦 {product.title}\n")
            if product.purchase_price:
                body_parts.append(f"   💰 Paid: ${product.purchase_price:.2f}\n")
            if product.current_new_price:
                body_parts.append(f"   🆕 New: ${product.current_new_price:.2f}\n")
            if product.current_used_price:
                body_parts.append(f"   ♻️ Used: ${product.current_used_price:.2f}\n")
            for a in alert_msgs:
                body_parts.append(f"   {a}\n")
            body_parts.append(f"   🔗 {product.url}\n")
            body_parts.append("-"*50 + "\n")
        
        msg.attach(MIMEText(''.join(body_parts), 'plain'))
        
        # Attach screenshots (up to 5 to avoid huge emails)
        screenshot_count = 0
        for alert in alerts_list[:5]:
            product = alert['product']
            if product.screenshot_main:
                ss_path = os.path.join('static', 'screenshots', product.screenshot_main)
                if os.path.exists(ss_path):
                    with open(ss_path, 'rb') as f:
                        img = MIMEImage(f.read())
                        img.add_header('Content-Disposition', 'attachment', filename=f'{product.asin}_screenshot.png')
                        msg.attach(img)
                        screenshot_count += 1
        
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port, timeout=30) as srv:
            srv.starttls()
            srv.login(settings.email_address, settings.email_password)
            srv.send_message(msg)
        logger.info(f"Sent batched alert email with {len(alerts_list)} items, {screenshot_count} screenshots")
        return True
    except Exception as e:
        logger.error(f"Failed to send batched email: {e}")
        return False


def send_recall_alert_email(recall_results, session, settings):
    """Send a high-priority email alert for product recalls"""
    if not settings.email_address or not settings.email_password or not recall_results:
        return False
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f"🚨 URGENT: {len(recall_results)} Product Recall(s) Detected!"
        msg['From'] = settings.email_address
        msg['To'] = settings.email_address
        msg['X-Priority'] = '1'  # High priority
        
        body_parts = [
            f"🚨 PRODUCT RECALL ALERT\n",
            f"{'='*50}\n",
            f"{len(recall_results)} of your Amazon purchases have been matched\n",
            f"to CPSC and/or FDA recall databases.\n",
            f"{'='*50}\n\n",
        ]
        
        for prod_id, recall_data in recall_results.items():
            prod = session.get(Product, prod_id)
            if not prod:
                continue
            
            body_parts.append(f"⚠️ {prod.title}\n")
            body_parts.append(f"   Amazon: {prod.url}\n")
            if recall_data.get('recall_title'):
                body_parts.append(f"   Recall: {recall_data['recall_title']}\n")
            if recall_data.get('recall_hazard'):
                body_parts.append(f"   🔴 Hazard: {recall_data['recall_hazard'][:300]}\n")
            if recall_data.get('recall_remedy'):
                body_parts.append(f"   ✅ Remedy: {recall_data['recall_remedy'][:300]}\n")
            if recall_data.get('recall_consumer_contact'):
                body_parts.append(f"   📞 Contact: {recall_data['recall_consumer_contact'][:200]}\n")
            if recall_data.get('recall_url'):
                body_parts.append(f"   📋 CPSC Details: {recall_data['recall_url']}\n")
            body_parts.append(f"{'─'*50}\n\n")
        
        body_parts.append("⚠️ STOP USING any recalled products immediately.\n")
        body_parts.append("Visit the CPSC links above for full details and remedies.\n\n")
        body_parts.append("---\nAmazon Price Tracker - Recall Monitor\n")
        body_parts.append(f"http://{APP_NAME}.localhost:{DEFAULT_PORT}/recalls\n")
        
        msg.attach(MIMEText(''.join(body_parts), 'plain'))
        
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port, timeout=30) as srv:
            srv.starttls()
            srv.login(settings.email_address, settings.email_password)
            srv.send_message(msg)
        logger.info(f"Sent recall alert email for {len(recall_results)} products")
        return True
    except Exception as e:
        logger.error(f"Failed to send recall alert email: {e}")
        return False

shutdown_requested = threading.Event()

def run_cycle():
    batched_alerts = []  # Collect alerts for batch email
    
    with get_session() as s:
        st = s.query(Settings).first()
        
        # Get global threshold settings
        use_global = st.global_alerts_enabled
        global_new_pct = st.global_new_pct if use_global else None
        global_new_dollars = st.global_new_dollars if use_global else None
        global_used_pct = st.global_used_pct if use_global else None
        global_used_dollars = st.global_used_dollars if use_global else None
        batch_emails = st.batch_email_alerts
        
        if st.auto_import_orders and st.email_address and st.email_password:
            # Determine import interval based on frequency setting
            import_freq = getattr(st, 'import_frequency', 'every_12h') or 'every_12h'
            if import_freq == 'every_6h':
                import_interval = timedelta(hours=6)
            elif import_freq == 'every_12h':
                import_interval = timedelta(hours=12)
            elif import_freq == 'daily':
                import_interval = timedelta(hours=24)
            else:
                import_interval = timedelta(hours=12)
            
            if not st.last_email_scan or datetime.now() - st.last_email_scan > import_interval:
                try:
                    products, _ = scan_amazon_orders(st.email_address, st.email_password, days_back=7)
                    for prod in products:
                        existing = s.query(Product).filter_by(asin=prod['asin']).first()
                        if existing:
                            # Restore archived products on re-order
                            if existing.is_archived:
                                existing.is_archived = False
                                existing.archived_at = None
                                existing.source = 'email'
                                existing.order_id = prod.get('order_id')
                                existing.order_date = prod.get('order_date')
                                if prod.get('item_price'):
                                    existing.purchase_price = prod['item_price']
                                    existing.target_price = prod['item_price'] - 0.01
                                if st.default_expiration_days > 0:
                                    base_date = prod.get('order_date') or datetime.now()
                                    existing.expires_at = base_date + timedelta(days=st.default_expiration_days)
                            continue
                        base_date = prod.get('order_date') or datetime.now()
                        exp = base_date + timedelta(days=st.default_expiration_days) if st.default_expiration_days > 0 else None
                        item_price = prod.get('item_price')
                        target = (item_price - 0.01) if item_price else None
                        s.add(Product(asin=prod['asin'], url=f"https://www.amazon.com/dp/{prod['asin']}", 
                            title=prod.get('product_name', f"Loading... {prod['asin']}"), source='email',
                            order_date=prod.get('order_date'), order_id=prod.get('order_id'),
                            purchase_price=item_price, target_price=target,
                            created_at=datetime.now(), expires_at=exp))
                    st.last_email_scan = datetime.now()
                    s.commit()
                except Exception as e:
                    logger.error(f"Auto-import error: {e}")
        
        # Auto recall scan
        if st.recall_scan_enabled:
            should_scan = False
            if st.recall_scan_frequency == 'every_check':
                should_scan = True
            elif st.recall_scan_frequency == 'daily':
                should_scan = not st.last_recall_scan or datetime.now() - st.last_recall_scan > timedelta(hours=24)
            elif st.recall_scan_frequency == 'weekly':
                should_scan = not st.last_recall_scan or datetime.now() - st.last_recall_scan > timedelta(days=7)
            
            if should_scan:
                try:
                    # Check ALL products (active + archived) — recalls apply forever
                    all_products = s.query(Product).all()
                    to_check = [(p.id, p.title, p.asin) for p in all_products 
                                if p.title and 'Loading' not in (p.title or '') and p.recall_status not in ('matched', 'dismissed')]
                    
                    if to_check:
                        logger.info(f"Auto recall scan: checking {len(to_check)} products")
                        results, matches_found = run_recall_scan(to_check)
                        
                        for prod_id, recall_data in results.items():
                            prod = s.get(Product, prod_id)
                            if prod:
                                apply_recall_to_product(prod, recall_data)
                        
                        for prod_id, _, _ in to_check:
                            if prod_id not in results:
                                prod = s.get(Product, prod_id)
                                if prod and prod.recall_status not in ('matched', 'dismissed'):
                                    prod.recall_status = 'none'
                                    prod.last_recall_check = datetime.now()
                        
                        if matches_found > 0:
                            send_recall_alert_email(results, s, st)
                    
                    st.last_recall_scan = datetime.now()
                    s.commit()
                except Exception as e:
                    logger.error(f"Auto recall scan error: {e}")
        
        if st.auto_archive:
            now = datetime.now()
            for p in s.query(Product).filter(Product.is_archived == False, Product.expires_at != None, Product.expires_at < now).all():
                p.is_archived = True; p.archived_at = now
        
        products = s.query(Product).filter_by(is_archived=False, is_active=True).all()
        if not products: return
        logger.info(f"Cycle: {len(products)} products (global alerts: {'ON' if use_global else 'OFF'})")
        
        for prod in products:
            if shutdown_requested.is_set(): break
            try:
                data = run_scraper(prod.asin)
                if not data.get('error'):
                    prod.update_from_scrape(data)
                    
                    # Check for alerts
                    alerts = []
                    
                    if data.get('new_price'):
                        # Target price check (not affected by global)
                        if prod.target_price and data['new_price'] <= prod.target_price:
                            alerts.append(f"🎯 NEW ${data['new_price']:.2f} hit target ${prod.target_price:.2f}")
                        
                        # Threshold check (use global if enabled)
                        if prod.should_alert_new(data['new_price'], global_new_pct, global_new_dollars):
                            ref_price = prod.purchase_price or prod.highest_new_price or prod.prev_new_price
                            if ref_price and ref_price > 0:
                                drop_pct = (ref_price - data['new_price']) / ref_price * 100
                                drop_dollars = ref_price - data['new_price']
                                paid_str = f" (paid ${prod.purchase_price:.2f})" if prod.purchase_price else ""
                                alerts.append(f"📉 NEW dropped {drop_pct:.1f}% (${drop_dollars:.2f}) to ${data['new_price']:.2f}{paid_str}")
                    
                    if data.get('used_price'):
                        # Target price check (not affected by global)
                        if prod.target_price and data['used_price'] <= prod.target_price:
                            alerts.append(f"🎯 USED ${data['used_price']:.2f} hit target ${prod.target_price:.2f}")
                        
                        # Threshold check (use global if enabled)
                        if prod.should_alert_used(data['used_price'], global_used_pct, global_used_dollars):
                            ref_price = prod.highest_used_price or prod.purchase_price or prod.prev_used_price
                            if ref_price and ref_price > 0:
                                drop_pct = (ref_price - data['used_price']) / ref_price * 100
                                drop_dollars = ref_price - data['used_price']
                                paid_str = f" (paid ${prod.purchase_price:.2f})" if prod.purchase_price else ""
                                alerts.append(f"📉 USED dropped {drop_pct:.1f}% (${drop_dollars:.2f}) to ${data['used_price']:.2f}{paid_str}")
                    
                    # Process alerts
                    if alerts and (not prod.last_alert_sent or datetime.now() - prod.last_alert_sent > timedelta(hours=ALERT_COOLDOWN_HOURS)):
                        if batch_emails:
                            # Collect for batched email
                            batched_alerts.append({'product': prod, 'alerts': alerts})
                            prod.last_alert_sent = datetime.now()
                        else:
                            # Send individual email
                            body = f"📦 {prod.title}\n"
                            if prod.purchase_price:
                                body += f"💰 You paid: ${prod.purchase_price:.2f}\n"
                            body += f"\n" + "\n".join(alerts) + f"\n\n🔗 {prod.url}"
                            ss_path = os.path.join('static', 'screenshots', prod.screenshot_main) if prod.screenshot_main else None
                            if send_alert_email(f"📦 {prod.title[:40]}", body, st, ss_path): 
                                prod.last_alert_sent = datetime.now()
                    s.commit()
            except Exception as e: logger.error(f"Error {prod.asin}: {e}")
            time.sleep(random.uniform(5, 10))
        
        # Send batched email if any alerts collected
        if batched_alerts and batch_emails:
            if send_batched_alert_email(batched_alerts, st):
                logger.info(f"Sent batched alert for {len(batched_alerts)} products")
            s.commit()

def manager_loop():
    global next_run_time_global
    while not shutdown_requested.is_set():
        try: run_cycle()
        except Exception as e: logger.error(f"Cycle error: {e}")
        with get_session() as s:
            st = s.query(Settings).first()
            base_interval = (st.check_interval_minutes if st else DEFAULT_INTERVAL_MINUTES) * 60
        jitter_seconds = random.uniform(-INTERVAL_JITTER_MINUTES * 60, INTERVAL_JITTER_MINUTES * 60)
        wait = int(base_interval + jitter_seconds)
        next_run_time_global = datetime.now() + timedelta(seconds=wait)
        logger.info(f"Next check: {next_run_time_global.strftime('%I:%M%p')} ({wait//60}m)")
        for _ in range(wait):
            if shutdown_requested.is_set(): break
            time.sleep(1)

def signal_handler(sig, frame): shutdown_requested.set()

def ensure_single_instance():
    """Prevent multiple instances. If another is running, try to kill it gracefully."""
    import sys, socket
    pid_path = os.path.join(os.getcwd(), PID_FILE)
    
    # Check if port is already in use (fastest check)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1)
        sock.connect(('127.0.0.1', DEFAULT_PORT))
        sock.close()
        # Port is in use — another instance is running
        logger.warning(f"Port {DEFAULT_PORT} already in use — another instance may be running.")
        
        # Try to read old PID and kill it
        if os.path.exists(pid_path):
            try:
                with open(pid_path, 'r') as f:
                    old_pid = int(f.read().strip())
                if old_pid != os.getpid():
                    logger.info(f"Terminating previous instance (PID {old_pid})...")
                    try:
                        os.kill(old_pid, signal.SIGTERM)
                        time.sleep(2)  # Give it time to shut down
                    except ProcessLookupError:
                        pass  # Already dead
                    except PermissionError:
                        logger.warning(f"Cannot kill PID {old_pid} — permission denied. Please close it manually.")
                        sys.exit(1)
            except (ValueError, IOError):
                pass
        
        # Check again after killing
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock2.settimeout(1)
            sock2.connect(('127.0.0.1', DEFAULT_PORT))
            sock2.close()
            logger.error(f"Port {DEFAULT_PORT} still in use after kill attempt. Close the other instance first.")
            sys.exit(1)
        except (ConnectionRefusedError, socket.timeout, OSError):
            pass  # Port freed — we're good
    except (ConnectionRefusedError, socket.timeout, OSError):
        pass  # Port is free — no other instance
    finally:
        try: sock.close()
        except: pass
    
    # Write our PID
    with open(pid_path, 'w') as f:
        f.write(str(os.getpid()))
    
    # Cleanup PID file on exit
    import atexit
    def cleanup_pid():
        try: os.remove(pid_path)
        except: pass
    atexit.register(cleanup_pid)

def get_friendly_url():
    """Return the user-friendly URL for the tracker."""
    return f"http://{APP_NAME}.localhost:{DEFAULT_PORT}"

def get_fallback_url():
    """Return the fallback URL if friendly hostname doesn't work."""
    return f"http://127.0.0.1:{DEFAULT_PORT}"

# ============================================================
# WINDOWS STARTUP MANAGEMENT
# ============================================================

def _manage_startup_shortcut(enable):
    """Add or remove the app from Windows startup."""
    if sys.platform != 'win32':
        return  # Only works on Windows
    
    try:
        startup_folder = os.path.join(os.environ.get('APPDATA', ''), 
                                       'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        if not os.path.isdir(startup_folder):
            return
        
        shortcut_path = os.path.join(startup_folder, 'AmazonPriceTracker.vbs')
        
        if enable:
            # Get the path to the current script or EXE
            if getattr(sys, 'frozen', False):
                # Running as EXE
                app_path = sys.executable
                script_content = f'Set WshShell = CreateObject("WScript.Shell")\nWshShell.Run """{app_path}""", 0, False\n'
            else:
                # Running as .py script — use pythonw to hide console
                app_path = os.path.abspath(__file__)
                python_dir = os.path.dirname(sys.executable)
                pythonw = os.path.join(python_dir, 'pythonw.exe')
                if not os.path.exists(pythonw):
                    pythonw = sys.executable
                script_content = f'Set WshShell = CreateObject("WScript.Shell")\nWshShell.CurrentDirectory = "{os.path.dirname(app_path)}"\nWshShell.Run """{pythonw}"" ""{app_path}""", 0, False\n'
            
            with open(shortcut_path, 'w') as f:
                f.write(script_content)
            logger.info(f"Startup shortcut created: {shortcut_path}")
        else:
            # Remove the shortcut
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
                logger.info("Startup shortcut removed")
    except Exception as e:
        logger.error(f"Startup shortcut error: {e}")

# ============================================================
# SYSTEM TRAY
# ============================================================

def create_tray_icon():
    """Create the system tray icon — orange package box with $ and green arrow."""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = 1.0  # scale factor (64px base)
    
    # Box body
    draw.rounded_rectangle([6, 18, 58, 58], radius=3, fill=(255, 153, 0))
    draw.rounded_rectangle([6, 18, 58, 58], radius=3, outline=(200, 110, 0), width=2)
    # Flap
    draw.rounded_rectangle([4, 10, 60, 22], radius=2, fill=(255, 170, 40))
    draw.rounded_rectangle([4, 10, 60, 22], radius=2, outline=(200, 110, 0), width=2)
    # Center tape
    draw.rectangle([28, 10, 36, 58], fill=(230, 130, 0))
    # Dollar sign
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        except:
            font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "$", font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((64 - tw) // 2 + 1, 26), "$", fill=(180, 90, 0), font=font)
    draw.text(((64 - tw) // 2, 25), "$", fill=(255, 255, 255), font=font)
    # Green down arrow
    draw.polygon([(44, 46), (56, 46), (50, 52)], fill=(0, 180, 0))
    
    return img.convert('RGB')

def open_browser():
    """Open the tracker in the default browser with friendly URL.
    *.localhost resolves to 127.0.0.1 in all modern browsers (RFC 6761)."""
    import socket
    # Wait for Flask to be ready (up to 5 seconds)
    for _ in range(10):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(('127.0.0.1', DEFAULT_PORT))
            s.close()
            break
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(0.5)
    
    url = get_friendly_url()
    webbrowser.open(url)
    logger.info(f"Opened browser: {url}")

def quit_app(icon):
    shutdown_requested.set()
    icon.stop()

def run_with_tray():
    menu = Menu(
        MenuItem('Open Dashboard', lambda: open_browser()),
        MenuItem('Quit', quit_app)
    )
    icon = Icon("Price Tracker", create_tray_icon(), "Amazon Price Tracker", menu)
    flask_thread = threading.Thread(target=app.run, kwargs={'host': '127.0.0.1', 'port': DEFAULT_PORT, 'use_reloader': False, 'threaded': True}, daemon=True)
    flask_thread.start()
    manager_thread = threading.Thread(target=manager_loop, daemon=True)
    manager_thread.start()
    threading.Timer(1.0, open_browser).start()
    logger.info("Running in system tray mode")
    icon.run()

def run_console():
    threading.Thread(target=app.run, kwargs={'host': '127.0.0.1', 'port': DEFAULT_PORT, 'use_reloader': False, 'threaded': True}, daemon=True).start()
    threading.Timer(1.0, open_browser).start()
    try: manager_loop()
    except KeyboardInterrupt: pass

if __name__ == "__main__":
    # Ensure working directory is the EXE/script location (not system32 or wherever Windows launches from)
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)) or os.getcwd())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    ensure_single_instance()
    os.makedirs('static/screenshots', exist_ok=True)
    init_db()
    from jinja2 import DictLoader
    app.jinja_env.loader = DictLoader({'layout': LAYOUT_TPL})
    app.jinja_env.globals['app_version'] = APP_VERSION
    
    logger.info("="*50)
    logger.info(f"AMAZON PRICE TRACKER v{APP_VERSION}")
    logger.info(f"  {get_friendly_url()}")
    logger.info(f"  {get_fallback_url()}  (fallback)")
    logger.info("="*50)
    
    if TRAY_AVAILABLE:
        run_with_tray()
    else:
        logger.info("Install pystray+pillow for system tray mode")
        run_console()
