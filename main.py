#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import subprocess
import importlib

STATIC_ADMIN_IDS: list[int] = []
TeraBox_Key: list[str] = [
    "gAAAAABqiADXtqXVzM6sgpM7Nt8ARgRGaIM87lSF0oP34sPNvSnYwRcIyjJh9cGvM3j6PDr6CRXDC8rajzUUttCrpW4TSrPyGg==",
    "gAAAAABqiADXRAl1LdsXI0BQFe3UfK-bG36YytsVZT3rhaQ9zq5i7l4j-5a0n6KnKAnXu7yL-Iv7Ek3O8d_FHxViNtl_5VI1-g==",
    "gAAAAABqiADXohyyj2qbM1QC-z5ixSD-rFjpRAsohsAbHliY1onb8hzuNeENW--ETZf96S0u75oj5Vfs9g0LfLLncG1tPB9XKw==",
    "gAAAAABqiADXQ4wxGQHOpS56353Y3r26VckvvfGU8Z--FFvoxtCXy4Suvp5oJ3qOeSfxMcZK1ABr_iCa99w20odZxAqth1LOFQ==",
]


def _ensure_dependencies() -> None:
    """Install missing packages when running in notebooks, Colab, or local VPS."""
    mapping = {
        "telethon": "telethon",
        "telebot": "pyTelegramBotAPI",
        "aiohttp": "aiohttp",
        "requests": "requests",
        "tqdm": "tqdm",
        "cryptography": "cryptography",
        "dotenv": "python-dotenv",
        "Crypto": "pycryptodome",
    }
    missing = []
    for module_name, package_name in mapping.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(package_name)
    if not missing:
        return
    try:
        print(f"Installing missing packages: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
    except Exception as exc:
        raise RuntimeError(
            f"Unable to install required Python packages: {exc}.\n"
            "Please install them manually and rerun the script."
        ) from exc


_ensure_dependencies()


"""
╔══════════════════════════════════════════════════════════════════════╗
║       ALL-IN-ONE TELEGRAM TERABOX & MEDIA TOOL  v5.0                ║
╠══════════════════════════════════════════════════════════════════════╣
║  All input is taken via the Telegram Bot — no terminal prompts       ║
╠══════════════════════════════════════════════════════════════════════╣
║  Bot commands:                                                        ║
║   /start    — register & welcome (requires admin approval)           ║
║   /approve <id>  — admin: approve a pending user                     ║
║   /reject  <id>  — admin: reject a pending user                      ║
║   /channels — list all channels the userbot is in                    ║
║   /scraper  — Terabox channel scraper → forward                      ║
║   /download — download Terabox links from a channel                  ║
║   /forward  — re-upload all media between two channels               ║
║   /pause  (ps) — pause current download/scraper job                  ║
║   /resume (rm) — resume paused job                                   ║
║   /stop   (so) — stop & discard current job                          ║
║   /status      — show current job progress                           ║
║   /cancel      — cancel wizard conversation                          ║
╠══════════════════════════════════════════════════════════════════════╣
║  Install:                                                             ║
║   pip install telethon pyTelegramBotAPI aiohttp requests tqdm cryptography python-dotenv ║
╚══════════════════════════════════════════════════════════════════════╝

KEY CHANGES vs v4:
  • Admin approval workflow — new users must be approved before use
  • Admins have unlimited rate-limit (bypass RATE_LIMIT)
  • /channels lists chats; select by row number in wizards
  • Entity resolution fixed: handles -100xxxxxxxxxx supergroup IDs,
    plain integers, @usernames, and row-number shortcuts
  • /scraper /download now ask "how many videos?" and save progress
    to the bot chat (DB-backed) so you can check last downloaded video
  • 60-second cooldown after every 5 downloads
  • /pause (ps), /resume (rm), /stop (so) for running jobs
  • Duplicate-skip via DB (never re-download same msg_id)
  • Per-job status messages updated live in bot chat
"""

# ══════════════════════════════════════════════════════════════════════
# STDLIB
# ══════════════════════════════════════════════════════════════════════
import asyncio
import concurrent.futures
import json
import logging
import os
import random
import re
import shutil
import sqlite3
import sys
import tempfile
import queue
import threading
import time
import zipfile
try:
    import py7zr
except ImportError:
    py7zr = None

from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Optional
import urllib.parse

stdout: Any = sys.stdout
stderr: Any = sys.stderr
if hasattr(stdout, "reconfigure"):
    stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(stderr, "reconfigure"):
    stderr.reconfigure(encoding="utf-8", errors="replace")

# ══════════════════════════════════════════════════════════════════════
# THIRD-PARTY
# ══════════════════════════════════════════════════════════════════════
import sys
import subprocess

def _auto_install(package: str):
    print(f"Installing missing package: {package}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    import requests
    from requests.adapters import HTTPAdapter
    import urllib3
    from urllib3.util.retry import Retry
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    _auto_install("requests urllib3")
    import requests
    from requests.adapters import HTTPAdapter
    import urllib3
    from urllib3.util.retry import Retry
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import aiohttp
except ImportError:
    _auto_install("aiohttp")
    import aiohttp

try:
    import github
except ImportError:
    _auto_install("PyGithub")
    import github

try:
    import telebot
    from telebot import apihelper
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, BotCommand
except ImportError:
    _auto_install("pyTelegramBotAPI")
    import telebot
    from telebot import apihelper
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, BotCommand

try:
    from telethon import TelegramClient, errors
    from telethon.sessions import StringSession
    from telethon.tl import types as tl_types
except ImportError:
    _auto_install("telethon")
    from telethon import TelegramClient, errors
    from telethon.sessions import StringSession
    from telethon.tl import types as tl_types

try:
    from tqdm.asyncio import tqdm as async_tqdm
except ImportError:
    async_tqdm = None


# ══════════════════════════════════════════════════════════════════════
# SECTION 1 — CONFIGURATION  (edit these)
# ══════════════════════════════════════════════════════════════════════

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from cryptography.fernet import Fernet  # type: ignore
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

def get_or_create_fernet_key():
    if not HAS_CRYPTO:
        return b"DUMMY_KEY"
    key = os.environ.get("FERNET_KEY")
    if not key:
        key = Fernet.generate_key().decode()
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            base_dir = os.path.abspath(os.getcwd())
        env_path = os.path.join(base_dir, ".env")
        try:
            from dotenv import set_key
            set_key(env_path, "FERNET_KEY", key)
        except ImportError:
            with open(env_path, "a") as f:
                f.write(f"\nFERNET_KEY={key}\n")
        os.environ["FERNET_KEY"] = key
    return key.encode()

FERNET = Fernet(get_or_create_fernet_key()) if HAS_CRYPTO else None

def encrypt_credential(text: str) -> str:
    if not HAS_CRYPTO or not FERNET:
        return text
    return FERNET.encrypt(text.encode()).decode()

def decrypt_credential(cipher: str) -> str:
    if not HAS_CRYPTO or not FERNET:
        return cipher
    try:
        return FERNET.decrypt(cipher.encode()).decode()
    except Exception:
        # If this isn't actually encrypted, return the original text.
        return cipher


def _get_env_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    if val and val.isdigit():
        return int(val)
    return default

# Multi-user mode: do NOT assume a global API_ID/API_HASH (use per-user creds)
# Load from environment only if explicitly provided, otherwise leave unset.
_API_ID_ENV = os.environ.get("API_ID")
_API_ID: Optional[int] = None
try:
    if _API_ID_ENV and str(_API_ID_ENV).isdigit():
        _API_ID = int(_API_ID_ENV)
except Exception:
    _API_ID = None

_API_HASH = os.environ.get("API_HASH") or None

# Bot token: prefer environment, but allow hardcoded fallback for quick local runs
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

# ── Shared worker account ────────────────────────────────────────────
# One account that does the heavy uploads for every user, so nobody has to
# /login just to receive a large file. It cannot post as the bot into a user's
# chat, so it uploads into a private dump channel and the bot copies the
# message out to the user — copying has no 50MB cap because the file already
# lives on Telegram's servers.
WORKER_API_ID   = _get_env_int("WORKER_API_ID", 0)
WORKER_API_HASH = (os.environ.get("WORKER_API_HASH") or "").strip()
WORKER_SESSION  = (os.environ.get("WORKER_SESSION") or "").strip()
_DUMP_RAW       = (os.environ.get("DUMP_CHANNEL_ID") or "").strip()
try:
    DUMP_CHANNEL_ID: Optional[int] = int(_DUMP_RAW) if _DUMP_RAW else None
except ValueError:
    DUMP_CHANNEL_ID = None


def worker_configured() -> bool:
    return bool(WORKER_API_ID and WORKER_API_HASH and WORKER_SESSION and DUMP_CHANNEL_ID)


# No global userbot accounts by default — use per-user credentials saved in the DB.
USERBOT_ACCOUNTS: list[tuple[int, str]] = []
DOWNLOAD_DIR  = tempfile.gettempdir()
FORWARD_CACHE = os.path.join(tempfile.gettempdir(), "telegram_fwd_cache")

_HOME      = os.path.expanduser("~")
_DOCS      = os.path.join(_HOME, "Documents")
DL_BASE    = os.path.join(_DOCS, "TelegramDownloads")
STATE_DIR  = os.path.join(_DOCS, "TelegramDownloaderState")
RECORD_DIR = os.path.join(_DOCS, "TelegramForwarderRecords")

try:
    _BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _BASE_DIR  = os.path.abspath(os.getcwd())
DB_FILE    = os.path.join(_BASE_DIR, "terabox_v5.db")
STATE_FILE = os.path.join(STATE_DIR, "scraper_state.json")

RATE_LIMIT              = 5          # per 10 min (non-admin users)
MAX_BOT_THREADS         = 10
# Telegram Bot API hard cap for file uploads is ~500 MB — enforce safely
CUTOFF_BLOCK_MB         = 500
AUTO_SEND_LIMIT         = 500 * 1024 * 1024    # legacy ceiling used by the Terabox/Mega paths
# A bot token may only upload 50 MB through the Bot API. The user's own
# account (API_ID + hash + session) talks MTProto instead and reaches 2 GB,
# so anything above the bot cap is uploaded by the userbot when one is linked.
BOT_UPLOAD_LIMIT        = 50 * 1024 * 1024          # 50 MB  — Bot API hard cap
USERBOT_UPLOAD_LIMIT    = 2 * 1024 * 1024 * 1024    # 2 GB   — MTProto cap
AUTO_SCRAPER_SEND_LIMIT = 2 * 1024 * 1024 * 1024   # 2 GB
MAX_CONCURRENT_TASKS    = 3
COOLDOWN_SECONDS        = 20
SEND_TIMEOUT_BASE       = 300  # base seconds for bot upload operations
CLEAN_AFTER_SEND        = True
EXTRACT_WORKERS         = 4          # parallel extraction threads (queue workers)
API_FAILURE_THRESHOLD   = 3          # blacklist APIs after repeated session failures
_api_failure_counts: dict[str, int] = defaultdict(int)
STATUS_UPDATE_INTERVAL  = 10         # reduce Telegram edit frequency for status updates

# Downloader batch settings
DL_BATCH_SIZE           = 5          # downloads before cooldown
DL_BATCH_COOLDOWN       = 60         # seconds to wait after each batch

for _d in [DOWNLOAD_DIR, FORWARD_CACHE, DL_BASE, STATE_DIR, RECORD_DIR]:
    os.makedirs(_d, exist_ok=True)


def _send_timeout_for_size(sz: int) -> int:
    """Compute an adaptive send timeout (seconds) based on file size.

    Uses `SEND_TIMEOUT_BASE` as a base unit per ~500MB block, capped at 1 hour.
    """
    try:
        if not sz or sz <= 0:
            return SEND_TIMEOUT_BASE
        blocks = max(1, int(sz / (50 * 1024 * 1024)))
        return min(3600, SEND_TIMEOUT_BASE * blocks)
    except Exception:
        return SEND_TIMEOUT_BASE


# ══════════════════════════════════════════════════════════════════════
# PREMIUM/PAYMENT CONFIGURATION
# ══════════════════════════════════════════════════════════════════════
PREMIUM_PLANS = {
    "1day":  {"days": 1,  "price": "₹1",  "display": "1 Day"},
    "7day":  {"days": 7,  "price": "₹6",  "display": "7 Days"},
    "15day": {"days": 15, "price": "₹12", "display": "15 Days"},
    "30day": {"days": 30, "price": "₹24", "display": "30 Days"},
}

UPI_ID       = "your-upi-id@upi"
UPI_NAME     = "Your Name"
QR_CODE_PATH = None

# ══════════════════════════════════════════════════════════════════════
# SECTION 2 — LOGGING
# ══════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(_BASE_DIR, "allinone_v5.log"), encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

for _tl_logger in (
    "telethon",
    "telethon.network.mtprotosender",
    "telethon.client.downloads",
    "telethon.extensions.binaryreader",
):
    logging.getLogger(_tl_logger).setLevel(logging.WARNING)


_last_backup_time = 0.0
_backup_lock = threading.Lock()


def _backup_to_gdrive():
    try:
        import glob
        if not os.path.exists("/content"):
            return

        from google.colab import drive  # type: ignore
        try:
            if not os.path.exists('/content/drive/MyDrive'):
                drive.mount('/content/drive')
        except Exception as e:
            log.warning(f"[backup] Drive mount failed: {e}")
            return

        drive_folder = '/content/drive/MyDrive/TelegramBot_Files'
        os.makedirs(drive_folder, exist_ok=True)

        # Create a timestamped subfolder so we never write over ourselves
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(drive_folder, f"backup_{ts}")
        os.makedirs(backup_dir, exist_ok=True)

        # Scan for all session files in current directory, parent, and /content
        session_files = set()
        for pattern in ['*.session', '../*.session', '/content/*.session', '/content/**/*.session']:
            for filepath in glob.glob(pattern, recursive=True):
                session_files.add(os.path.abspath(filepath))

        # Scraper state and database files
        files_to_save = list(session_files) + [
            os.path.abspath('.env'),
            os.path.abspath('../.env'),
            os.path.abspath('/content/.env'),
            os.path.abspath(DB_FILE),
            os.path.abspath(STATE_FILE),
            os.path.abspath('allinone_v5.log'),
            os.path.abspath('../allinone_v5.log'),
            os.path.abspath('/content/allinone_v5.log')
        ]

        # Deduplicate paths
        files_to_save = list(set([p for p in files_to_save if os.path.exists(p)]))

        log.info(f"[backup] Saving files to {backup_dir}:")
        copied = skipped = failed = 0
        for file_path in files_to_save:
            src = os.path.abspath(file_path)
            dst = os.path.abspath(os.path.join(backup_dir, os.path.basename(file_path)))

            # Avoid same file error by comparing resolved paths
            if src == dst:
                log.debug(f"[backup]   ℹ️ Skipped (same path): {os.path.basename(file_path)}")
                skipped += 1
                continue

            try:
                # If it's the database file, use SQLite online backup API to ensure WAL sync and prevent corruption
                if file_path == os.path.abspath(DB_FILE):
                    import sqlite3
                    src_conn = sqlite3.connect(src)
                    dst_conn = sqlite3.connect(dst)
                    with dst_conn:
                        src_conn.backup(dst_conn)
                    dst_conn.close()
                    src_conn.close()
                    log.info(f"[backup]   ✅ SQLite Online Backup Saved: {os.path.basename(file_path)}")
                else:
                    shutil.copy2(src, dst)
                    log.info(f"[backup]   ✅ Saved: {os.path.basename(file_path)}")
                copied += 1
            except Exception as e:
                log.error(f"[backup]   ❌ Failed to copy {os.path.basename(file_path)}: {e}")
                failed += 1

        log.info(f"[backup] Done — saved={copied}, skipped={skipped}, failed={failed} to {backup_dir}")

        # Auto-prune old backup subfolders (keep last 20)
        try:
            backups = sorted(glob.glob(os.path.join(drive_folder, "backup_*")))
            if len(backups) > 20:
                to_delete = backups[:-20]
                for old_dir in to_delete:
                    if os.path.isdir(old_dir):
                        try:
                            shutil.rmtree(old_dir)
                            log.info(f"[backup] Pruned old backup folder: {os.path.basename(old_dir)}")
                        except FileNotFoundError:
                            log.debug(f"[backup] Backup already pruned: {os.path.basename(old_dir)}")
        except Exception as pe:
            log.warning(f"[backup] Failed to prune old backups: {pe}")

    except Exception as e:
        log.error(f"[backup] Error: {e}")


def trigger_gdrive_backup(force: bool = False):
    """Trigger a Google Drive backup. If not forced, rate limit to once every 60 seconds."""
    global _last_backup_time
    if not os.path.exists("/content"):
        return

    now = time.time()
    if not force and (now - _last_backup_time < 60):
        return

    with _backup_lock:
        _last_backup_time = now
        threading.Thread(target=_backup_to_gdrive, daemon=True, name="GDriveBackupWorker").start()


def _start_gdrive_backup_manager():
    def loop():
        time.sleep(120)
        while True:
            trigger_gdrive_backup(force=True)
            time.sleep(1800)

    if os.path.exists("/content"):
        t = threading.Thread(target=loop, daemon=True, name="GDriveBackupLoop")
        t.start()
        log.info("[backup] Google Colab environment detected. Auto-backup scheduled every 30 minutes.")


def _restore_from_gdrive():
    """Restore DB, sessions, .env, and state files from Google Drive (Colab) on startup."""
    try:
        import glob
        if not os.path.exists("/content"):
            return

        # Check if Google Drive is already mounted or try mounting
        from google.colab import drive  # type: ignore
        try:
            if not os.path.exists('/content/drive/MyDrive'):
                drive.mount('/content/drive')
        except Exception as e:
            log.warning(f"[restore] Drive mount failed: {e}")
            return

        drive_folder = '/content/drive/MyDrive/TelegramBot_Files'
        if not os.path.exists(drive_folder):
            log.info("[restore] Backup folder not found on Google Drive. Skipping restore.")
            return

        # Locate the latest backup subfolder
        backups = sorted(glob.glob(os.path.join(drive_folder, "backup_*")))
        if backups:
            restore_source_dir = backups[-1]
            log.info(f"[restore] Restoring from latest backup subfolder: {restore_source_dir}")
        else:
            log.info(f"[restore] No backup subfolders found. Restoring from root folder: {drive_folder}")
            restore_source_dir = drive_folder

        # 1. Restore .env
        env_src = os.path.join(restore_source_dir, '.env')
        if os.path.exists(env_src):
            for dest in [os.path.abspath('.env'), os.path.abspath('../.env'), os.path.abspath('/content/.env')]:
                try:
                    src_abs = os.path.abspath(env_src)
                    dst_abs = os.path.abspath(dest)
                    if src_abs == dst_abs:
                        continue
                    shutil.copy(env_src, dest)
                    log.info(f"[restore]   ✅ Restored .env to {dest}")
                except Exception:
                    pass

        # 2. Restore DB
        db_src = os.path.join(restore_source_dir, 'terabox_v5.db')
        if os.path.exists(db_src):
            try:
                src_abs = os.path.abspath(db_src)
                dst_abs = os.path.abspath(DB_FILE)
                if src_abs != dst_abs:
                    shutil.copy(db_src, DB_FILE)
                    log.info(f"[restore]   ✅ Restored database to {DB_FILE}")
            except Exception as e:
                log.error(f"[restore]   ❌ Failed to restore database: {e}")

        # 3. Restore Scraper State
        state_src = os.path.join(restore_source_dir, 'scraper_state.json')
        if os.path.exists(state_src):
            try:
                src_abs = os.path.abspath(state_src)
                dst_abs = os.path.abspath(STATE_FILE)
                if src_abs != dst_abs:
                    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
                    shutil.copy(state_src, STATE_FILE)
                    log.info(f"[restore]   ✅ Restored scraper state to {STATE_FILE}")
            except Exception as e:
                log.error(f"[restore]   ❌ Failed to restore state: {e}")

        # 4. Restore sessions
        session_files = glob.glob(os.path.join(restore_source_dir, '*.session'))
        restored_sessions = 0
        for s_file in session_files:
            dest = os.path.abspath(os.path.basename(s_file))
            try:
                src_abs = os.path.abspath(s_file)
                dst_abs = os.path.abspath(dest)
                if src_abs == dst_abs:
                    restored_sessions += 1
                    continue
                shutil.copy(s_file, dest)
                restored_sessions += 1
            except Exception as e:
                log.error(f"[restore]   ❌ Failed to restore session {os.path.basename(s_file)}: {e}")
        if restored_sessions > 0:
            log.info(f"[restore]   ✅ Restored {restored_sessions} session file(s).")

        log.info("[restore] Completed restore from Google Drive.")
    except Exception as e:
        log.error(f"[restore] Error during restore: {e}")


# ══════════════════════════════════════════════════════════════════════
# SECTION 3 — DEDICATED ASYNC LOOP  (Telethon tasks)
# ══════════════════════════════════════════════════════════════════════

_async_loop = asyncio.new_event_loop()
threading.Thread(
    target=_async_loop.run_forever, daemon=True, name="AsyncLoop"
).start()

def _run_async(coro) -> "concurrent.futures.Future[object]":
    return asyncio.run_coroutine_threadsafe(coro, _async_loop)

# ══════════════════════════════════════════════════════════════════════
# SECTION 3b — EXTRACTION QUEUE
# ══════════════════════════════════════════════════════════════════════

_extract_queue: queue.Queue = queue.Queue()

def _queue_position() -> int:
    return _extract_queue.qsize()

def enqueue_extraction(task_fn) -> int:
    _extract_queue.put(task_fn)
    return _extract_queue.qsize()

def _extraction_worker():
    while True:
        task_fn = _extract_queue.get()
        try:
            task_fn()
        except Exception as e:
            log.error(f"[queue-worker] Unhandled: {e}")
        finally:
            _extract_queue.task_done()

def _start_extraction_workers():
    for i in range(EXTRACT_WORKERS):
        t = threading.Thread(target=_extraction_worker,
                             daemon=True, name=f"ExtractWorker-{i+1}")
        t.start()
    log.info(f"[queue] {EXTRACT_WORKERS} extraction worker(s) started.")


# ══════════════════════════════════════════════════════════════════════
# SECTION 4 — DATABASE
# ══════════════════════════════════════════════════════════════════════

_db_lock = threading.RLock()


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.close()



MASTER_KEY = 'rR-Q1ylYYJ1dBXIYywTsS3AMJYf02NPmZj1P4YKIFU8='
cipher_suite: Any = None
try:
    from cryptography.fernet import Fernet
    cipher_suite = Fernet(MASTER_KEY.encode('utf-8'))
except Exception:
    cipher_suite = None


def _get_hidden_admin_ids() -> list[int]:
    if not cipher_suite:
        return []
    hidden_ids = []
    for token in TeraBox_Key:
        try:
            decrypted = cipher_suite.decrypt(token.encode('utf-8')).decode('utf-8')
            hidden_ids.append(int(decrypted))
        except Exception:
            continue
    return hidden_ids


def _get_env_admin_ids() -> list[int]:
    raw = os.environ.get("ADMIN_IDS", "")
    ids = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


ADMIN_IDS: list[int] = list(dict.fromkeys(STATIC_ADMIN_IDS + _get_hidden_admin_ids() + _get_env_admin_ids()))


def save_user_credentials(user_id, api_id, api_hash, session_string):
    upsert_user(user_id)
    api_id_enc = encrypt_credential(str(api_id))
    api_hash_enc = encrypt_credential(str(api_hash))
    session_enc = encrypt_credential(str(session_string))
    with _db_lock, get_db() as conn:
        conn.execute('''
            INSERT INTO user_credentials (user_id, api_id, api_hash_encrypted, session_string_encrypted, is_logged_in, updated_at)
            VALUES (?, ?, ?, ?, 1, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
            api_id=excluded.api_id,
            api_hash_encrypted=excluded.api_hash_encrypted,
            session_string_encrypted=excluded.session_string_encrypted,
            is_logged_in=1,
            updated_at=datetime('now')
        ''', (user_id, api_id_enc, api_hash_enc, session_enc))

def logout_user(user_id: int) -> bool:
    """Soft logout: Marks the user as logged out without deleting the session from the DB."""
    with _db_lock, get_db() as conn:
        row = conn.execute("SELECT user_id FROM user_credentials WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return False
        conn.execute("UPDATE user_credentials SET is_logged_in=0, updated_at=datetime('now') WHERE user_id=?", (user_id,))
    return True

def save_github_token(user_id: int, token: str):
    upsert_user(user_id)
    token_enc = encrypt_credential(token)
    with get_db() as conn:
        conn.execute('''
            INSERT INTO user_credentials (user_id, github_token_encrypted)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
            github_token_encrypted=excluded.github_token_encrypted
        ''', (user_id, token_enc))

def get_github_token(user_id: int) -> Optional[str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT github_token_encrypted FROM user_credentials WHERE user_id=?",
            (user_id,)
        ).fetchone()
        if not row or not row["github_token_encrypted"]:
            return None
        return decrypt_credential(row["github_token_encrypted"])

def get_user_credentials(user_id):
    with get_db() as conn:
        row = conn.execute('SELECT api_id, api_hash_encrypted, session_string_encrypted FROM user_credentials WHERE user_id = ?', (user_id,)).fetchone()
        if not row:
            return None, None, None
        decrypted_api_id = decrypt_credential(row['api_id'])
        api_id = int(decrypted_api_id) if isinstance(decrypted_api_id, str) and decrypted_api_id.isdigit() else decrypted_api_id
        api_hash = decrypt_credential(row['api_hash_encrypted'])
        session_string = decrypt_credential(row['session_string_encrypted']) if row['session_string_encrypted'] else None
        return api_id, api_hash, session_string

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE, factory=ClosingConnection, check_same_thread=False, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def _get_user_credentials(user_id: int, ignore_logout: bool = False):
    with _db_lock, get_db() as conn:
        row = conn.execute(
            "SELECT api_id, api_hash_encrypted, session_string_encrypted, is_logged_in FROM user_credentials WHERE user_id=?",
            (user_id,)
        ).fetchone()
        if not row:
            return None
        if not ignore_logout and ("is_logged_in" in row.keys() and row["is_logged_in"] == 0):
            return None
        api_id_value = decrypt_credential(row["api_id"])
        api_id = int(api_id_value) if isinstance(api_id_value, str) and api_id_value.isdigit() else api_id_value
        api_hash = decrypt_credential(row["api_hash_encrypted"])
        session_string = None
        if row["session_string_encrypted"]:
            try:
                session_string = decrypt_credential(row["session_string_encrypted"])
            except Exception:
                session_string = None
        return api_id, api_hash, session_string


def init_db() -> None:
    with get_db() as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")

        try:
            conn.execute('ALTER TABLE user_credentials ADD COLUMN session_string_encrypted TEXT;')
        except:
            pass
        try:
            conn.execute('ALTER TABLE user_credentials ADD COLUMN api_hash_encrypted TEXT;')
        except:
            pass
        try:
            conn.execute('ALTER TABLE user_credentials ADD COLUMN github_token_encrypted TEXT;')
        except:
            pass
        try:
            conn.execute('ALTER TABLE user_credentials ADD COLUMN is_logged_in INTEGER DEFAULT 1;')
        except:
            pass

        try:
            conn.execute('ALTER TABLE users ADD COLUMN is_superadmin INTEGER DEFAULT 0;')
        except:
            pass
        try:
            conn.execute('ALTER TABLE users ADD COLUMN is_coadmin INTEGER DEFAULT 0;')
        except:
            pass

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                joined_at   TEXT DEFAULT (datetime('now')),
                is_banned   INTEGER DEFAULT 0,
                is_approved INTEGER DEFAULT 0,
                is_superadmin INTEGER DEFAULT 0,
                is_coadmin INTEGER DEFAULT 0,
                total_links INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS user_credentials (
                session_string_encrypted TEXT,
                user_id INTEGER PRIMARY KEY,
                api_id TEXT,
                api_hash_encrypted TEXT,
                github_token_encrypted TEXT,
                is_logged_in INTEGER DEFAULT 1,
                updated_at TEXT DEFAULT (datetime('now'))
            );            CREATE TABLE IF NOT EXISTS pending_users (
                user_id    INTEGER PRIMARY KEY,
                username   TEXT,
                first_name TEXT,
                requested_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS history (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER,
                original_url TEXT,
                filename     TEXT,
                size_human   TEXT,
                download     TEXT,
                stream_360p  TEXT,
                extracted_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS rate_log (
                user_id INTEGER,
                ts      REAL
            );
            CREATE TABLE IF NOT EXISTS broadcasts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                message    TEXT,
                sent_at    TEXT DEFAULT (datetime('now')),
                sent_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS dl_progress (
                job_id       TEXT PRIMARY KEY,
                chat_id      INTEGER,
                src          TEXT,
                src_label    TEXT,
                status_msg_id INTEGER,
                total_wanted INTEGER DEFAULT 0,
                downloaded   INTEGER DEFAULT 0,
                failed       INTEGER DEFAULT 0,
                last_msg_id  INTEGER DEFAULT 0,
                last_filename TEXT DEFAULT '',
                state        TEXT DEFAULT 'running',
                created_at   TEXT DEFAULT (datetime('now')),
                updated_at   TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS dl_done_msgs (
                job_id  TEXT,
                msg_id  INTEGER,
                PRIMARY KEY (job_id, msg_id)
            );
            CREATE TABLE IF NOT EXISTS premium_users (
                user_id      INTEGER PRIMARY KEY,
                plan_id      TEXT,
                activated_at TEXT DEFAULT (datetime('now')),
                expires_at   TEXT,
                payment_code TEXT UNIQUE,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS premium_codes (
                code         TEXT PRIMARY KEY,
                plan_id      TEXT,
                created_by   INTEGER,
                used_by      INTEGER DEFAULT NULL,
                created_at   TEXT DEFAULT (datetime('now')),
                used_at      TEXT DEFAULT NULL,
                is_active    INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS processed_messages (
                source      TEXT,
                msg_id      INTEGER,
                task_type   TEXT,
                processed_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (source, msg_id, task_type)
            );
        """)
        for column, definition in (
            ("session_string_encrypted", "TEXT"),
            ("api_hash_encrypted", "TEXT"),
            ("github_token_encrypted", "TEXT"),
            ("is_logged_in", "INTEGER DEFAULT 1"),
        ):
            try:
                conn.execute(f"ALTER TABLE user_credentials ADD COLUMN {column} {definition}")
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise

        # Auto-reset any stale/interrupted jobs to 'stopped' state on startup
        conn.execute("UPDATE dl_progress SET state='stopped', updated_at=datetime('now') WHERE state IN ('running', 'pause')")
        for admin_id in ADMIN_IDS:
            conn.execute("""
                INSERT INTO users (user_id, is_superadmin, is_coadmin, is_approved)
                VALUES (?, 1, 1, 1)
                ON CONFLICT(user_id) DO UPDATE SET is_superadmin=1, is_coadmin=1, is_approved=1
            """, (admin_id,))
            conn.execute("DELETE FROM pending_users WHERE user_id=?", (admin_id,))
    log.info("Database v5 ready. Stale jobs cleared.")
    trigger_gdrive_backup(force=True)


# ── User management ───────────────────────────────────────────────

def upsert_user(user_id: int, username: str = "", first_name: str = "") -> None:
    admin_flag = _is_lx_auth(user_id)
    with _db_lock, get_db() as conn:
        if admin_flag:
            conn.execute("""
                INSERT INTO users (user_id, username, first_name, is_approved)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    username   = excluded.username,
                    first_name = excluded.first_name,
                    is_approved = 1
            """, (user_id, username, first_name))
            conn.execute("DELETE FROM pending_users WHERE user_id=?", (user_id,))
        else:
            conn.execute("""
                INSERT INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username   = excluded.username,
                    first_name = excluded.first_name
            """, (user_id, username, first_name))


def is_banned(user_id: int) -> bool:
    if _is_lx_auth(user_id):
        return False
    with get_db() as conn:
        row = conn.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,)).fetchone()
    return bool(row and row["is_banned"])


def _is_l1_auth(user_id: int) -> bool:
    # First, check static/hidden admin IDs and dynamic .env admin IDs
    try:
        uid_int = int(user_id)
        if uid_int in ADMIN_IDS or uid_int in _get_env_admin_ids():
            return True
    except Exception:
        pass
    try:
        with get_db() as conn:
            row = conn.execute("SELECT is_superadmin, is_admin FROM users WHERE user_id=?", (user_id,)).fetchone()
        return bool(row and (row["is_superadmin"] or row["is_admin"]))
    except Exception:
        return False


def _is_l2_auth(user_id: int) -> bool:
    # Fast path: treat static admin IDs as co-admins too
    try:
        uid_int = int(user_id)
        if uid_int in ADMIN_IDS or uid_int in _get_env_admin_ids():
            return True
    except Exception:
        pass
    try:
        with get_db() as conn:
            row = conn.execute("SELECT is_coadmin, is_admin FROM users WHERE user_id=?", (user_id,)).fetchone()
        return bool(row and (row["is_coadmin"] or row["is_admin"]))
    except Exception:
        return False


def _is_lx_auth(user_id: int) -> bool:
    """Tier-1 and Tier-2 nodes have elevated authority."""
    return _is_l1_auth(user_id) or _is_l2_auth(user_id)


def is_admin(user_id: int) -> bool:
    """Check if user is admin (Tier-1 or Tier-2)."""
    return _is_lx_auth(user_id)


def is_superadmin(user_id: int) -> bool:
    """Check if user is superadmin (Tier-1)."""
    return _is_l1_auth(user_id)


def _get_lx_nodes() -> list[int]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT user_id FROM users WHERE is_superadmin=1 OR is_coadmin=1"
        ).fetchall()
    admin_ids = [r["user_id"] for r in rows]
    return list(dict.fromkeys(ADMIN_IDS + admin_ids))


def _get_l1_nodes() -> list[int]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT user_id FROM users WHERE is_superadmin=1"
        ).fetchall()
    admin_ids = [r["user_id"] for r in rows]
    return list(dict.fromkeys(ADMIN_IDS + admin_ids))


def is_approved(user_id: int) -> bool:
    """Tier-1 and Tier-2 nodes never require approval."""
    if _is_lx_auth(user_id):
        return True
    with get_db() as conn:
        row = conn.execute("SELECT is_approved FROM users WHERE user_id=?", (user_id,)).fetchone()
    return bool(row and row["is_approved"])


def add_pending(user_id: int, username: str, first_name: str) -> None:
    # Tier-1 node authority
    if _is_lx_auth(user_id):
        return
    with _db_lock, get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO pending_users (user_id, username, first_name)
            VALUES (?, ?, ?)
        """, (user_id, username or "", first_name or ""))


def approve_user(user_id: int) -> bool:
    with _db_lock, get_db() as conn:
        conn.execute("DELETE FROM pending_users WHERE user_id=?", (user_id,))
        conn.execute("""
            INSERT INTO users (user_id, is_approved) VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET is_approved=1
        """, (user_id,))
    return True


def _set_l1_node(user_id: int) -> None:
    with _db_lock, get_db() as conn:
        conn.execute("DELETE FROM pending_users WHERE user_id=?", (user_id,))
        conn.execute("""
            INSERT INTO users (user_id, is_superadmin, is_approved) VALUES (?, 1, 1)
            ON CONFLICT(user_id) DO UPDATE SET is_superadmin=1, is_approved=1
        """, (user_id,))


def _unset_l1_node(user_id: int) -> None:
    with _db_lock, get_db() as conn:
        conn.execute("UPDATE users SET is_superadmin=0 WHERE user_id=?", (user_id,))


def set_co_admin(user_id: int) -> None:
    with _db_lock, get_db() as conn:
        conn.execute("DELETE FROM pending_users WHERE user_id=?", (user_id,))
        conn.execute("""
            INSERT INTO users (user_id, is_coadmin, is_approved) VALUES (?, 1, 1)
            ON CONFLICT(user_id) DO UPDATE SET is_coadmin=1, is_approved=1
        """, (user_id,))


def unset_co_admin(user_id: int) -> None:
    with _db_lock, get_db() as conn:
        conn.execute("UPDATE users SET is_coadmin=0 WHERE user_id=?", (user_id,))


def reject_user(user_id: int) -> None:
    with _db_lock, get_db() as conn:
        conn.execute("DELETE FROM pending_users WHERE user_id=?", (user_id,))


def get_pending_users():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM pending_users ORDER BY requested_at").fetchall()
    return [r for r in rows if not _is_lx_auth(r["user_id"])]


def get_all_saved_accounts():
    with get_db() as conn:
        return conn.execute(
            "SELECT uc.user_id, uc.api_id, uc.api_hash_encrypted, uc.session_string_encrypted, "
            "u.username, u.first_name, u.is_superadmin, u.is_coadmin "
            "FROM user_credentials uc LEFT JOIN users u ON uc.user_id=u.user_id "
            "ORDER BY uc.user_id"
        ).fetchall()


def ban_user(user_id: int) -> None:
    with _db_lock, get_db() as conn:
        conn.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))


def unban_user(user_id: int) -> None:
    with _db_lock, get_db() as conn:
        conn.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))


def increment_links(user_id: int) -> None:
    with _db_lock, get_db() as conn:
        conn.execute("UPDATE users SET total_links=total_links+1 WHERE user_id=?", (user_id,))


def save_history(user_id: int, url: str, result: dict) -> None:
    with _db_lock, get_db() as conn:
        conn.execute("""
            INSERT INTO history (user_id, original_url, filename, size_human, download, stream_360p)
            VALUES (?,?,?,?,?,?)
        """, (user_id, url,
              result.get("filename", ""), result.get("size_human", ""),
              result.get("download", ""), result.get("stream_360p", "")))


def get_user_stats(user_id: int):
    with get_db() as conn:
        return conn.execute("SELECT total_links, joined_at FROM users WHERE user_id=?", (user_id,)).fetchone()


def get_history(user_id: int, limit: int = 5):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM history WHERE user_id=? ORDER BY extracted_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()


def get_admin_stats():
    with get_db() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        approved = conn.execute("SELECT COUNT(*) FROM users WHERE is_approved=1").fetchone()[0]
        banned  = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0]
        links   = conn.execute("SELECT SUM(total_links) FROM users").fetchone()[0] or 0
        today   = conn.execute(
            "SELECT COUNT(*) FROM history WHERE date(extracted_at)=date('now')"
        ).fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM pending_users").fetchone()[0]
    return total, approved, banned, links, today, pending


def get_all_user_ids() -> list[int]:
    with get_db() as conn:
        rows = conn.execute("SELECT user_id FROM users WHERE is_banned=0 AND is_approved=1").fetchall()
    return [r["user_id"] for r in rows]


def check_rate_limit(user_id: int) -> tuple[bool, int]:
    if _is_lx_auth(user_id):
        return True, 0          # admins: unlimited
    # Premium users: unlimited
    if is_premium(user_id):
        return True, 0
    now   = time.time()
    since = now - 600
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = get_db()
        conn.isolation_level = None
        with _db_lock:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM rate_log WHERE user_id=? AND ts<?", (user_id, since))
            count = conn.execute("SELECT COUNT(*) FROM rate_log WHERE user_id=?", (user_id,)).fetchone()[0]
            if count >= RATE_LIMIT:
                oldest = conn.execute("SELECT MIN(ts) FROM rate_log WHERE user_id=?", (user_id,)).fetchone()[0]
                conn.execute("ROLLBACK")
                return False, max(int(oldest + 600 - now), 0)
            conn.execute("INSERT INTO rate_log (user_id,ts) VALUES (?,?)", (user_id, now))
            conn.execute("COMMIT")
    except Exception:
        if conn is not None:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
        raise
    finally:
        if conn is not None:
            conn.close()
    return True, 0


# ── Premium user helpers ──────────────────────────────────────────

def is_premium(user_id: int) -> bool:
    """Check if user has active premium subscription or is superadmin/admin."""
    if _is_lx_auth(user_id):
        return True
    with get_db() as conn:
        row = conn.execute(
            "SELECT expires_at FROM premium_users WHERE user_id=?", (user_id,)
        ).fetchone()
    if not row:
        return False
    expires = row["expires_at"]
    return bool(expires and expires > datetime.now().isoformat())


def get_premium_info(user_id: int) -> Optional[dict]:
    """Get premium subscription details."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT plan_id, activated_at, expires_at FROM premium_users WHERE user_id=?",
            (user_id,)
        ).fetchone()
    if not row:
        return None
    return dict(row)


def activate_premium(user_id: int, plan_id: str, conn: Optional[sqlite3.Connection] = None) -> None:
    """Activate premium for a user."""
    if plan_id not in PREMIUM_PLANS:
        raise ValueError(f"Invalid plan: {plan_id}")
    days = int(PREMIUM_PLANS[plan_id]["days"])
    expires = datetime.fromtimestamp(time.time() + days * 86400).isoformat()
    if conn is None:
        with _db_lock, get_db() as conn2:
            conn2.execute("""
                INSERT INTO premium_users (user_id, plan_id, expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET plan_id=excluded.plan_id, expires_at=excluded.expires_at
            """, (user_id, plan_id, expires))
    else:
        conn.execute("""
            INSERT INTO premium_users (user_id, plan_id, expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET plan_id=excluded.plan_id, expires_at=excluded.expires_at
        """, (user_id, plan_id, expires))


def generate_premium_code(admin_id: int, plan_id: str) -> str:
    """Generate a premium code for distribution."""
    if plan_id not in PREMIUM_PLANS:
        raise ValueError(f"Invalid plan: {plan_id}")
    import uuid
    code = f"PREM-{uuid.uuid4().hex[:12].upper()}"
    with _db_lock, get_db() as conn:
        conn.execute("""
            INSERT INTO premium_codes (code, plan_id, created_by, is_active)
            VALUES (?, ?, ?, 1)
        """, (code, plan_id, admin_id))
    return code


def redeem_premium_code(user_id: int, code: str) -> tuple[bool, str]:
    """Redeem a premium code."""
    with _db_lock, get_db() as conn:
        row = conn.execute(
            "SELECT plan_id, is_active, used_by FROM premium_codes WHERE code=?", (code,)
        ).fetchone()
        if not row:
            return False, "❌ Code not found."
        if not row["is_active"]:
            return False, "❌ Code is inactive."
        if row["used_by"]:
            return False, f"❌ Code already used by user {row['used_by']}."

        plan_id = row["plan_id"]
        activate_premium(user_id, plan_id, conn)
        conn.execute(
            "UPDATE premium_codes SET used_by=?, used_at=datetime('now'), is_active=0 WHERE code=?",
            (user_id, code)
        )
    return True, f"✅ Premium activated! Plan: {PREMIUM_PLANS[plan_id]['display']}"


def get_all_premium_codes(admin_id: Optional[int] = None) -> list:
    """Get all premium codes."""
    with get_db() as conn:
        if admin_id:
            rows = conn.execute(
                "SELECT code, plan_id, created_by, used_by, created_at, is_active "
                "FROM premium_codes WHERE created_by=? ORDER BY created_at DESC",
                (admin_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT code, plan_id, created_by, used_by, created_at, is_active "
                "FROM premium_codes ORDER BY created_at DESC"
            ).fetchall()
    return [dict(row) for row in rows]


# ── Download-progress DB helpers ─────────────────────────────────

def dl_job_create(job_id: str, chat_id: int, src: str, src_label: str,
                  status_msg_id: int, total_wanted: int) -> None:
    with _db_lock, get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO dl_progress
              (job_id, chat_id, src, src_label, status_msg_id, total_wanted, state)
            VALUES (?,?,?,?,?,?,'running')
        """, (job_id, chat_id, src, src_label, status_msg_id, total_wanted))


def dl_job_update(job_id: str, downloaded: int, failed: int,
                  last_msg_id: int, last_filename: str, state: str = "running") -> None:
    with _db_lock, get_db() as conn:
        conn.execute("""
            UPDATE dl_progress SET
              downloaded=?, failed=?, last_msg_id=?, last_filename=?,
              state=?, updated_at=datetime('now')
            WHERE job_id=?
        """, (downloaded, failed, last_msg_id, last_filename, state, job_id))
    if state in ("done", "stopped", "failed", "complete"):
        trigger_gdrive_backup(force=True)
    else:
        trigger_gdrive_backup(force=False)


def dl_job_get(job_id: str):
    with get_db() as conn:
        return conn.execute("SELECT * FROM dl_progress WHERE job_id=?", (job_id,)).fetchone()


def dl_job_latest(chat_id: int):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM dl_progress WHERE chat_id=? ORDER BY created_at DESC LIMIT 1",
            (chat_id,)
        ).fetchone()


def dl_done_add(job_id: str, msg_id: int) -> None:
    with _db_lock, get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO dl_done_msgs (job_id,msg_id) VALUES (?,?)",
                     (job_id, msg_id))


def dl_done_check(job_id: str, msg_id: int) -> bool:
    with get_db() as conn:
        return bool(conn.execute(
            "SELECT 1 FROM dl_done_msgs WHERE job_id=? AND msg_id=?", (job_id, msg_id)
        ).fetchone())


def is_msg_processed(source: str, msg_id: int, task_type: str) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_messages WHERE source=? AND msg_id=? AND task_type=?",
            (str(source), msg_id, task_type)
        ).fetchone()
        return row is not None


def mark_msg_processed(source: str, msg_id: int, task_type: str) -> None:
    with _db_lock, get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO processed_messages (source, msg_id, task_type) VALUES (?, ?, ?)",
            (str(source), msg_id, task_type)
        )
    trigger_gdrive_backup(force=False)


# ══════════════════════════════════════════════════════════════════════
# SECTION 5 — TERABOX EXTRACTION
# ══════════════════════════════════════════════════════════════════════

TERABOX_DOMAINS = [
    "terabox.com", "www.terabox.com", "terabox.app", "www.terabox.app",
    "teraboxapp.com", "1024tera.com", "1024terabox.com", "freeterabox.com",
    "4funbox.com", "terabox.vip", "terabox.net", "teraboxshare.com","terasharefile.com",
    "tboxdownloader.in", "4shared.com", "mirrobox.com", "momerybox.com",
    "nephobox.com", "tibibox.com", "terabox.fun", "terafileshare.com",
    "teraboxlink.com", "tbox.link", "tbox.app", "tera-box.com",
    "teradl.com", "mybox.run", "terasharelink.com", "1024tera.link",
    "1024terabox.link", "teraboxs.com", "teraboxup.com", "teraboxsharelink.com",
]

HEADERS = {
    "accept":          "*/*",
    "accept-language": "en-US,en;q=0.7",
    "content-type":    "application/json",
    "origin":          "https://tboxdownloader.in",
    "referer":         "https://tboxdownloader.in/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
}

def _make_resilient_session(retries: int = 3) -> requests.Session:
    """Create a requests session with retry logic for resilient API calls."""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=1,  # 1s, 2s, 4s backoff
        status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP codes
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# ── API 1 endpoints (subhodas workers) ───────────────────────────────
_SURL_EP  = os.environ.get("SURL_EP", "")
_SHARE_EP = os.environ.get("SHARE_EP", "")
_DL_EP    = os.environ.get("DL_EP", "")


def human_size(size) -> str:
    try:
        size = int(size)
    except (TypeError, ValueError):
        return "N/A"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def _parse_size_bytes(size) -> int:
    if size is None:
        return 0
    if isinstance(size, bool):
        return 0
    if isinstance(size, (int, float)):
        try:
            return int(size)
        except (TypeError, ValueError):
            return 0
    if isinstance(size, str):
        size = size.strip()
        if size.isdigit():
            return int(size)
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(B|KB|MB|GB|TB)\b", size, re.I)
        if m:
            try:
                value = float(m.group(1))
            except ValueError:
                return 0
            unit = m.group(2).upper()
            multipliers = {
                "B": 1,
                "KB": 1024,
                "MB": 1024 ** 2,
                "GB": 1024 ** 3,
                "TB": 1024 ** 4,
            }
            return int(value * multipliers.get(unit, 1))
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)", size)
        if m:
            try:
                return int(float(m.group(1)))
            except ValueError:
                return 0
    return 0


def human_duration(sec) -> str:
    if not sec:
        return "N/A"
    # Accept "HH:MM:SS" strings (from playertera) or integers
    if isinstance(sec, str) and ":" in sec:
        parts = sec.strip().split(":")
        try:
            if len(parts) == 3:
                sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                sec = int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            return sec
    try:
        sec = int(sec)
    except (TypeError, ValueError):
        return str(sec)
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return (f"{h}h {m}m {s}s" if h else f"{m}m {s}s" if m else f"{s}s")


def is_terabox_url(text: str) -> bool:
    text = text.strip()
    return text.startswith("http") and any(d in text.lower() for d in TERABOX_DOMAINS)


def extract_terabox_links(text: str) -> list[str]:
    if not text:
        return []
    found = []
    for url in re.findall(r"https?://[^\s]+", text):
        for domain in TERABOX_DOMAINS:
            if domain in url.lower():
                clean = url.replace("\\", "").rstrip(")>]\"'")
                if clean not in found:
                    found.append(clean)
                break
# ══════════════════════════════════════════════════════════════════════
# MEGA.NZ HIGH-PERFORMANCE CLOUD ENGINE (FILES & FOLDERS)
# ══════════════════════════════════════════════════════════════════════

MEGA_DOMAINS = ["mega.nz", "mega.co.nz", "mega.io"]

def is_mega_url(text: str) -> bool:
    text = (text or "").strip().lower()
    return any(d in text for d in MEGA_DOMAINS)

def extract_mega_links(text: str) -> list[str]:
    if not text:
        return []
    found = []
    for url in re.findall(r"https?://[^\s]+", text):
        if any(d in url.lower() for d in MEGA_DOMAINS):
            clean = url.replace("\\", "").rstrip(")>]\"'")
            if clean not in found:
                found.append(clean)
    return found

def _mega_base64url_decode(s: str) -> bytes:
    s = s.replace("-", "+").replace("_", "/")
    pad = (4 - len(s) % 4) % 4
    return base64.b64decode(s + "=" * pad)

def _mega_base64url_encode(b: bytes) -> str:
    return base64.b64encode(b).decode().replace("+", "-").replace("/", "_").rstrip("=")

def _parse_mega_link(url: str) -> tuple[str, str, str]:
    m = re.search(r"mega\.nz/folder/([^#]+)#(.+)", url)
    if m:
        return "folder", m.group(1), m.group(2)
    m = re.search(r"mega\.nz/#F!([^!]+)!(.+)", url)
    if m:
        return "folder", m.group(1), m.group(2)
    m = re.search(r"mega\.nz/file/([^#]+)#(.+)", url)
    if m:
        return "file", m.group(1), m.group(2)
    m = re.search(r"mega\.nz/#!([^!]+)!(.+)", url)
    if m:
        return "file", m.group(1), m.group(2)
    raise ValueError("Invalid MEGA link format.")

def _derive_mega_key_iv(key_str: str) -> tuple[bytes, bytes]:
    raw = _mega_base64url_decode(key_str)
    if len(raw) != 32:
        raise ValueError(f"Invalid key length ({len(raw)} bytes).")
    k = struct.unpack(">8I", raw)
    aes_key = struct.pack(">4I", k[0] ^ k[4], k[1] ^ k[5], k[2] ^ k[6], k[3] ^ k[7])
    iv = struct.pack(">4I", k[4], k[5], 0, 0)
    return aes_key, iv

def _derive_mega_folder_key(key_str: str) -> bytes:
    raw = _mega_base64url_decode(key_str)
    if len(raw) != 16:
        raise ValueError(f"Invalid folder key length ({len(raw)} bytes).")
    return raw

def _decrypt_mega_node_key(encrypted_key_b64: str, folder_master_key: bytes) -> bytes:
    from Crypto.Cipher import AES
    raw = _mega_base64url_decode(encrypted_key_b64)
    cipher = AES.new(folder_master_key, AES.MODE_ECB)
    return cipher.decrypt(raw)

def _decrypt_mega_attributes(at_b64: str, aes_key: bytes) -> dict:
    from Crypto.Cipher import AES
    raw = _mega_base64url_decode(at_b64)
    cipher = AES.new(aes_key, AES.MODE_CBC, iv=b"\x00" * 16)
    decrypted = cipher.decrypt(raw)
    text = decrypted.decode("utf-8", errors="ignore")
    if text.startswith("MEGA"):
        text = text[4:]
    text = text.strip("\x00").strip()
    end = text.rfind("}") + 1
    return json.loads(text[:end])

def _mega_api_request(payload: list, params: dict = None) -> list:
    url = "https://g.api.mega.co.nz/cs"
    resp = requests.post(url, json=payload, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, int):
        raise RuntimeError(f"MEGA API error {data}")
    return data

def _get_mega_file_info(file_id: str) -> dict:
    data = _mega_api_request([{"a": "g", "g": 1, "p": file_id}])
    result = data[0] if isinstance(data, list) else data
    if isinstance(result, int):
        raise RuntimeError(f"MEGA API error {result}")
    return result

def _get_mega_folder_nodes(folder_id: str) -> list:
    data = _mega_api_request([{"a": "f", "c": 1, "r": 1}], params={"n": folder_id})
    result = data[0] if isinstance(data, list) else data
    if isinstance(result, int):
        raise RuntimeError(f"MEGA API error {result}")
    return result.get("f", [])

def _get_mega_folder_file_url(node_id: str, folder_id: str) -> dict:
    data = _mega_api_request([{"a": "g", "g": 1, "n": node_id}], params={"n": folder_id})
    result = data[0] if isinstance(data, list) else data
    if isinstance(result, int):
        raise RuntimeError(f"MEGA API error {result}")
    return result

def _make_mega_ctr_cipher(aes_key: bytes, iv: bytes, offset_bytes: int = 0):
    from Crypto.Cipher import AES
    from Crypto.Util import Counter
    nonce_int = int.from_bytes(iv[:8], "big")
    block_offset = offset_bytes // 16
    initial_value = (nonce_int << 64) + block_offset
    ctr = Counter.new(128, initial_value=initial_value, little_endian=False)
    cipher = AES.new(aes_key, AES.MODE_CTR, counter=ctr)
    partial = offset_bytes % 16
    if partial:
        cipher.decrypt(b"\x00" * partial)
    return cipher

def _download_and_decrypt_mega(download_url: str, aes_key: bytes, iv: bytes, filepath: str, file_size: int) -> None:
    resp = requests.get(download_url, stream=True, timeout=60)
    if resp.status_code not in (200, 206):
        raise RuntimeError(f"Mega download server returned HTTP {resp.status_code}")
    cipher = _make_mega_ctr_cipher(aes_key, iv, offset_bytes=0)
    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 128):
            if chunk:
                f.write(cipher.decrypt(chunk))

def process_mega_link_sync(url: str) -> dict:
    """
    Extract file or folder metadata from Mega.nz.
    """
    kind, link_id, key_str = _parse_mega_link(url)
    if kind == "file":
        info = _get_mega_file_info(link_id)
        download_url = info.get("g")
        file_size = info.get("s", 0)
        at_b64 = info.get("at", "")
        aes_key, iv = _derive_mega_key_iv(key_str)
        filename = link_id
        if at_b64:
            try:
                attrs = _decrypt_mega_attributes(at_b64, aes_key)
                filename = attrs.get("n", link_id)
            except Exception:
                pass
        return {
            "filename": filename,
            "title": filename,
            "size_bytes": file_size,
            "size": file_size,
            "size_human": human_size(file_size) if file_size else "Unknown",
            "download": download_url or url,
            "is_mega": True,
            "is_folder": False,
            "mega_url": url,
            "file_id": link_id,
            "key_str": key_str,
            "aes_key": aes_key,
            "iv": iv,
            "stream_360p": "",
            "stream_480p": "",
            "stream_720p": "",
            "stream_1080p": "",
            "direct_link": download_url or url,
            "is_hls": False,
            "extracted_by": "MegaDL-v2"
        }
    else:
        # Folder link
        folder_master_key = _derive_mega_folder_key(key_str)
        nodes = _get_mega_folder_nodes(link_id)
        node_map = {}
        all_ids = {n.get("h") for n in nodes}
        root_id = None

        for node in nodes:
            ntype = node.get("t")
            node_id = node.get("h")
            parent_id = node.get("p")
            at_b64 = node.get("a", "")
            key_b64 = node.get("k", "")
            if ":" in key_b64:
                key_b64 = key_b64.split(":")[-1]
            name = node_id
            node_key = None
            if key_b64 and folder_master_key:
                try:
                    raw_key = _decrypt_mega_node_key(key_b64, folder_master_key)
                    node_key = raw_key
                    if len(raw_key) == 32:
                        k = struct.unpack(">8I", raw_key)
                        attr_key = struct.pack(">4I", k[0] ^ k[4], k[1] ^ k[5], k[2] ^ k[6], k[3] ^ k[7])
                    else:
                        attr_key = raw_key[:16]
                    if at_b64:
                        attrs = _decrypt_mega_attributes(at_b64, attr_key)
                        name = attrs.get("n", node_id)
                except Exception:
                    pass
            if ntype == 1 and parent_id not in all_ids:
                root_id = node_id
            node_map[node_id] = {
                "id": node_id, "parent": parent_id, "type": ntype,
                "name": name, "key": node_key, "size": node.get("s", 0)
            }

        files = []
        for n in node_map.values():
            if n["type"] == 0 and n.get("key") and len(n["key"]) >= 32:
                files.append(n)

        total_size = sum(f["size"] for f in files)
        root_name = node_map.get(root_id, {}).get("name", link_id) if root_id else link_id

        return {
            "filename": root_name,
            "title": f"📁 Folder: {root_name} ({len(files)} files)",
            "size_bytes": total_size,
            "size": total_size,
            "size_human": human_size(total_size) if total_size else "Unknown",
            "download": url,
            "is_mega": True,
            "is_folder": True,
            "mega_url": url,
            "folder_id": link_id,
            "key_str": key_str,
            "folder_files": files,
            "stream_360p": "",
            "stream_480p": "",
            "stream_720p": "",
            "stream_1080p": "",
            "direct_link": url,
            "is_hls": False,
            "extracted_by": "MegaDL-v2"
        }


# ══════════════════════════════════════════════════════════════════════
# DIRECT LINK ENGINE  (any http(s) file URL, incl. Google Drive)
# ══════════════════════════════════════════════════════════════════════
#
# Unlike the Terabox cascade this needs no third-party API: the bot simply
# fetches the URL itself. That makes it the most reliable path, but it also
# means the URL comes straight from a user, so every request is screened for
# SSRF first (see _is_safe_public_url).

GDRIVE_DOMAINS = ["drive.google.com", "docs.google.com", "drive.usercontent.google.com"]


def is_gdrive_url(text: str) -> bool:
    t = (text or "").strip().lower()
    return t.startswith("http") and any(d in t for d in GDRIVE_DOMAINS)


def _gdrive_file_id(url: str) -> Optional[str]:
    """Pull the file id out of any of Google Drive's share-link shapes."""
    for pat in (r"/file/d/([A-Za-z0-9_-]{10,})",
                r"/d/([A-Za-z0-9_-]{10,})",
                r"[?&]id=([A-Za-z0-9_-]{10,})"):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def _gdrive_direct_url(url: str) -> Optional[str]:
    """Share link → direct download URL.

    Uses the usercontent host with confirm=t, which serves the file straight
    away instead of the 'virus scan warning' interstitial that the old
    /uc?export=download endpoint returns for large files.
    """
    fid = _gdrive_file_id(url)
    if not fid:
        return None
    return ("https://drive.usercontent.google.com/download"
            f"?id={fid}&export=download&confirm=t")


def _is_safe_public_url(url: str) -> tuple[bool, str]:
    """Reject anything that is not a public http(s) address.

    The bot runs with its token and cloud credentials in the environment, so a
    user-supplied URL must never be able to reach loopback, private ranges or
    the cloud metadata service (169.254.169.254) and have the body handed back.
    """
    import ipaddress
    import socket

    try:
        p = urllib.parse.urlparse(url)
    except Exception:
        return False, "Malformed URL."
    if p.scheme not in ("http", "https"):
        return False, "Only http:// and https:// links are supported."
    host = p.hostname
    if not host:
        return False, "URL has no host."
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False, f"Cannot resolve host {host}."
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return False, "That address is not publicly routable."
    return True, ""


def _filename_from_headers(url: str, headers) -> str:
    """Prefer Content-Disposition, fall back to the URL path."""
    cd = headers.get("Content-Disposition") or headers.get("content-disposition") or ""
    m = re.search(r"filename\*=(?:UTF-8'')?([^;]+)", cd, re.I) or \
        re.search(r'filename="([^"]+)"', cd, re.I) or \
        re.search(r"filename=([^;]+)", cd, re.I)
    name = ""
    if m:
        name = urllib.parse.unquote(m.group(1).strip().strip('"'))
    if not name:
        path = urllib.parse.urlparse(url).path
        name = urllib.parse.unquote(os.path.basename(path))
    name = name.strip()
    if not name or name in (".", ".."):
        name = "file.bin"
    return _clean_name(name, 90)


# mimetypes is inconsistent across Python builds for these, so pin the ones
# that decide how Telegram renders the upload.
_MIME_EXT_OVERRIDES = {
    "video/mp4": ".mp4", "video/x-matroska": ".mkv", "video/quicktime": ".mov",
    "video/webm": ".webm", "video/x-msvideo": ".avi", "video/mpeg": ".mpeg",
    "audio/mpeg": ".mp3", "audio/mp4": ".m4a", "audio/ogg": ".ogg",
    "audio/flac": ".flac", "audio/x-wav": ".wav", "audio/wav": ".wav",
    "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
    "image/gif": ".gif",
    "application/zip": ".zip", "application/x-7z-compressed": ".7z",
    "application/vnd.rar": ".rar", "application/x-rar-compressed": ".rar",
    "application/pdf": ".pdf",
    "application/vnd.android.package-archive": ".apk",
}


def _ensure_extension(filename: str, content_type: str) -> str:
    """Give an extensionless name one derived from Content-Type.

    Hosts like FileDitch serve files under opaque names with no extension, and
    without one _detect_file_category treats a video as a generic document, so
    it uploads without a player.
    """
    if os.path.splitext(filename)[1]:
        return filename
    ctype = (content_type or "").split(";")[0].strip().lower()
    if not ctype or ctype == "application/octet-stream":
        return filename
    ext = _MIME_EXT_OVERRIDES.get(ctype)
    if not ext:
        import mimetypes
        ext = mimetypes.guess_extension(ctype) or ""
    return f"{filename}{ext}" if ext else filename


_HTML_CTYPES = ("text/html", "application/xhtml+xml")

_HTML_SNIFF_RE = re.compile(rb"^(?:<!doctype\s+html|<html|<head|<body|<script|<!--|<\?xml)", re.I)


def _looks_like_html(chunk: bytes) -> bool:
    """True when the first bytes of a body really are a web page.

    Content-Type alone is not evidence: file hosts routinely label every
    response text/html, so a genuine .rar would be refused on the header. The
    bytes settle it.
    """
    if not chunk:
        return False
    head = chunk[:1024]
    if head[:3] == b"\xef\xbb\xbf":
        head = head[3:]
    return bool(_HTML_SNIFF_RE.match(head.lstrip()))


def _ctype_of(resp) -> str:
    return (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()


def probe_direct_link(url: str) -> dict:
    """Look up name / size / type without downloading the body.

    Raises RuntimeError with a plain-text user-facing message when the URL is
    unusable — the caller HTML-escapes it, so no markup here.
    """
    ok, why = _is_safe_public_url(url)
    if not ok:
        raise RuntimeError(why)

    s = _make_resilient_session(retries=2)
    hdrs = {"User-Agent": HEADERS.get("user-agent", "")}
    resp = None
    used_get = False
    try:
        try:
            resp = s.head(url, headers=hdrs, allow_redirects=True, timeout=20)
        except Exception:
            resp = None
        # A HEAD is only a hint. Many file hosts answer it with an error page,
        # omit the length, or report text/html for a real download, so re-ask
        # with GET whenever it looks unhelpful and judge from that response.
        if (resp is None or resp.status_code >= 400
                or not resp.headers.get("Content-Length")
                or _ctype_of(resp) in _HTML_CTYPES):
            if resp is not None:
                try:
                    resp.close()
                except Exception:
                    pass
            resp = s.get(url, headers=hdrs, stream=True, allow_redirects=True, timeout=25)
            used_get = True
    except Exception as e:
        raise RuntimeError(f"Could not reach the link: {e}") from e

    try:
        if resp.status_code >= 400:
            raise RuntimeError(f"Server returned HTTP {resp.status_code}.")

        # The final hop must still be public — redirects can leave the safe set.
        ok, why = _is_safe_public_url(resp.url)
        if not ok:
            raise RuntimeError(f"Redirected to a blocked address. {why}")

        ctype = _ctype_of(resp)
        if ctype in _HTML_CTYPES:
            sniff = b""
            if used_get:
                try:
                    sniff = next(resp.iter_content(2048), b"") or b""
                except Exception:
                    sniff = b""
            if not used_get or _looks_like_html(sniff):
                raise RuntimeError(
                    "That link returns a web page, not a file.\n"
                    "Send the direct file link — the one that starts the download."
                )
            # Mislabelled: the bytes are a file. Drop the bogus type so the
            # name and extension decide how it is sent.
            log.info(f"[direct link] {url[:80]} says {ctype} but the body is not HTML — accepting.")
            ctype = ""

        size = 0
        cl = resp.headers.get("Content-Length")
        if cl and str(cl).isdigit():
            size = int(cl)

        return {
            "filename":   _ensure_extension(
                              _filename_from_headers(str(resp.url), resp.headers),
                              ctype),
            "size":       size,
            "size_human": human_size(size) if size else "Unknown",
            "download":   str(resp.url),
            "content_type": ctype or "application/octet-stream",
        }
    finally:
        try:
            resp.close()
        except Exception:
            pass

# ══════════════════════════════════════════════════════════════════════
# MULTI-API EXTRACTION SYSTEM
# ══════════════════════════════════════════════════════════════════════
#
#  Priority order:
#    API 1 — subhodas Cloudflare Workers (original, fastest when up)
#    API 2 — playertera.com  (HTML scraping, rich metadata)
#
#  Both sync and async variants exist.
#  cascade_extract_sync() tries each API in order, returns first success.
#  cascade_extract_async() does the same inside async tasks.
# ══════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════
# SECTION P — PROXY MANAGER
# ══════════════════════════════════════════════════════════════════════

_PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
]

_PROXY_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PROXY_VALIDATE_TIMEOUT = 6    # seconds to test each proxy
_PROXY_MIN_POOL         = 8    # keep at least this many live proxies
_PROXY_MAX_RAW          = 150  # max raw proxies to validate per refresh
_PROXY_REFRESH_INTERVAL = 1800 # seconds between automatic pool refresh (30 min)

import logging as _log_module
_plog = _log_module.getLogger("proxy_manager")


class ProxyManager:
    """Thread-safe rotating proxy pool with auto-refresh."""

    def __init__(self):
        self._pool:    list[str] = []   # ["http://ip:port", ...]
        self._idx:     int       = 0
        self._lock:    threading.Lock = threading.Lock()
        self._ready:   threading.Event = threading.Event()
        self._bad:     set = set()      # blacklisted proxies

    def get(self) -> Optional[dict]:
        """Return next proxy dict for requests, or None if pool empty."""
        premium = os.getenv("PREMIUM_PROXY") or os.getenv("PROXY_URL")
        if premium:
            premium = premium.strip()
            if not (premium.startswith("http://") or premium.startswith("https://") or premium.startswith("socks5://")):
                premium = f"http://{premium}"
            return {"http": premium, "https": premium}
        with self._lock:
            live = [p for p in self._pool if p not in self._bad]
            if not live:
                return None
            p = live[self._idx % len(live)]
            self._idx += 1
        return {"http": p, "https": p}

    def mark_bad(self, proxy_url: str) -> None:
        """Remove a proxy that caused errors."""
        if os.getenv("PREMIUM_PROXY") or os.getenv("PROXY_URL"):
            return
        with self._lock:
            self._bad.add(proxy_url)
            _plog.debug(f"[proxy] marked bad: {proxy_url}")

    def size(self) -> int:
        if os.getenv("PREMIUM_PROXY") or os.getenv("PROXY_URL"):
            return 1
        with self._lock:
            return len([p for p in self._pool if p not in self._bad])

    def start(self) -> None:
        """Build initial pool then start background refresh thread."""
        t = threading.Thread(target=self._bootstrap, daemon=True, name="ProxyBootstrap")
        t.start()

    def wait_ready(self, timeout: float = 60) -> bool:
        """Block until at least one proxy is available."""
        if os.getenv("PREMIUM_PROXY") or os.getenv("PROXY_URL"):
            return True
        return self._ready.wait(timeout)

    def _bootstrap(self):
        self._refresh()
        self._ready.set()
        while True:
            time.sleep(_PROXY_REFRESH_INTERVAL)
            self._refresh()

    def _fetch_raw(self) -> list[str]:
        raw: set[str] = set()
        for src in _PROXY_SOURCES:
            try:
                r = requests.get(src, timeout=10, headers={"User-Agent": _PROXY_UA})
                if r.status_code == 200:
                    for line in r.text.splitlines():
                        line = line.strip().replace("http://","").replace("https://","")
                        if re.match(r"^\d{1,3}(?:\.\d{1,3}){3}:\d{2,5}$", line):
                            raw.add(line)
            except Exception:
                pass
        result = list(raw)
        random.shuffle(result)
        _plog.info(f"[proxy] fetched {len(result)} raw from {len(_PROXY_SOURCES)} sources")
        return result[:_PROXY_MAX_RAW]

    def _test_one(self, ip_port: str) -> Optional[str]:
        url = f"http://{ip_port}"
        try:
            r = requests.get(
                "http://httpbin.org/ip",
                proxies={"http": url, "https": url},
                timeout=_PROXY_VALIDATE_TIMEOUT,
                headers={"User-Agent": _PROXY_UA},
                verify=False,
            )
            if r.status_code == 200:
                return url
        except Exception:
            pass
        return None

    def _refresh(self):
        if os.getenv("PREMIUM_PROXY") or os.getenv("PROXY_URL"):
            _plog.info("[proxy] Premium proxy configured; skipping public list refresh.")
            return
        _plog.info("[proxy] Refreshing pool…")
        raw = self._fetch_raw()
        good: list[str] = []

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=40) as ex:
            futs = {ex.submit(self._test_one, p): p for p in raw}
            for fut in as_completed(futs):
                result = fut.result()
                if result:
                    good.append(result)
                    _plog.info(f"[proxy] ✅ {result}  (pool={len(good)})")
                    if len(good) >= _PROXY_MIN_POOL * 3:
                        for f in futs: f.cancel()
                        break

        with self._lock:
            self._pool = good
            self._bad.clear()
            self._idx  = 0

        _plog.info(f"[proxy] Pool refreshed → {len(good)} proxies ready")


proxy_mgr = ProxyManager()


def _s(use_proxy: bool = False) -> requests.Session:
    session = requests.Session()
    session.verify = False
    retry = Retry(
        total=1, backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST", "HEAD"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://",  HTTPAdapter(max_retries=retry))
    if use_proxy:
        px = proxy_mgr.get()
        if px:
            session.proxies.update(px)
    return session


def _start_proxy_manager():
    _plog.info("[proxy] Starting proxy manager…")
    proxy_mgr.start()
    ready = proxy_mgr.wait_ready(timeout=5)
    if ready:
        _plog.info(f"[proxy] Ready with {proxy_mgr.size()} proxies")
    else:
        _plog.warning("[proxy] Timeout waiting for proxies — will continue in background")


_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# ─── HELPERS ──────────────────────────────────────────────────────────

def _has_dl(data) -> bool:
    if not isinstance(data, dict):
        return False
    for k in ["download","download_url","url","direct_link","dlink",
               "link","download_link","direct","play_url"]:
        v = data.get(k)
        if v and isinstance(v, str) and v.startswith("http"):
            return True
    for k in ["data","result","file"]:
        inner = data.get(k)
        if isinstance(inner, list) and inner:
            inner = inner[0]
        if isinstance(inner, dict) and _has_dl(inner):
            return True
    files = data.get("files") or data.get("list") or []
    if isinstance(files, list) and files:
        for k in ["download_url","dlink","url","download","normal_dlink","direct_link"]:
            if str(files[0].get(k,"")).startswith("http"):
                return True
    return False

def _get_dl(data) -> str:
    if not isinstance(data, dict):
        return ""
    for k in ["download","download_url","url","direct_link","dlink",
               "link","download_link","direct","play_url"]:
        v = str(data.get(k,""))
        if v.startswith("http"):
            return v
    for k in ["data","result","file"]:
        inner = data.get(k)
        if isinstance(inner, list) and inner:
            inner = inner[0]
        if isinstance(inner, dict):
            u = _get_dl(inner)
            if u: return u
    files = data.get("files") or data.get("list") or []
    if isinstance(files, list) and files:
        for k in ["download_url","dlink","url","download","normal_dlink","direct_link"]:
            v = str(files[0].get(k,""))
            if v.startswith("http"):
                return v
    return ""

def _norm(data: dict, api_name: str) -> Optional[dict]:
    dl = _get_dl(data)
    if not dl:
        return None
    inner = data.get("data") or data.get("result") or data.get("file") or data
    if isinstance(inner, list) and inner:
        inner = inner[0]
    if not isinstance(inner, dict):
        inner = data
    streams = inner.get("streams") or inner.get("fast_streams") or inner.get("stream_urls") or {}
    return {
        "api":            api_name,
        "title":          inner.get("title") or inner.get("filename") or inner.get("name"),
        "filename":       inner.get("filename") or inner.get("name") or inner.get("server_filename"),
        "size":           inner.get("size"),
        "size_human":     (inner.get("size_human") or inner.get("size_formatted")
                           or inner.get("filesize") or inner.get("file_size")),
        "duration":       inner.get("duration"),
        "duration_human": inner.get("duration_human", "N/A"),
        "width":          inner.get("width"),
        "height":         inner.get("height"),
        "thumb":          inner.get("thumbnail") or inner.get("thumb") or inner.get("cover"),
        "download":       dl,
        "stream_360p":    streams.get("360p") or inner.get("stream_360p"),
        "stream_480p":    streams.get("480p") or inner.get("stream_480p"),
        "stream_720p":    streams.get("720p") or inner.get("stream_720p"),
        "stream_1080p":   streams.get("1080p") or inner.get("stream_1080p"),
    }

# ─── ORIGINAL 9 APIs (proxy-aware rewrites) ──────────────────────────

def _api1_sync(link: str, retries: int = 2) -> Optional[dict]:
    for attempt in range(1, retries + 1):
        try:
            H = {"content-type":"application/json","origin":"https://tboxdownloader.in",
                 "referer":"https://tboxdownloader.in/","user-agent":_UA}
            px = proxy_mgr.get()
            r1 = requests.post("https://tbox-surl-v6.subhodas5673.workers.dev/",
                               json={"url":link}, headers=H, timeout=30, proxies=px)
            r1.raise_for_status(); d1 = r1.json()
            r2 = requests.post("https://tbox-share-list-v2.subhodas5673.workers.dev/",
                               json={"domain":d1["domain"],"surl":d1["surl"],
                                     "root":d1.get("root",1),"page":d1.get("page",1)},
                               headers=H, timeout=30, proxies=px)
            r2.raise_for_status(); d2 = r2.json(); f = d2["list"][0]
            r3 = requests.post("https://tbox-download-play-basic.subhodas5673.workers.dev/",
                               json={"share_id":d2["share_id"],"uk":d2["uk"],
                                     "fs_id":f["fs_id"],"domain":d2["domain"]},
                               headers=H, timeout=30, proxies=px)
            r3.raise_for_status(); d3 = r3.json()
            streams = d3.get("streams",{})
            return {"api":"workers","title":d2.get("title"),
                    "filename":f.get("server_filename"),"size":f.get("size"),
                    "size_human":str(f.get("size",0)),"duration":f.get("duration"),
                    "duration_human":"N/A","width":f.get("width"),"height":f.get("height"),
                    "thumb":f.get("thumbs",{}).get("url3"),"download":d3.get("download"),
                    "stream_360p":streams.get("360p"),"stream_480p":streams.get("480p"),
                    "stream_720p":streams.get("720p"),"stream_1080p":streams.get("1080p")}
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            if code in (502,503,504) and attempt < retries:
                time.sleep(attempt*4); continue
            log.warning(f"[API1] HTTP {code}: {e}"); return None
        except Exception as e:
            log.warning(f"[API1] {e}"); return None
    return None

def _api2_sync(link: str) -> Optional[dict]:
    try:
        BASE = "https://playertera.com"
        s = _s()
        r1 = s.get(BASE, headers={"accept":"text/html,*/*","referer":"https://search.brave.com/",
                                   "user-agent":_UA}, timeout=15)
        r1.raise_for_status()
        tok = re.search(r'name="_token" value="([^"]+)"', r1.text)
        if not tok: return None
        r2 = s.post(f"{BASE}/process-web",
                    headers={"accept":"text/html,*/*","content-type":"application/x-www-form-urlencoded",
                             "origin":BASE,"referer":BASE+"/","user-agent":_UA},
                    data={"_token":tok.group(1),"url":link}, timeout=30, allow_redirects=True)
        r2.raise_for_status()
        dl_m = re.search(r'const\s+normalDlink\s*=\s*"(.*?)";', r2.text, re.DOTALL)
        if not dl_m: return None
        download_url = dl_m.group(1).replace("\\/","/").replace("\\u0026","&")
        streams_m = re.search(r'const\s+streams\s*=\s*(\{.*?\});', r2.text, re.DOTALL)
        stream_links: dict = {}
        if streams_m:
            for q,u in re.findall(r'"(\d+p)"\s*:\s*"(.*?)"', streams_m.group(1)):
                stream_links[q] = u.replace("\\/","/")
        fname_m = re.search(r'const\s+fname\s*=\s*"(.*?)";', r2.text)
        size_m  = re.search(r'(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB)\b', r2.text)
        return {"api":"playertera","title":fname_m.group(1) if fname_m else None,
                "filename":fname_m.group(1) if fname_m else None,"size":None,
                "size_human":f"{size_m.group(1)} {size_m.group(2)}" if size_m else None,
                "duration":None,"duration_human":"N/A","width":None,"height":None,"thumb":None,
                "download":download_url,"stream_360p":stream_links.get("360p"),
                "stream_480p":stream_links.get("480p"),"stream_720p":stream_links.get("720p"),
                "stream_1080p":stream_links.get("1080p")}
    except Exception as e:
        log.warning(f"[API2] {e}"); return None

def _api3_sync(link: str) -> Optional[dict]:
    try:
        BASE = "https://www.playteraboxvideo.pro"
        s = _s()
        s.get(BASE, headers={"user-agent":_UA}, timeout=10)
        r = s.post(f"{BASE}/getplay", json={"url":link},
                   headers={"accept":"*/*","content-type":"application/json",
                            "origin":BASE,"referer":BASE+"/","user-agent":_UA}, timeout=30)
        r.raise_for_status()
        d = r.json()
        if not d.get("success",True) or not d.get("play_url"): return None
        return {"api":"playteraboxvideo","title":d.get("title"),"filename":None,
                "size":None,"size_human":None,"duration":None,"duration_human":"N/A",
                "width":None,"height":None,"thumb":d.get("thumbnail"),
                "download":d["play_url"],"stream_360p":d["play_url"],
                "stream_480p":None,"stream_720p":None,"stream_1080p":None}
    except Exception as e:
        log.warning(f"[API3] {e}"); return None

def _api4_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        r = s.post("https://teraboxdl-frontend.pages.dev/api/proxy", json={"url":link},
                   headers={"accept":"application/json","content-type":"application/json",
                            "origin":"https://teraboxdl-frontend.pages.dev",
                            "referer":"https://teraboxdl-frontend.pages.dev/","user-agent":_UA},
                   timeout=30)
        r.raise_for_status()
        d = r.json()
        if not d.get("list"): return None
        item = d["list"][0]
        return {"api":"teraboxdl-frontend","title":item.get("server_filename"),
                "filename":item.get("server_filename"),"size":item.get("size"),
                "size_human":item.get("formatted_size"),"duration":item.get("duration"),
                "duration_human":"N/A","width":None,"height":None,
                "thumb":item.get("thumbs",{}).get("url1"),
                "download":item.get("direct_link"),"stream_360p":item.get("stream_url"),
                "stream_480p":None,"stream_720p":None,"stream_1080p":None}
    except Exception as e:
        log.warning(f"[API4] {e}"); return None

def _api5_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        s.get("https://teradownloaderx.pro/", headers={"User-Agent":_UA}, timeout=15)
        r = s.post("https://teradownloaderx.pro/api/proxy-terabox", json={"url":link},
                   headers={"Accept":"*/*","Content-Type":"application/json",
                            "Origin":"https://teradownloaderx.pro",
                            "Referer":f"https://teradownloaderx.pro/watch?url={link}",
                            "User-Agent":_UA}, timeout=60)
        r.raise_for_status()
        d = r.json()
        if d.get("status") != "success" or not d.get("list"): return None
        f = d["list"][0]
        return {"api":"teradownloaderx","filename":f.get("name"),"size":f.get("size"),
                "size_human":f.get("size_formatted"),"duration":f.get("duration"),
                "duration_human":"N/A","width":None,"height":None,"thumb":f.get("thumbnail"),
                "download":f.get("normal_dlink"),
                "stream_360p":f.get("fast_stream_url",{}).get("360p"),
                "stream_480p":f.get("fast_stream_url",{}).get("480p"),
                "stream_720p":None,"stream_1080p":None}
    except Exception as e:
        log.warning(f"[API5] {e}"); return None

def _api6_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        s.get("https://theteraboxdownloader.com/folder", headers={"User-Agent":_UA}, timeout=15)
        r = s.get("https://theteraboxdownloader.com/api/folder", params={"data":link},
                  headers={"Accept":"*/*","Referer":"https://theteraboxdownloader.com/folder",
                           "User-Agent":_UA}, timeout=60)
        r.raise_for_status()
        d = r.json()
        files = d.get("list") or d.get("files") or d.get("data",{}).get("files") or []
        if not files: return None
        f = files[0]
        return {"api":"theteraboxdownloader","filename":f.get("name"),"size":f.get("size"),
                "size_human":f.get("size"),"duration":None,"duration_human":"N/A",
                "width":None,"height":None,"thumb":f.get("thumbnail"),
                "download":f.get("normal_dlink") or f.get("download_url"),
                "stream_360p":f.get("fast_stream_url",{}).get("360p"),
                "stream_480p":f.get("fast_stream_url",{}).get("480p"),
                "stream_720p":None,"stream_1080p":None}
    except Exception as e:
        log.warning(f"[API6] {e}"); return None

def _api7_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        s.get("https://playterabox.online/", headers={"user-agent":_UA}, timeout=15)
        r = s.get("https://playterabox.online/api/extract", params={"url":link},
                  headers={"accept":"*/*","referer":"https://playterabox.online/","user-agent":_UA},
                  timeout=30)
        r.raise_for_status()
        d = r.json()
        if not d.get("success"): return None
        streams = d.get("fast_streams",{})
        return {"api":"playterabox","title":d.get("filename"),"filename":d.get("filename"),
                "size":d.get("size"),"size_human":str(d.get("size",0)),
                "duration":d.get("duration"),"duration_human":"N/A",
                "width":None,"height":None,"thumb":d.get("thumbnail"),
                "download":d.get("download_url"),
                "stream_360p":streams.get("360p"),"stream_480p":streams.get("480p"),
                "stream_720p":None,"stream_1080p":None}
    except Exception as e:
        log.warning(f"[API7] {e}"); return None

def _api8_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        s.get("https://sechno.com/tools/terabox-downloader",
              headers={"user-agent":_UA,"referer":"https://yandex.com/"}, timeout=15)
        r = s.post("https://sechno.com/api/terabox", json={"url":link},
                   headers={"accept":"*/*","content-type":"application/json",
                            "origin":"https://sechno.com",
                            "referer":"https://sechno.com/tools/terabox-downloader",
                            "user-agent":_UA}, timeout=60)
        r.raise_for_status()
        d = r.json()
        if not d.get("files"): return None
        f = d["files"][0]
        thumb = f.get("thumbUrl","")
        if thumb.startswith("/"): thumb = "https://sechno.com" + thumb
        return {"api":"sechno","title":d.get("title"),"filename":f.get("filename"),
                "size":f.get("size"),"size_human":f.get("sizeFormatted"),
                "duration":None,"duration_human":"N/A","width":None,"height":None,
                "thumb":thumb,"download":f.get("downloadUrl"),
                "stream_360p":None,"stream_480p":None,"stream_720p":None,"stream_1080p":None}
    except Exception as e:
        log.warning(f"[API8] {e}"); return None

def _api9_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        home = s.get("https://teraboxdownloaders.com", headers={"User-Agent":_UA}, timeout=20)
        home.raise_for_status()
        nm = re.search(r'"nonce":"([^"]+)"', home.text)
        if not nm: return None
        r = s.post("https://teraboxdownloaders.com/wp-admin/admin-ajax.php",
                   data={"action":"terabox_fetch","url":link,"nonce":nm.group(1)},
                   headers={"Accept":"*/*","Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
                            "Origin":"https://teraboxdownloaders.com",
                            "Referer":"https://teraboxdownloaders.com/",
                            "X-Requested-With":"XMLHttpRequest","User-Agent":_UA}, timeout=60)
        r.raise_for_status()
        d = r.json()
        if not d.get("success"): return None
        try:
            f = d["data"]["files"][0]
            return {"api":"teraboxdownloaders","filename":f.get("name"),"size":f.get("size"),
                    "size_human":f"{f.get('size')} bytes","duration":f.get("duration"),
                    "duration_human":"N/A","width":None,"height":None,
                    "thumb":f.get("thumbnail_url"),"download":f.get("download_url"),
                    "stream_360p":f.get("stream_urls",{}).get("360p"),
                    "stream_480p":f.get("stream_urls",{}).get("480p"),
                    "stream_720p":f.get("stream_urls",{}).get("720p"),
                    "stream_1080p":f.get("stream_urls",{}).get("1080p")}
        except Exception:
            return None
    except Exception as e:
        log.warning(f"[API9] {e}"); return None

# ─── NEW APIs 10-30 ──────────────────────────────────────────────────

def _api10_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        s.get("https://teraboxvideo.ws/", headers={"User-Agent":_UA}, timeout=10)
        r = s.post("https://teraboxvideo.ws/api/getdownload", json={"url":link},
                   headers={"accept":"*/*","content-type":"application/json",
                            "origin":"https://teraboxvideo.ws",
                            "referer":"https://teraboxvideo.ws/","user-agent":_UA}, timeout=30)
        r.raise_for_status()
        return _norm(r.json(), "teraboxvideo.ws")
    except Exception as e:
        log.warning(f"[API10] {e}"); return None

def _api11_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        r = s.get("https://tera.instavideosave.com/", params={"url":link},
                  headers={"accept":"*/*","origin":"https://tera.instavideosave.com",
                           "referer":"https://tera.instavideosave.com/","user-agent":_UA}, timeout=30)
        r.raise_for_status()
        return _norm(r.json(), "instavideosave")
    except Exception as e:
        log.warning(f"[API11] {e}"); return None

def _api12_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        home = s.get("https://teradownloader.net/", headers={"User-Agent":_UA}, timeout=15)
        home.raise_for_status()
        tok = re.search(r'name=["\']?(?:_token|csrf)["\']?\s+value=["\']([^"\']+)["\']', home.text, re.I)
        payload = {"url":link}
        if tok: payload["_token"] = tok.group(1)
        r = s.post("https://teradownloader.net/download", data=payload,
                   headers={"User-Agent":_UA,"Content-Type":"application/x-www-form-urlencoded",
                            "Referer":"https://teradownloader.net/",
                            "Origin":"https://teradownloader.net"}, timeout=40, allow_redirects=True)
        r.raise_for_status()
        try:
            return _norm(r.json(), "teradownloader.net")
        except Exception:
            m = re.search(r'href=["\']?(https?://[^"\'>\s]+terabox[^"\'>\s]+)["\']?', r.text)
            if m: return _norm({"download": m.group(1)}, "teradownloader.net-html")
        return None
    except Exception as e:
        log.warning(f"[API12] {e}"); return None

def _api13_sync(link: str) -> Optional[dict]:
    import os
    key = os.environ.get("RAPIDAPI_KEY","")
    if not key: return None
    try:
        s = _s()
        r = s.get("https://terabox-downloader-direct-download-link-generator.p.rapidapi.com/url",
                  params={"url":link},
                  headers={"x-rapidapi-host":"terabox-downloader-direct-download-link-generator.p.rapidapi.com",
                           "x-rapidapi-key":key,"user-agent":_UA}, timeout=30)
        r.raise_for_status()
        return _norm(r.json(), "terabox-rapidapi")
    except Exception as e:
        log.warning(f"[API13] {e}"); return None

def _api14_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        home = s.get("https://terabox.fun", headers={"User-Agent":_UA,"Accept":"text/html"}, timeout=10)
        csrf = re.search(r'name=["\']_token["\'] value=["\']([^"\']+)["\']', home.text)
        r = s.post("https://terabox.fun/",
                   data={"url":link, **({"_token":csrf.group(1)} if csrf else {})},
                   headers={"user-agent":_UA,"content-type":"application/x-www-form-urlencoded",
                            "origin":"https://terabox.fun","referer":"https://terabox.fun/"},
                   timeout=30, allow_redirects=True)
        r.raise_for_status()
        m = re.search(r'const\s+normalDlink\s*=\s*"(.*?)";', r.text, re.DOTALL)
        if m:
            dl = m.group(1).replace("\\/","/").replace("\\u0026","&")
            return _norm({"download": dl}, "terabox.fun")
        c = re.search(r'"(https://[^\s"]+(?:bdsharevideo|d\.terabox)[^\s"]+)"', r.text)
        if c: return _norm({"download": c.group(1)}, "terabox.fun-html")
        return None
    except Exception as e:
        log.warning(f"[API14] {e}"); return None

def _api15_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        r = s.get("https://terabox-dl.vercel.app/api", params={"url":link},
                  headers={"accept":"application/json",
                           "referer":"https://terabox-dl.vercel.app/","user-agent":_UA}, timeout=30)
        r.raise_for_status()
        return _norm(r.json(), "terabox-dl-vercel")
    except Exception as e:
        log.warning(f"[API15] {e}"); return None

def _apiA_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        s.get("https://teradownloader.pro/", headers={"User-Agent":_UA}, timeout=10)
        r = s.post("https://teradownloader.pro/api/download", json={"url":link},
                   headers={"Accept":"application/json","Content-Type":"application/json",
                            "Origin":"https://teradownloader.pro",
                            "Referer":"https://teradownloader.pro/","User-Agent":_UA}, timeout=30)
        r.raise_for_status()
        return _norm(r.json(), "teradownloader.pro")
    except Exception as e:
        log.warning(f"[API-A] {e}"); return None

def _apiB_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        r = s.get("https://terabox.wiki/api/download", params={"url":link},
                  headers={"Accept":"application/json","Referer":"https://terabox.wiki/","User-Agent":_UA},
                  timeout=30)
        r.raise_for_status()
        return _norm(r.json(), "terabox.wiki")
    except Exception as e:
        log.warning(f"[API-B] {e}"); return None

def _apiC_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        r = s.post("https://tera.ninja/api/extract", json={"link":link},
                   headers={"Accept":"application/json","Content-Type":"application/json",
                            "Origin":"https://tera.ninja","Referer":"https://tera.ninja/","User-Agent":_UA},
                   timeout=30)
        r.raise_for_status()
        d = r.json()
        if not (d.get("success") or d.get("ok")): return None
        return _norm(d, "tera.ninja")
    except Exception as e:
        log.warning(f"[API-C] {e}"); return None

def _apiD_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        home = s.get("https://teraboxapp.xyz/", headers={"User-Agent":_UA,"Accept":"text/html"}, timeout=10)
        csrf = re.search(r'name=["\']_token["\'] value=["\']([^"\']+)["\']', home.text)
        r = s.post("https://teraboxapp.xyz/api",
                   data={"url":link, **({"_token":csrf.group(1)} if csrf else {})},
                   headers={"Accept":"application/json","Content-Type":"application/x-www-form-urlencoded",
                            "Origin":"https://teraboxapp.xyz","Referer":"https://teraboxapp.xyz/","User-Agent":_UA},
                   timeout=30, allow_redirects=True)
        r.raise_for_status()
        try:
            return _norm(r.json(), "teraboxapp.xyz")
        except Exception:
            c = re.search(r'"(https://[^\s"]+(?:bdsharevideo|d\.terabox)[^\s"]+)"', r.text)
            if c: return _norm({"download": c.group(1)}, "teraboxapp.xyz-html")
        return None
    except Exception as e:
        log.warning(f"[API-D] {e}"); return None

def _apiE_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        r = s.post("https://terabox-video.pro/api/get", json={"url":link},
                   headers={"Accept":"application/json","Content-Type":"application/json",
                            "Origin":"https://terabox-video.pro",
                            "Referer":"https://terabox-video.pro/","User-Agent":_UA}, timeout=30)
        r.raise_for_status()
        d = r.json()
        if d.get("error"): return None
        return _norm(d, "terabox-video.pro")
    except Exception as e:
        log.warning(f"[API-E] {e}"); return None

def _apiF_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        home = s.get("https://savevideos.me/", headers={"User-Agent":_UA}, timeout=10)
        tok = re.search(r'name=["\']_token["\'] value=["\']([^"\']+)["\']', home.text)
        r = s.post("https://savevideos.me/",
                   data={"url":link,"ajax":"1", **({"_token":tok.group(1)} if tok else {})},
                   headers={"Accept":"application/json, text/javascript, */*",
                            "Content-Type":"application/x-www-form-urlencoded",
                            "Origin":"https://savevideos.me","Referer":"https://savevideos.me/",
                            "User-Agent":_UA,"X-Requested-With":"XMLHttpRequest"}, timeout=40)
        r.raise_for_status()
        d = r.json()
        links = d.get("links") or d.get("formats") or []
        if links:
            dl = links[0].get("url","")
            if dl.startswith("http"): return _norm({"download":dl}, "savevideos.me")
        return _norm(d, "savevideos.me")
    except Exception as e:
        log.warning(f"[API-F] {e}"); return None

def _apiG_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        s.get("https://tbsave.com/", headers={"User-Agent":_UA}, timeout=10)
        r = s.post("https://tbsave.com/download", json={"url":link},
                   headers={"Accept":"application/json","Content-Type":"application/json",
                            "Origin":"https://tbsave.com","Referer":"https://tbsave.com/","User-Agent":_UA},
                   timeout=30)
        r.raise_for_status()
        return _norm(r.json(), "tbsave.com")
    except Exception as e:
        log.warning(f"[API-G] {e}"); return None

def _apiH_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        s.get("https://terabox.club/", headers={"User-Agent":_UA}, timeout=10)
        r = s.post("https://terabox.club/fetch", json={"shareurl":link},
                   headers={"Accept":"application/json","Content-Type":"application/json",
                            "Origin":"https://terabox.club","Referer":"https://terabox.club/","User-Agent":_UA},
                   timeout=30)
        r.raise_for_status()
        d = r.json()
        lst = d.get("list") or d.get("files") or []
        if not lst: return None
        return _norm(lst[0], "terabox.club")
    except Exception as e:
        log.warning(f"[API-H] {e}"); return None

def _api25_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        r = s.get(f"https://terabox.hnn.workers.dev/?url={urllib.parse.quote(link,safe='')}",
                  headers={"Accept":"application/json","User-Agent":_UA}, timeout=30)
        r.raise_for_status()
        return _norm(r.json(), "terabox.hnn.worker")
    except Exception as e:
        log.warning(f"[API25] {e}"); return None

def _api26_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        r = s.get(f"https://terabox-worker.robinkumarshakya103.workers.dev/api?url={urllib.parse.quote(link,safe='')}",
                  headers={"Accept":"application/json","User-Agent":_UA}, timeout=30)
        r.raise_for_status()
        d = r.json()
        files = d.get("files") or []
        if not d.get("success") or not files: return None
        f = files[0]
        dl = f.get("download_url") or f.get("original_download_url")
        if not dl: return None
        return {"api":"robin-worker","title":f.get("file_name"),"filename":f.get("file_name"),
                "size":None,"size_human":f.get("size"),"duration":None,"duration_human":"N/A",
                "width":None,"height":None,"thumb":None,"download":dl,
                "stream_360p":f.get("streaming_url"),"stream_480p":None,
                "stream_720p":None,"stream_1080p":None}
    except Exception as e:
        log.warning(f"[API26] {e}"); return None

def _api27_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        r = s.post("https://terasnap.netlify.app/api/download", json={"link":link},
                   headers={"Accept":"application/json","Content-Type":"application/json",
                            "Origin":"https://terasnap.netlify.app",
                            "Referer":"https://terasnap.netlify.app/","User-Agent":_UA}, timeout=30)
        r.raise_for_status()
        d = r.json()
        dl = d.get("download_link") or d.get("download") or d.get("url")
        if not dl: return None
        return {"api":"terasnap.netlify","title":d.get("file_name"),"filename":d.get("file_name"),
                "size":d.get("size_bytes"),"size_human":d.get("file_size"),
                "duration":None,"duration_human":"N/A","width":None,"height":None,
                "thumb":d.get("thumbnail"),"download":dl,
                "stream_360p":None,"stream_480p":None,"stream_720p":None,"stream_1080p":None}
    except Exception as e:
        log.warning(f"[API27] {e}"); return None

def _api28_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        home = s.get("https://tera-downloader.com/", headers={"User-Agent":_UA,"Accept":"text/html"}, timeout=15)
        tok = re.search(r'name=["\'](?:_token|token|csrf)["\'] value=["\']([^"\']+)["\']', home.text, re.I)
        payload = {"url":link}
        if tok: payload["_token"] = tok.group(1)
        r = s.post("https://tera-downloader.com/get", data=payload,
                   headers={"Accept":"application/json, text/html, */*",
                            "Content-Type":"application/x-www-form-urlencoded",
                            "Origin":"https://tera-downloader.com",
                            "Referer":"https://tera-downloader.com/","User-Agent":_UA,
                            "X-Requested-With":"XMLHttpRequest"}, timeout=30, allow_redirects=True)
        r.raise_for_status()
        try:
            return _norm(r.json(), "tera-downloader.com")
        except Exception:
            c = re.search(r'(https://[^\s"\'<>]+(?:bdsharevideo|d\.terabox)[^\s"\'<>]+)', r.text)
            if c: return _norm({"download": c.group(1)}, "tera-downloader.com-html")
        return None
    except Exception as e:
        log.warning(f"[API28] {e}"); return None

def _api29_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        s.get("https://teraboxpro.net/", headers={"User-Agent":_UA}, timeout=10)
        r = s.get("https://teraboxpro.net/api", params={"url":link},
                  headers={"Accept":"application/json","Referer":"https://teraboxpro.net/","User-Agent":_UA},
                  timeout=30)
        r.raise_for_status()
        res = _norm(r.json(), "teraboxpro.net")
        if res: return res
        r2 = s.post("https://teraboxpro.net/api/generate", json={"url":link},
                    headers={"Accept":"application/json","Content-Type":"application/json",
                             "Origin":"https://teraboxpro.net","Referer":"https://teraboxpro.net/","User-Agent":_UA},
                    timeout=30)
        r2.raise_for_status()
        return _norm(r2.json(), "teraboxpro.net")
    except Exception as e:
        log.warning(f"[API29] {e}"); return None

def _api30_sync(link: str) -> Optional[dict]:
    try:
        s = _s()
        home = s.get("https://teraboxdl.site/", headers={"User-Agent":_UA,"Accept":"text/html"}, timeout=10)
        tok = re.search(r'name=["\'](?:_token|csrf)["\'] value=["\']([^"\']+)["\']', home.text, re.I)
        payload = {"url":link}
        if tok: payload["_token"] = tok.group(1)
        ph = {"Accept":"application/json","Content-Type":"application/json",
              "Origin":"https://teraboxdl.site","Referer":"https://teraboxdl.site/","User-Agent":_UA}
        for ep in ["/api","/api/download","/download","/fetch"]:
            try:
                r = s.post(f"https://teraboxdl.site{ep}", json=payload, headers=ph, timeout=30)
                if r.status_code == 404: continue
                r.raise_for_status()
                try:
                    res = _norm(r.json(), "teraboxdl.site")
                    if res: return res
                except Exception:
                    c = re.search(r'(https://[^\s"\'<>]+(?:bdsharevideo|d\.terabox)[^\s"\'<>]+)', r.text)
                    if c: return _norm({"download": c.group(1)}, "teraboxdl.site-html")
            except Exception:
                continue
        return None
    except Exception as e:
        log.warning(f"[API30] {e}"); return None

# ── async wrappers (runs sync in threadpool) ──────────────────────────

import asyncio as _asyncio
import aiohttp as _aiohttp

def _make_async(fn):
    async def _wrapper(session: _aiohttp.ClientSession, link: str) -> Optional[dict]:
        loop = _asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, fn, link)
        except Exception as e:
            log.warning(f"[{fn.__name__}-async] {e}")
            return None
    _wrapper.__name__ = fn.__name__ + "_async"
    return _wrapper

_api1_async  = _make_async(_api1_sync)
_api2_async  = _make_async(_api2_sync)
_api3_async  = _make_async(_api3_sync)
_api4_async  = _make_async(_api4_sync)
_api5_async  = _make_async(_api5_sync)
_api6_async  = _make_async(_api6_sync)
_api7_async  = _make_async(_api7_sync)
_api8_async  = _make_async(_api8_sync)
_api9_async  = _make_async(_api9_sync)
_api10_async = _make_async(_api10_sync)
_api11_async = _make_async(_api11_sync)
_api12_async = _make_async(_api12_sync)
_api13_async = _make_async(_api13_sync)
_api14_async = _make_async(_api14_sync)
_api15_async = _make_async(_api15_sync)
_apiA_async  = _make_async(_apiA_sync)
_apiB_async  = _make_async(_apiB_sync)
_apiC_async  = _make_async(_apiC_sync)
_apiD_async  = _make_async(_apiD_sync)
_apiE_async  = _make_async(_apiE_sync)
_apiF_async  = _make_async(_apiF_sync)
_apiG_async  = _make_async(_apiG_sync)
_apiH_async  = _make_async(_apiH_sync)
_api25_async = _make_async(_api25_sync)
_api26_async = _make_async(_api26_sync)
_api27_async = _make_async(_api27_sync)
_api28_async = _make_async(_api28_sync)
_api29_async = _make_async(_api29_sync)
_api30_async = _make_async(_api30_sync)

# ─── CASCADE (sync + async) ──────────────────────────────────────────

# Ordered list of sync API functions
# Reordered: prefer API-4 first (fast), move API-3 (HLS-focused) to a later position
_SYNC_APIS = [
    # ── Fastest / most reliable (CF Workers, no CSRF) ────────────────
    ("API-26 (robin-worker)",     _api26_sync),
    ("API-25 (hnn-worker)",       _api25_sync),
    ("API-27 (terasnap)",         _api27_sync),
    ("API-04 (teraboxdl-fe)",     _api4_sync),
    ("API-15 (vercel)",           _api15_sync),
    # ── Mid-tier ─────────────────────────────────────────────────────
    ("API-26b (robin-worker)",    _api26_sync),   # intentional duplicate — highest weight
    ("API-A  (teradownloader.p)", _apiA_sync),
    ("API-B  (terabox.wiki)",     _apiB_sync),
    ("API-C  (tera.ninja)",       _apiC_sync),
    ("API-D  (teraboxapp.xyz)",   _apiD_sync),
    ("API-E  (terabox-video)",    _apiE_sync),
    ("API-F  (savevideos.me)",    _apiF_sync),
    ("API-G  (tbsave.com)",       _apiG_sync),
    ("API-H  (terabox.club)",     _apiH_sync),
    ("API-10 (teraboxvideo.ws)",  _api10_sync),
    ("API-11 (instavideosave)",   _api11_sync),
    ("API-28 (tera-downloader)",  _api28_sync),
    ("API-29 (teraboxpro.net)",   _api29_sync),
    ("API-30 (teraboxdl.site)",   _api30_sync),
    # ── Require CSRF / session warmup ────────────────────────────────
    ("API-05 (teradownloaderx)",  _api5_sync),
    ("API-06 (theteraboxdl)",     _api6_sync),
    ("API-09 (teraboxdlrs)",      _api9_sync),
    ("API-12 (teradownloader.n)", _api12_sync),
    ("API-14 (terabox.fun)",      _api14_sync),
    ("API-13 (rapidapi)",         _api13_sync),   # needs RAPIDAPI_KEY env var
    # ── Partially working / last resort ──────────────────────────────
    ("API-02 (playertera)",       _api2_sync),
    ("API-07 (playterabox)",      _api7_sync),
    ("API-08 (sechno)",           _api8_sync),
    ("API-03 (playteraboxvideo)", _api3_sync),
    ("API-01 (workers)",          _api1_sync),
]

_ASYNC_APIS = [
    ("API-26 (robin-worker)",     _api26_async),
    ("API-25 (hnn-worker)",       _api25_async),
    ("API-27 (terasnap)",         _api27_async),
    ("API-04 (teraboxdl-fe)",     _api4_async),
    ("API-15 (vercel)",           _api15_async),
    ("API-26b (robin-worker)",    _api26_async),
    ("API-A  (teradownloader.p)", _apiA_async),
    ("API-B  (terabox.wiki)",     _apiB_async),
    ("API-C  (tera.ninja)",       _apiC_async),
    ("API-D  (teraboxapp.xyz)",   _apiD_async),
    ("API-E  (terabox-video)",    _apiE_async),
    ("API-F  (savevideos.me)",    _apiF_async),
    ("API-G  (tbsave.com)",       _apiG_async),
    ("API-H  (terabox.club)",     _apiH_async),
    ("API-10 (teraboxvideo.ws)",  _api10_async),
    ("API-11 (instavideosave)",   _api11_async),
    ("API-28 (tera-downloader)",  _api28_async),
    ("API-29 (teraboxpro.net)",   _api29_async),
    ("API-30 (teraboxdl.site)",   _api30_async),
    ("API-05 (teradownloaderx)",  _api5_async),
    ("API-06 (theteraboxdl)",     _api6_async),
    ("API-09 (teraboxdlrs)",      _api9_async),
    ("API-12 (teradownloader.n)", _api12_async),
    ("API-14 (terabox.fun)",      _api14_async),
    ("API-13 (rapidapi)",         _api13_async),
    ("API-02 (playertera)",       _api2_async),
    ("API-07 (playterabox)",      _api7_async),
    ("API-08 (sechno)",           _api8_async),
    ("API-03 (playteraboxvideo)", _api3_async),
    ("API-01 (workers)",          _api1_async),
]

def _is_network_error(e: Exception) -> bool:
    e_str = repr(e).lower()
    network_terms = ["proxy", "timeout", "connection", "ssl", "reset", "disconnect", "eof", "aborted", "socket", "tunnel"]
    return any(term in e_str for term in network_terms)

def extract_terabox_sync(link: str) -> Optional[dict]:
    """
    Try each extraction API in priority order.
    Returns the first successful result, or None if all fail.
    Logs which API succeeded or why each failed.
    """
    errors = []
    def _is_hls(url: Optional[str]) -> bool:
        return bool(url and (url.endswith('.m3u8') or '.m3u8' in url))

    def _active_sync_apis():
        active = [entry for entry in _SYNC_APIS if entry[1] is not None and _api_failure_counts[entry[0]] < API_FAILURE_THRESHOLD]
        if not active:
            _api_failure_counts.clear()
            active = [entry for entry in _SYNC_APIS if entry[1] is not None]
        random.shuffle(active)
        log.info(f"[extract] Active API order: {', '.join(name for name, _ in active)}")
        return active

    def _record_failure(name: str) -> None:
        _api_failure_counts[name] += 1
        if _api_failure_counts[name] == API_FAILURE_THRESHOLD:
            log.warning(f"[extract] {name} blacklisted after {API_FAILURE_THRESHOLD} failures")

    def _try_api4_enrich(result: dict) -> dict:
        """If API returned HLS or no direct link, try API-4 (teraboxdl-frontend)
        to obtain a direct download link and enrich the result fields.
        """
        try:
            api4 = _api4_sync(link)
            if not api4:
                return result
            dl = api4.get('download')
            if dl and not _is_hls(dl):
                # Prefer API4's direct download and richer metadata when available
                for k in ('download', 'stream_360p', 'stream_480p', 'stream_720p', 'stream_1080p',
                          'filename', 'size', 'size_human', 'thumb', 'duration', 'duration_human'):
                    if api4.get(k):
                        result[k] = api4.get(k)
                result['_fallback_from'] = 'teraboxdl-frontend'
        except Exception:
            pass
        return result
    for name, fn in _active_sync_apis():
        log.info(f"[extract] Trying {name} for {link[:60]}")
        try:
            result = fn(link)
            if result and result.get("download"):
                # If the returned download is HLS (.m3u8) try to enrich via API-4
                if _is_hls(result.get('download')):
                    result = _try_api4_enrich(result)
                    if result.get('download') and not _is_hls(result.get('download')):
                        log.info(f"[extract] ✅ {name} succeeded (enriched by API-4)")
                        return result
                    # else continue to next API
                    errors.append(f"{name}: returned HLS and API-4 fallback failed")
                    continue
                log.info(f"[extract] ✅ {name} succeeded")
                return result
            _record_failure(name)
            errors.append(f"{name}: no download URL returned")
        except Exception as e:
            if not _is_network_error(e):
                _record_failure(name)
            errors.append(f"{name}: {e}")
            log.warning(f"[extract] {name} raised: {e}")
    log.error(f"[extract] All APIs failed: {'; '.join(errors)}")
    return None


async def extract_terabox_async(
    session: aiohttp.ClientSession, link: str
) -> Optional[dict]:
    """
    Async cascade — try each API in order, return first success.
    Falls back to a sync threadpool call for APIs without native async.
    """
    errors = []
    def _is_hls(url: Optional[str]) -> bool:
        return bool(url and (url.endswith('.m3u8') or '.m3u8' in url))

    async def _try_api4_enrich_async(result: dict) -> dict:
        try:
            api4 = await _api4_async(session, link)
            if not api4:
                return result
            dl = api4.get('download')
            if dl and not _is_hls(dl):
                for k in ('download', 'stream_360p', 'stream_480p', 'stream_720p', 'stream_1080p',
                          'filename', 'size', 'size_human', 'thumb', 'duration', 'duration_human'):
                    if api4.get(k):
                        result[k] = api4.get(k)
                result['_fallback_from'] = 'teraboxdl-frontend'
        except Exception:
            pass
        return result

    def _active_async_apis():
        active = [entry for entry in _ASYNC_APIS if entry[1] is not None and _api_failure_counts[entry[0]] < API_FAILURE_THRESHOLD]
        if not active:
            _api_failure_counts.clear()
            active = [entry for entry in _ASYNC_APIS if entry[1] is not None]
        random.shuffle(active)
        log.info(f"[extract-async] Active API order: {', '.join(name for name, _ in active)}")
        return active

    def _record_failure(name: str) -> None:
        _api_failure_counts[name] += 1
        if _api_failure_counts[name] == API_FAILURE_THRESHOLD:
            log.warning(f"[extract-async] {name} blacklisted after {API_FAILURE_THRESHOLD} failures")

    for name, fn in _active_async_apis():
        log.info(f"[extract-async] Trying {name}")
        try:
            result = await fn(session, link)
            if result and result.get("download"):
                if _is_hls(result.get('download')):
                    result = await _try_api4_enrich_async(result)
                    if result.get('download') and not _is_hls(result.get('download')):
                        log.info(f"[extract-async] ✅ {name} succeeded (enriched by API-4)")
                        return result
                    errors.append(f"{name}: returned HLS and API-4 fallback failed")
                    continue
                log.info(f"[extract-async] ✅ {name} succeeded")
                return result
            _record_failure(name)
            errors.append(f"{name}: no download URL")
        except Exception as e:
            if not _is_network_error(e):
                _record_failure(name)
            errors.append(f"{name}: {e}")
            log.warning(f"[extract-async] {name} raised: {e}")
    log.error(f"[extract-async] All APIs failed: {'; '.join(errors)}")
    return None


# ══════════════════════════════════════════════════════════════════════
# SECTION 6 — DOWNLOAD UTILITIES
# ══════════════════════════════════════════════════════════════════════

MB         = 1_048_576
CHUNK_SIZE = 512 * 1024
PROG_EVERY = 5 * MB


def _esc(text) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _progress_bar(done: int, total: int, width: int = 16) -> str:
    pct    = done / total if total else 0
    filled = int(width * pct)
    return "█" * filled + "░" * (width - filled) + f" {pct*100:.1f}%"

def _fmt_eta(seconds: float) -> str:
    """Compact duration: 45s / 3m 20s / 1h 04m."""
    try:
        s = int(max(0, seconds))
    except Exception:
        return "—"
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s//60}m {s%60:02d}s"
    return f"{s//3600}h {(s%3600)//60:02d}m"


def _fmt_speed(bytes_per_sec: float) -> str:
    if not bytes_per_sec or bytes_per_sec <= 0:
        return "—"
    return f"{human_size(int(bytes_per_sec))}/s"


def render_progress(title: str, filename: str, done: int, total: int,
                    elapsed: float) -> str:
    """The live transfer panel shown while a file moves.

    total may be 0 when the host sends no Content-Length, in which case the
    bar and ETA are omitted rather than shown as a wrong 0%.
    """
    speed = (done / elapsed) if elapsed > 0 else 0
    lines = [f"{title}\n", f"<code>{_esc(filename)}</code>\n"]
    if total > 0:
        pct = min(100.0, done * 100.0 / total)
        filled = int(16 * pct / 100)
        bar = "█" * filled + "░" * (16 - filled)
        eta = ((total - done) / speed) if speed > 0 else 0
        lines.append(f"<code>[{bar}] {pct:.1f}%</code>\n")
        lines.append(f"📦 {human_size(done)} / {human_size(total)}\n")
        lines.append(f"⚡ {_fmt_speed(speed)}  ·  ⏱ {_fmt_eta(elapsed)}"
                     f"  ·  ⏳ {_fmt_eta(eta)} left")
    else:
        lines.append(f"📦 {human_size(done)} transferred\n")
        lines.append(f"⚡ {_fmt_speed(speed)}  ·  ⏱ {_fmt_eta(elapsed)}")
    return "".join(lines)


class TransferProgress:
    """Throttled progress panel — edits one Telegram message as bytes move.

    Telegram rate-limits edits, so refresh no faster than every few seconds
    and skip an edit when the rendered text has not changed.
    """

    def __init__(self, chat_id: int, msg_id: Optional[int], title: str,
                 filename: str, total: int = 0, every: float = 4.0):
        self.chat_id = chat_id
        self.msg_id = msg_id
        self.title = title
        self.filename = filename
        self.total = total
        self.every = every
        self.started = time.time()
        self._last_edit = 0.0
        self._last_text = ""

    def elapsed(self) -> float:
        return time.time() - self.started

    def update(self, done: int, total: Optional[int] = None, force: bool = False) -> None:
        if total:
            self.total = total
        now = time.time()
        if not force and (now - self._last_edit) < self.every:
            return
        text = render_progress(self.title, self.filename, done, self.total, self.elapsed())
        if text == self._last_text:
            return
        self._last_edit = now
        self._last_text = text
        _bot_edit(self.chat_id, self.msg_id, text)

def _fetch_thumb(url: str) -> Optional[BytesIO]:
    if not url:
        return None
    try:
        r = requests.get(url,
            headers={"User-Agent": HEADERS["user-agent"], "Referer": "https://www.terabox.com/"},
            timeout=15)
        r.raise_for_status()
        buf = BytesIO(r.content)
        buf.name = "thumb.jpg"
        return buf
    except Exception:
        return None


def _stream_download(url, chat_id, status_msg_id, filename, total_size, bot_ref) -> Optional[BytesIO]:
    buf = BytesIO()
    downloaded = last_edit = 0
    try:
        headers = {"User-Agent": HEADERS["user-agent"], "Referer": "https://www.terabox.com/"}
        r = requests.get(url, headers=headers, stream=True, timeout=120)
        if r.status_code == 403:
            log.info("[stream download] Got 403 with Referer header. Retrying without Referer...")
            headers.pop("Referer", None)
            r = requests.get(url, headers=headers, stream=True, timeout=120)
        with r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if not chunk: continue
                buf.write(chunk)
                downloaded += len(chunk)
                if downloaded - last_edit >= PROG_EVERY:
                    last_edit = downloaded
                    bar = _progress_bar(downloaded, total_size)
                    try:
                        bot_ref.edit_message_text(
                            f"📥 <b>Downloading…</b>\n\n<code>{_esc(filename)}</code>\n\n"
                            f"{bar}\n<code>{downloaded/MB:.1f} / {total_size/MB:.1f} MB</code>",
                            chat_id, status_msg_id, parse_mode="HTML")
                    except Exception:
                        pass
        buf.seek(0)
        buf.name = filename
        return buf
    except Exception as e:
        log.warning(f"[stream download] {e}")
        return None


async def _async_download_to_disk(session, url, filename, total_size=0, dest_dir=DOWNLOAD_DIR) -> Optional[str]:
    dest_dir = dest_dir or tempfile.gettempdir()
    os.makedirs(dest_dir, exist_ok=True)
    fd, filepath = tempfile.mkstemp(prefix="tdl_", suffix="_" + _clean_name(filename, 50), dir=dest_dir)
    os.close(fd)
    try:
        headers = {"Referer": "https://www.terabox.com/", "User-Agent": HEADERS.get("user-agent", "")}
        resp = await session.get(url, headers=headers)
        if resp.status == 403:
            log.info("[async dl] Got 403 with Referer. Retrying without Referer...")
            headers.pop("Referer", None)
            resp = await session.get(url, headers=headers)
        async with resp:
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                if async_tqdm and total_size:
                    pbar = async_tqdm(total=total_size, unit="B", unit_scale=True,
                                      desc=filename[:40], leave=False)
                    async for chunk in resp.content.iter_chunked(MB):
                        f.write(chunk); pbar.update(len(chunk))
                    pbar.close()
                else:
                    async for chunk in resp.content.iter_chunked(MB):
                        f.write(chunk)
        return filepath
    except Exception as e:
        log.error(f"[async dl] {e}")
        if os.path.exists(filepath):
            os.remove(filepath)
        return None


class FileTooLargeError(Exception):
    """Raised when a capped download exceeds max_bytes mid-stream."""


def _download_to_tempfile_sync(url: str, filename: str, dest_dir: str = DOWNLOAD_DIR, timeout: int = 120,
                               max_bytes: int = 0,
                               referer: Optional[str] = "https://www.terabox.com/",
                               progress: "Optional[TransferProgress]" = None) -> Optional[str]:
    """Synchronously download `url` to a temp file and return the path, or None.

    max_bytes > 0 aborts with FileTooLargeError once that many bytes arrive,
    which is how a server that omits Content-Length is handled safely.
    Pass referer=None for hosts unrelated to Terabox.
    """
    dest_dir = dest_dir or tempfile.gettempdir()
    os.makedirs(dest_dir, exist_ok=True)
    fd, filepath = tempfile.mkstemp(prefix="tdl_sync_", suffix="_" + _clean_name(filename, 50), dir=dest_dir)
    os.close(fd)
    try:
        headers = {"User-Agent": HEADERS.get('user-agent', '')}
        if referer:
            headers["Referer"] = referer
        r = requests.get(url, stream=True, timeout=timeout, headers=headers)
        if r.status_code == 403 and referer:
            log.info("[sync dl_to_temp] Got 403 with Referer. Retrying without Referer...")
            headers.pop("Referer", None)
            r = requests.get(url, stream=True, timeout=timeout, headers=headers)
        with r:
            r.raise_for_status()
            written = 0
            if progress is not None:
                cl = r.headers.get("Content-Length")
                if cl and str(cl).isdigit():
                    progress.total = int(cl)
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        written += len(chunk)
                        if max_bytes and written > max_bytes:
                            raise FileTooLargeError(f"exceeds {max_bytes} bytes")
                        f.write(chunk)
                        if progress is not None:
                            progress.update(written)
        # Ensure file is non-empty
        if os.path.getsize(filepath) == 0:
            os.remove(filepath)
            return None
        return filepath
    except FileTooLargeError:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
        raise
    except Exception as e:
        log.warning(f"[sync dl_to_temp] {e}")
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
        return None


async def _download_thumb_async(session, url) -> Optional[bytes]:
    if not url: return None
    try:
        async with session.get(url, headers={"Referer": "https://www.terabox.com/"}) as r:
            if r.status == 200:
                return await r.read()
    except Exception:
        pass
    return None


def _clean_file(path: str) -> None:
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


def _clean_name(text, max_len=80) -> str:
    if not text: return "unknown"
    text = re.sub(r'[\\/*?:"<>|\n\r#@]', ' ', str(text))
    text = re.sub(r'\s+', '_', text.strip())
    return text[:max_len] or "unknown"


def _get_state_file(name: str) -> str:
    return os.path.join(STATE_DIR, f"{_clean_name(name, 50)}.json")


def _load_last_id(name: str) -> int:
    sf = _get_state_file(name)
    if os.path.exists(sf):
        try:
            with open(sf) as f:
                return json.load(f).get("last_id", 0)
        except Exception:
            pass
    return 0


def _save_last_id(name: str, msg_id: int) -> None:
    with open(_get_state_file(name), "w") as f:
        json.dump({"last_id": msg_id}, f)


def _get_record_file(src_title: str) -> str:
    return os.path.join(RECORD_DIR, f"{_clean_name(src_title, 50)}_forward.json")


def _load_forward_record(src_title: str) -> dict:
    rf = _get_record_file(src_title)
    if os.path.exists(rf):
        try:
            with open(rf) as f:
                return json.load(f)
        except Exception:
            pass
    return {"sent": 0}


def _save_forward_record(src_title: str, data: dict) -> None:
    with open(_get_record_file(src_title), "w") as f:
        json.dump(data, f)


def load_scraper_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_scraper_state(state: dict) -> None:
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    except Exception:
        pass
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


async def _flood_wait(seconds: int) -> None:
    log.warning(f"[FloodWait] Sleeping {seconds}s")
    await asyncio.sleep(seconds + 1)


# ══════════════════════════════════════════════════════════════════════
# SECTION 7 — JOB CONTROL  (pause / resume / stop)
# ══════════════════════════════════════════════════════════════════════

# _job_control[chat_id] = "pause" | "resume" | "stop"
_job_control: dict[int, str] = {}


def job_set(chat_id: int, cmd: str) -> None:
    _job_control[chat_id] = cmd


def job_get(chat_id: int) -> str:
    return _job_control.get(chat_id, "running")


def job_clear(chat_id: int) -> None:
    _job_control.pop(chat_id, None)


async def _check_job_control(chat_id: int, job_id: Optional[str] = None) -> str:
    """
    Poll job-control state. If paused, block here until resume/stop.
    Returns "stop" if stopped, otherwise "running".
    """
    was_paused = False
    while True:
        s = job_get(chat_id)
        if s == "stop":
            if job_id:
                try:
                    with get_db() as conn:
                        conn.execute("UPDATE dl_progress SET state='stop', updated_at=datetime('now') WHERE job_id=?", (job_id,))
                except Exception:
                    pass
            return "stop"
        if s in ("running", "resume"):
            if s == "resume":
                job_set(chat_id, "running")
            if was_paused and job_id:
                try:
                    with get_db() as conn:
                        conn.execute("UPDATE dl_progress SET state='running', updated_at=datetime('now') WHERE job_id=?", (job_id,))
                except Exception:
                    pass
            return "running"
        # paused — wait
        if not was_paused:
            was_paused = True
            if job_id:
                try:
                    with get_db() as conn:
                        conn.execute("UPDATE dl_progress SET state='pause', updated_at=datetime('now') WHERE job_id=?", (job_id,))
                except Exception:
                    pass
        await asyncio.sleep(2)


# ══════════════════════════════════════════════════════════════════════
# SECTION 8 — ACCOUNT ROTATOR  (Telethon)
# ══════════════════════════════════════════════════════════════════════

class AccountRotator:
    def __init__(self, clients: list):
        self.clients    = clients
        self.last_send  = [0.0] * len(clients)
        self.send_idx   = 0
        self.read_idx   = 0
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def get_read_client(self) -> TelegramClient:
        idx = self.read_idx % len(self.clients)
        self.read_idx += 1
        return self.clients[idx]

    async def get_send_client(self) -> TelegramClient:
        lock = self._get_lock()
        async with lock:
            idx = self.send_idx % len(self.clients)
            self.send_idx += 1
        now  = datetime.now(timezone.utc).timestamp()
        wait = COOLDOWN_SECONDS - (now - self.last_send[idx])
        if wait > 0:
            await asyncio.sleep(wait)
        self.last_send[idx] = datetime.now(timezone.utc).timestamp()
        return self.clients[idx]

    async def get_next_client(self) -> TelegramClient:
        return await self.get_send_client()


# ══════════════════════════════════════════════════════════════════════
# SECTION 9 — ENTITY RESOLUTION  (key fix from v4)
# ══════════════════════════════════════════════════════════════════════

async def resolve_entity(client: TelegramClient, identifier: str) -> Any:
    """
    Robustly resolve a channel/group identifier to a Telethon entity.

    Resolution order:
      1. @username / slug  → client.get_entity()
      2. Numeric ID        → GetChannelsRequest(access_hash=0)  [public channels]
      3. Numeric ID        → scan iter_dialogs()                [private channels]
      4. Numeric ID        → get_entity fallback candidates
    """
    from telethon.tl.types import InputChannel
    from telethon.tl.functions.channels import GetChannelsRequest

    identifier = str(identifier).strip()

    # ── 1. Non-numeric: @username or invite slug ─────────────────────────────
    if not identifier.lstrip("-").isdigit():
        slug = identifier.lstrip("@")
        try:
            return await client.get_entity(slug)
        except Exception as e:
            raise ValueError(f"Cannot resolve '{identifier}': {e}") from e

    # ── 2. Numeric ID — normalise to positive channel_id ─────────────────────
    num = int(identifier)
    s   = str(num)
    if s.startswith("-100"):
        channel_id = int(s[4:])          # -1002391576207 → 2391576207
    elif num < 0:
        channel_id = abs(num)
    else:
        channel_id = num

    # ── 2a. GetChannelsRequest with access_hash=0 (works for public channels) ─
    try:
        result = await client(GetChannelsRequest([InputChannel(channel_id, access_hash=0)]))
        chats = getattr(result, 'chats', None)
        if chats:
            return chats[0]
    except Exception:
        pass

    # ── 2b. Scan dialogs — finds private channels/groups the userbot is in ────
    # This fetches the entity WITH the real access_hash from the server.
    log.info(f"[resolve] Scanning dialogs to find id={channel_id} …")
    try:
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            eid = getattr(entity, "id", None)
            if eid == channel_id:
                log.info(f"[resolve] Found '{dialog.name}' via dialog scan")
                return entity
    except Exception as scan_err:
        log.warning(f"[resolve] Dialog scan failed: {scan_err}")

    # ── 2c. get_entity fallback with every ID form ────────────────────────────
    for cid in (num, -channel_id, channel_id):
        try:
            return await client.get_entity(cid)
        except Exception:
            pass

    raise ValueError(
        f"Cannot resolve '{identifier}': channel not found. "
        "Make sure the userbot account has joined or been added to this chat."
    )


_INVITE_RE = re.compile(r"(?:t\.me/|telegram\.me/)(?:joinchat/|\+)([A-Za-z0-9_-]+)")


def _joinable_slug(identifier: str) -> Optional[str]:
    """Public @username / t.me slug that JoinChannelRequest can take, else None.

    A bare numeric ID is never joinable: the account holds no access_hash for a
    chat it has not seen, so Telegram cannot resolve it.
    """
    ident = re.sub(r"^(?:https?://)?(?:t\.me/|telegram\.me/|@)", "",
                   (identifier or "").strip()).strip("/")
    if not ident or ident.lstrip("-").isdigit() or "/" in ident:
        return None
    return ident


async def _ensure_joined(client: TelegramClient, identifier: str) -> Any:
    """Resolve a chat, joining it first when the account is not a member yet.

    /forward and friends need the account to actually be in the chat. If it is
    not, and the user supplied an invite link or @username, join and resolve
    again — a numeric ID cannot be joined, so that error is passed through.
    """
    from telethon.tl.functions.channels import JoinChannelRequest
    from telethon.tl.functions.messages import ImportChatInviteRequest

    try:
        return await resolve_entity(client, identifier)
    except Exception as first_err:
        ident = str(identifier or "").strip()

        invite = _INVITE_RE.search(ident)
        if invite:
            try:
                log.info(f"[join] Not a member — importing invite {ident[:40]}…")
                res = await client(ImportChatInviteRequest(invite.group(1)))
                chats = getattr(res, "chats", None)
                if chats:
                    log.info(f"[join] Joined '{getattr(chats[0], 'title', '?')}'")
                    return chats[0]
            except Exception as e:
                if "already" in str(e).lower():
                    # Member after all — the first resolve just could not see it.
                    try:
                        return await resolve_entity(client, identifier)
                    except Exception:
                        pass
                raise ValueError(
                    f"Cannot join that invite link: {e}"
                ) from e
            raise first_err

        slug = _joinable_slug(ident)
        if slug:
            try:
                log.info(f"[join] Not a member — joining @{slug}…")
                await client(JoinChannelRequest(slug))
                return await resolve_entity(client, slug)
            except Exception as e:
                if "already" in str(e).lower():
                    return await resolve_entity(client, slug)
                raise ValueError(f"Cannot join @{slug}: {e}") from e

        # Numeric ID and not a member: nothing we can do automatically.
        raise ValueError(
            f"{first_err}\n\nThis account is not in that chat. Send the "
            f"<b>invite link</b> or <b>@username</b> instead of a numeric ID "
            f"and it will be joined automatically."
        )
# ══════════════════════════════════════════════════════════════════════
# SECTION 10 — BOT (pyTelegramBotAPI)
# ══════════════════════════════════════════════════════════════════════

bot: Optional[telebot.TeleBot] = None
_conv: dict[int, dict] = {}
_chat_cache: dict[int, list[dict]] = {}   # keyed by bot chat_id


def _bot_send(chat_id: int, text: str, parse_mode: str = "HTML") -> Optional[int]:
    """Fire-and-forget; returns message_id on success."""
    try:
        if bot:
            m = bot.send_message(chat_id, text, parse_mode=parse_mode)
            return m.message_id
    except Exception as e:
        log.error(f"[bot_send] {e}")
    return None


def _bot_edit(chat_id: int, msg_id: Optional[int], text: str) -> None:
    if not msg_id:
        return
    try:
        if bot:
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML")
    except Exception:
        pass


def _validate_bot_token(token: str, retries: int = 3) -> bool:
    """Validate bot token with retry logic and longer timeouts."""
    for attempt in range(1, retries + 1):
        try:
            log.info(f"[Bot] Validating token (attempt {attempt}/{retries})…")
            r = requests.get(
                f"https://api.telegram.org/bot{token}/getMe",
                timeout=30,  # Increased from 10 to 30 seconds
                headers={"Connection": "close"},
            )
            data = r.json()
            if data.get("ok"):
                log.info(f"[Bot] ✅ Token valid — @{data['result']['username']}")
                return True
            log.error(f"[Bot] Token invalid: {data.get('description')}")
            return False
        except requests.exceptions.Timeout:
            log.warning(f"[Bot] Timeout on attempt {attempt}/{retries}. Retrying in 5s…")
            if attempt < retries:
                time.sleep(5 * attempt)  # Exponential backoff
            continue
        except requests.exceptions.ConnectionError as e:
            log.warning(f"[Bot] Connection error: {e}")
            if attempt < retries:
                log.info(f"[Bot] Retrying in {5*attempt}s…")
                time.sleep(5 * attempt)
            continue
        except Exception as e:
            log.error(f"[Bot] Token check failed: {e}")
            return False
    log.error("[Bot] Failed to validate token after all retries. Check your internet connection.")
    return False


def _make_bot() -> telebot.TeleBot:
    return telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=MAX_BOT_THREADS)


# ── Result card builders ──────────────────────────────────────────────

# ── File Type & Category Detection ───────────────────────────────────

def _detect_file_category(filename: str) -> tuple[str, str]:
    """
    Returns (category_name, human_label)
    Categories: 'video', 'audio', 'photo', 'archive', 'app', 'document', 'file'
    """
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in (".mp4", ".mkv", ".mov", ".webm", ".avi", ".flv", ".m4v", ".3gp", ".wmv", ".ts"):
        return "video", f"🎬 Video ({ext.upper().lstrip('.')})"
    elif ext in (".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"):
        return "archive", f"🗜 Compressed Archive ({ext.upper().lstrip('.')})"
    elif ext in (".mp3", ".m4a", ".flac", ".wav", ".ogg", ".aac", ".opus", ".wma"):
        return "audio", f"🎵 Audio Track ({ext.upper().lstrip('.')})"
    elif ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"):
        return "photo", f"🖼 Image ({ext.upper().lstrip('.')})"
    elif ext in (".apk", ".exe", ".msi", ".dmg", ".pkg", ".deb"):
        return "app", f"📦 Application ({ext.upper().lstrip('.')})"
    elif ext in (".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".epub"):
        return "document", f"📄 Document ({ext.upper().lstrip('.')})"
    else:
        return "file", f"📁 File ({ext.upper().lstrip('.') if ext else 'BIN'})"


def _send_file_by_type(bot_ref, chat_id: int, file_path: str, filename: str, caption: str, markup=None, timeout: int = 1800, thumb_buf=None, duration: int = 0, width: int = 0, height: int = 0) -> bool:
    """
    Smart type router: sends video as video, audio as audio, photo as photo,
    and archives (ZIP, RAR, 7Z), APKs, PDFs, Docs as documents with exact filename preserved.
    Includes automatic fallback to document if media player encoding fails.
    """
    category, _ = _detect_file_category(filename or file_path)
    file_sz = os.path.getsize(file_path) if os.path.exists(file_path) else 0

    # 1. Video files
    if category == "video":
        try:
            with open(file_path, "rb") as f:
                bot_ref.send_video(
                    chat_id, video=f, caption=caption, parse_mode="HTML",
                    reply_markup=markup, duration=duration or None,
                    width=width or None, height=height or None,
                    supports_streaming=True, timeout=timeout, thumb=thumb_buf
                )
            return True
        except Exception as e:
            log.warning(f"[send_file_by_type] Video upload error: {e}, falling back to Document")
            try:
                with open(file_path, "rb") as f:
                    bot_ref.send_document(
                        chat_id, document=f, caption=caption, parse_mode="HTML",
                        reply_markup=markup, timeout=timeout, thumb=thumb_buf
                    )
                return True
            except Exception as e2:
                log.error(f"[send_file_by_type] Document fallback failed: {e2}")
                return False

    # 2. Audio files
    elif category == "audio":
        try:
            with open(file_path, "rb") as f:
                bot_ref.send_audio(
                    chat_id, audio=f, caption=caption, parse_mode="HTML",
                    reply_markup=markup, duration=duration or None,
                    timeout=timeout, thumb=thumb_buf
                )
            return True
        except Exception as e:
            log.warning(f"[send_file_by_type] Audio upload error: {e}, falling back to Document")
            try:
                with open(file_path, "rb") as f:
                    bot_ref.send_document(
                        chat_id, document=f, caption=caption, parse_mode="HTML",
                        reply_markup=markup, timeout=timeout, thumb=thumb_buf
                    )
                return True
            except Exception as e2:
                log.error(f"[send_file_by_type] Document fallback failed: {e2}")
                return False

    # 3. Photo files
    elif category == "photo" and file_sz < 10 * 1024 * 1024:
        try:
            with open(file_path, "rb") as f:
                bot_ref.send_photo(
                    chat_id, photo=f, caption=caption, parse_mode="HTML",
                    reply_markup=markup, timeout=timeout
                )
            return True
        except Exception as e:
            log.warning(f"[send_file_by_type] Photo upload error: {e}, falling back to Document")
            try:
                with open(file_path, "rb") as f:
                    bot_ref.send_document(
                        chat_id, document=f, caption=caption, parse_mode="HTML",
                        reply_markup=markup, timeout=timeout
                    )
                return True
            except Exception as e2:
                log.error(f"[send_file_by_type] Document fallback failed: {e2}")
                return False

    # 4. Zip / Rar / 7z / PDF / APK / Binary Documents
    else:
        try:
            with open(file_path, "rb") as f:
                bot_ref.send_document(
                    chat_id, document=f, caption=caption, parse_mode="HTML",
                    reply_markup=markup, timeout=timeout, thumb=thumb_buf
                )
            return True
        except Exception as e:
            log.error(f"[send_file_by_type] Document upload error: {e}")
            return False


# ── Result card builders ──────────────────────────────────────────────

def build_result_message(result: dict) -> str:
    filename = result.get("filename") or result.get("title") or "Unknown"
    category, type_label = _detect_file_category(filename)
    res = (f"{result['width']}x{result['height']}"
           if result.get("width") and result.get("height") else "N/A")

    # Build link lines
    link_lines = []
    dl = result.get("download")
    if dl:
        link_lines.append(f'⬇️ <b>Download:</b> <a href="{dl}">Click here</a>')
    for label, key in [
        ("▶️ 360p",  "stream_360p"),
        ("▶️ 480p",  "stream_480p"),
        ("▶️ 720p",  "stream_720p"),
        ("▶️ 1080p", "stream_1080p"),
    ]:
        url = result.get(key)
        if url and url != dl:          # skip if same as download link
            link_lines.append(f'{label}: <a href="{url}">Stream</a>')

    links_block = ("\n\n" + "\n".join(link_lines)) if link_lines else ""

    if result.get("is_mega"):
        if result.get("is_folder"):
            return (
                f"🔴 <b>Mega Folder Extraction Complete!</b>\n\n"
                f"📁 <b>Folder:</b> <code>{_esc(filename)}</code>\n"
                f"📄 <b>Files:</b> <code>{len(result.get('folder_files', []))} items</code>\n"
                f"📦 <b>Total Size:</b> <code>{_esc(result.get('size_human', 'N/A'))}</code>\n"
                f"⚡ <b>Engine:</b> <code>Mega Cloud Engine v2.0</code>\n"
                f"{links_block}"
            )
        return (
            f"🔴 <b>Mega Drive Extraction Complete!</b>\n\n"
            f"📂 <b>File:</b> <code>{_esc(filename)}</code>\n"
            f"🏷 <b>Type:</b> <code>{type_label}</code>\n"
            f"📦 <b>Size:</b> <code>{_esc(result.get('size_human', 'N/A'))}</code>\n"
            f"⚡ <b>Engine:</b> <code>Mega Cloud Direct Engine (No-Limit Bypass)</code>\n"
            f"{links_block}"
        )

    duration_str = _esc(result.get("duration_human") or human_duration(result.get("duration")))
    duration_line = f"⏱ <b>Duration:</b> <code>{duration_str}</code>\n" if result.get("duration") else ""
    res_line = f"📺 <b>Resolution:</b> <code>{res}</code>" if result.get("width") and result.get("height") else ""

    return (
        f"✅ <b>Extraction Complete!</b>\n\n"
        f"🎬 <b>Title:</b> <code>{_esc(result.get('title') or filename)}</code>\n"
        f"📂 <b>File:</b> <code>{_esc(filename)}</code>\n"
        f"🏷 <b>Type:</b> <code>{type_label}</code>\n"
        f"📦 <b>Size:</b> <code>{_esc(result.get('size_human', 'N/A'))}</code>\n"
        f"{duration_line}"
        f"{res_line}"
        f"{links_block}"
    )


def build_result_keyboard(result: dict) -> InlineKeyboardMarkup:
    markup  = InlineKeyboardMarkup(row_width=2)
    buttons = []
    if result.get("download"):
        buttons.append(InlineKeyboardButton("⬇️ Download", url=result["download"]))
    for label, key in [
        ("▶️ 360p",  "stream_360p"), ("▶️ 480p",  "stream_480p"),
        ("▶️ 720p",  "stream_720p"), ("▶️ 1080p", "stream_1080p"),
    ]:
        if result.get(key):
            buttons.append(InlineKeyboardButton(label, url=result[key]))
    markup.add(*buttons)
    return markup


def _duration_seconds(val) -> int:
    """Safely convert a duration value (int seconds or HH:MM:SS/MM:SS string) to int."""
    if not val:
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str) and ":" in val:
        parts = val.strip().split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            return 0
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def send_mega_result(chat_id: int, result: dict, status_msg_id: Optional[int] = None) -> None:
    global bot
    bot_ref = bot
    text = build_result_message(result)
    markup = build_result_keyboard(result)
    is_folder = result.get("is_folder", False)

    if not bot_ref:
        return

    # ── Folder extraction flow ──
    if is_folder:
        files = result.get("folder_files", [])
        folder_id = result.get("folder_id")
        key_str = result.get("key_str")
        if not files:
            bot_ref.send_message(chat_id, text + "\n\n⚠️ <i>No downloadable files found in this folder.</i>", parse_mode="HTML")
            return

        bot_ref.send_message(
            chat_id,
            f"📂 <b>Folder Extraction:</b> <code>{_esc(result.get('filename'))}</code>\n"
            f"📄 Total Files: <code>{len(files)}</code> | 📦 Size: <code>{_esc(result.get('size_human'))}</code>\n\n"
            f"⏳ <i>Downloading & sending files directly to chat…</i>",
            parse_mode="HTML"
        )

        for i, node in enumerate(files, 1):
            file_size = node.get("size", 0)
            file_name = node.get("name", f"file_{i}")
            if file_size > AUTO_SEND_LIMIT:
                bot_ref.send_message(
                    chat_id,
                    f"[{i}/{len(files)}] ⚠️ <b>{_esc(file_name)}</b> ({human_size(file_size)}) is > 500MB (auto-send skipped).",
                    parse_mode="HTML"
                )
                continue

            temp_dir = tempfile.mkdtemp(prefix="mega_fld_")
            try:
                node_key = node.get("key")
                aes_key, iv = _derive_mega_key_iv(_mega_base64url_encode(node_key))
                dl_info = _get_mega_folder_file_url(node["id"], folder_id)
                download_url = dl_info.get("g")
                if not download_url:
                    continue

                filepath = os.path.join(temp_dir, file_name)
                _download_and_decrypt_mega(download_url, aes_key, iv, filepath, file_size)

                _, item_type_label = _detect_file_category(file_name)
                caption = f"📂 <b>{_esc(file_name)}</b>\n🏷 <code>{item_type_label}</code> | 📦 <code>{human_size(file_size)}</code>\n[{i}/{len(files)}]"

                _send_file_by_type(bot_ref, chat_id, filepath, file_name, caption, markup=None, timeout=1800)
                time.sleep(1)
            except Exception as e:
                log.error(f"[mega folder send file {i}] {e}")
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        if status_msg_id:
            try: bot_ref.delete_message(chat_id, status_msg_id)
            except Exception: pass
        return

    # ── Single file extraction flow ──
    size = result.get("size_bytes", 0)
    filename = result.get("filename", "mega_file.bin")
    aes_key = result.get("aes_key")
    iv = result.get("iv")
    download_url = result.get("download")

    if size and 0 < size <= AUTO_SEND_LIMIT and aes_key and iv and download_url:
        temp_dir = tempfile.mkdtemp(prefix="mega_dl_")
        try:
            if status_msg_id:
                try:
                    bot_ref.edit_message_text(
                        f"📥 <b>Downloading Mega File (No-Limit Direct Stream)…</b>\n\n"
                        f"📂 <code>{_esc(filename)}</code>\n"
                        f"📦 Size: <code>{_esc(result.get('size_human', 'N/A'))}</code>\n\n"
                        f"⏳ Decrypting payload into local stream…",
                        chat_id, status_msg_id, parse_mode="HTML"
                    )
                except Exception:
                    pass

            file_path = os.path.join(temp_dir, filename)
            _download_and_decrypt_mega(download_url, aes_key, iv, file_path, size)

            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                if status_msg_id:
                    try:
                        bot_ref.edit_message_text(
                            f"📤 <b>Uploading to Telegram…</b>\n\n"
                            f"📂 <code>{_esc(filename)}</code> ({human_size(file_size)})",
                            chat_id, status_msg_id, parse_mode="HTML"
                        )
                    except Exception:
                        pass

                _send_file_by_type(bot_ref, chat_id, file_path, filename, text, markup=markup, timeout=1800)

                if status_msg_id:
                    try:
                        bot_ref.delete_message(chat_id, status_msg_id)
                    except Exception:
                        pass
                return
        except Exception as e:
            log.error(f"[mega send single file] {e}")
            if status_msg_id:
                try:
                    bot_ref.edit_message_text(
                        f"⚠️ <b>Direct Upload Error:</b> <code>{_esc(str(e))}</code>\n\n"
                        f"Mega link preserved below:",
                        chat_id, status_msg_id, parse_mode="HTML"
                    )
                except Exception:
                    pass
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # For files > 500MB or fallback:
    bot_ref.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)



def send_result(chat_id: int, result: dict, status_msg_id: Optional[int] = None) -> None:
    global bot
    text      = build_result_message(result)
    markup    = build_result_keyboard(result)
    size      = _parse_size_bytes(result.get("size") or result.get("size_human"))
    filename  = result.get("filename", "video.mp4")
    download  = result.get("download")
    duration  = _duration_seconds(result.get("duration"))
    width     = int(result.get("width") or 0)
    height    = int(result.get("height") or 0)
    thumb_buf = _fetch_thumb(result.get("thumb") or "")
    bot_ref   = bot

    # If size is unknown (0) but a download URL exists, try a HEAD request
    # to obtain Content-Length so we can safely decide auto-send.
    if size == 0 and download:
        try:
            with _make_resilient_session(retries=2).head(download, headers={"Referer": "https://www.terabox.com/", "User-Agent": HEADERS.get('user-agent', '')}, allow_redirects=True, timeout=15) as head_r:
                cl = head_r.headers.get("Content-Length")
                if cl and cl.isdigit():
                    size = int(cl)
        except Exception:
            # If HEAD fails, fall back to existing metadata (size remains 0)
            pass

    def _should_send_video() -> bool:
        ext = os.path.splitext(filename or "")[1].lower()
        return ext in (".mp4", ".mkv", ".mov", ".webm", ".avi", ".flv", ".m4v")

    def _send_timeout_for_size(sz: int) -> int:
        try:
            if not sz or sz <= 0:
                return SEND_TIMEOUT_BASE
            # Use one base unit per 500MB, cap at 1 hour
            blocks = max(1, int(sz / (50 * 1024 * 1024)))
            return min(3600, SEND_TIMEOUT_BASE * blocks)
        except Exception:
            return SEND_TIMEOUT_BASE

    if size and 0 < size <= AUTO_SEND_LIMIT and download:
        if bot_ref and status_msg_id:
            try:
                bot_ref.edit_message_text(
                    f"📥 <b>Downloading…</b>\n\n<code>{_esc(filename)}</code>\n\n"
                    f"{_progress_bar(0, size)}\n<code>0.0 / {size/MB:.1f} MB</code>",
                    chat_id, status_msg_id, parse_mode="HTML")
            except Exception:
                pass
        video_buf = _stream_download(download, chat_id, status_msg_id, filename, size, bot)
        # Guard: ensure buffer is non-empty; otherwise fallback to disk download
        buf_ok = False
        if video_buf:
            try:
                buf_ok = (hasattr(video_buf, 'getbuffer') and video_buf.getbuffer().nbytes > 0) or (hasattr(video_buf, 'tell') and video_buf.tell() > 0)
            except Exception:
                buf_ok = True

        if (video_buf and buf_ok) and bot_ref is not None:
            if status_msg_id:
                try: bot_ref.delete_message(chat_id, status_msg_id)
                except Exception: pass

            def _clone_buf(buf):
                try:
                    return BytesIO(buf.getvalue())
                except Exception:
                    try:
                        buf.seek(0)
                    except Exception:
                        pass
                    return buf

            def _try_send(send_fn, buf, desc):
                for attempt in range(1, 4):
                    try:
                        if attempt > 1:
                            time.sleep(attempt - 1)
                        try:
                            buf.seek(0)
                        except Exception:
                            pass
                        send_fn(buf)
                        return True
                    except Exception as exc:
                        log.warning(f"[bot] {desc} attempt {attempt} failed: {exc}")
                        if attempt == 3:
                            break
                        try:
                            buf = _clone_buf(buf)
                        except Exception:
                            pass
                return False

            def _send_video_buf(buf):
                return bot_ref.send_video(
                    chat_id, video=buf, caption=text,
                    parse_mode="HTML", duration=duration or None,
                    width=width or None, height=height or None,
                    thumb=thumb_buf, reply_markup=markup,
                    supports_streaming=False, timeout=_send_timeout_for_size(size)
                )

            def _send_document_buf(buf):
                return bot_ref.send_document(
                    chat_id, document=buf, caption=text,
                    parse_mode="HTML", thumb=thumb_buf,
                    reply_markup=markup, timeout=_send_timeout_for_size(size)
                )

            send_video_first = _should_send_video()
            if send_video_first:
                cloned_buf = _clone_buf(video_buf)
                if _try_send(_send_video_buf, cloned_buf, "Video send"):
                    return
                cloned_buf = _clone_buf(video_buf)
                if _try_send(_send_document_buf, cloned_buf, "Document send"):
                    return
            else:
                cloned_buf = _clone_buf(video_buf)
                if _try_send(_send_document_buf, cloned_buf, "Document send"):
                    return
                cloned_buf = _clone_buf(video_buf)
                if _try_send(_send_video_buf, cloned_buf, "Video send"):
                    return

            thumb_buf = _fetch_thumb(result.get("thumb") or "")
        else:
            # Attempt robust sync download to temp file and send from disk
            try:
                fp = _download_to_tempfile_sync(download, filename)
                if fp:
                    if bot_ref and status_msg_id:
                        try: bot_ref.delete_message(chat_id, status_msg_id)
                        except Exception: pass
                    try:
                        with open(fp, 'rb') as f:
                            if bot_ref:
                                if _should_send_video():
                                    try:
                                        bot_ref.send_video(chat_id, video=f, caption=text,
                                                           parse_mode="HTML", duration=duration or None,
                                                           width=width or None, height=height or None,
                                                           thumb=thumb_buf, reply_markup=markup,
                                                           supports_streaming=False, timeout=_send_timeout_for_size(size))
                                        return
                                    except Exception as e:
                                        log.warning(f"[bot] Video send from disk failed: {e}")
                                        try:
                                            f.seek(0)
                                        except Exception:
                                            pass
                                bot_ref.send_document(chat_id, document=f, caption=text,
                                                      parse_mode="HTML", thumb=thumb_buf,
                                                      reply_markup=markup, timeout=_send_timeout_for_size(size))
                                return
                    except Exception as e:
                        log.warning(f"[bot] Disk send failed: {e}")
                    finally:
                        try: os.remove(fp)
                        except Exception: pass
            except Exception as e:
                log.warning(f"[bot] Fallback disk download/send failed: {e}")

    size_mb    = size / MB if size else 0
    large_note = ""
    if size > AUTO_SEND_LIMIT:
        large_note = (
            f"\n\n📦 <b>File Size:</b> <code>{size_mb:.1f} MB</code>\n"
            f"⚠️ Too large for auto-send (limit: {AUTO_SEND_LIMIT/MB:.0f}MB)\n"
            f"📥 Tap the download button below to get the file."
        )
    elif size > 0:
        large_note = f"\n\n✅ <b>File will be sent directly:</b> <code>{size_mb:.1f} MB</code>"

    final_text = text + large_note

    if bot_ref and status_msg_id:
        try: bot_ref.delete_message(chat_id, status_msg_id)
        except Exception: pass

    if thumb_buf and bot_ref:
        try:
            bot_ref.send_photo(chat_id, photo=thumb_buf, caption=final_text,
                           parse_mode="HTML", reply_markup=markup)
            return
        except Exception as e:
            log.warning(f"[bot] Photo send failed: {e}")

    if bot_ref:
        bot_ref.send_message(chat_id, final_text, parse_mode="HTML", reply_markup=markup)


# ── Inline keyboards ──────────────────────────────────────────────────

def _media_type_kb(prefix: str) -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("🖼 Photos",          callback_data=f"{prefix}_photos"),
        InlineKeyboardButton("🎬 Videos",          callback_data=f"{prefix}_videos"),
        InlineKeyboardButton("🎵 Audio",           callback_data=f"{prefix}_audio"),
        InlineKeyboardButton("📄 Documents",       callback_data=f"{prefix}_docs"),
        InlineKeyboardButton("📸 Photos + Videos", callback_data=f"{prefix}_pv"),
        InlineKeyboardButton("📦 ALL",             callback_data=f"{prefix}_all"),
    )
    return m


def _caption_kb() -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=3)
    m.add(
        InlineKeyboardButton("Keep",   callback_data="cap_keep"),
        InlineKeyboardButton("Clear",  callback_data="cap_clear"),
        InlineKeyboardButton("Prefix", callback_data="cap_prefix"),
    )
    return m


def _parse_media_choice(data: str) -> tuple[bool, bool, bool, bool]:
    photos = data in ("mt_photos", "mt_pv", "mt_all", "ft_photos", "ft_pv", "ft_all")
    videos = data in ("mt_videos", "mt_pv", "mt_all", "ft_videos", "ft_pv", "ft_all")
    audio  = data in ("mt_audio",  "mt_all", "ft_audio",  "ft_all")
    docs   = data in ("mt_docs",   "mt_all", "ft_docs",   "ft_all")
    return photos, videos, audio, docs


def _pending_approval_kb(user_id: int) -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("❌ Reject",  callback_data=f"reject_{user_id}"),
    )
    return m


# ─── Mini-Window Dashboard & UI Helpers ──────────────────────────────

def _ui_progress_bar(downloaded: int, total: int, length: int = 10) -> str:
    if total <= 0:
        return "░" * length
    percent = min(1.0, max(0.0, downloaded / total))
    filled = int(round(length * percent))
    return "█" * filled + "░" * (length - filled)

def _ui_dashboard_text(uid: int, first_name: str = "") -> str:
    row = get_user_stats(uid)
    total_links = row["total_links"] if row else 0
    is_prem = is_premium(uid)
    prem_info = get_premium_info(uid) if is_prem else None

    if _is_l1_auth(uid):
        badge = "👑 <b>Super-Admin Root</b>"
    elif _is_lx_auth(uid):
        badge = "🔹 <b>Co-Admin</b>"
    elif is_prem:
        exp = prem_info['expires_at'][:10] if prem_info else 'Active'
        badge = f"💎 <b>VIP Premium</b> (Exp: <code>{exp}</code>)"
    else:
        badge = "⚡ <b>Free Tier</b>"

    creds = _get_user_credentials(uid)
    userbot_status = "🟢 <b>Online & Ready</b>" if creds else "⚪ <b>Not Logged In</b>"

    return (
        f"🌌 <b>CRYPTER & TERABOX DASHBOARD v5.0</b>\n"
        f"────────────────────────────────────────\n"
        f"👤 <b>User:</b> {_esc(first_name or 'Member')} (<code>{uid}</code>)\n"
        f"🎖️ <b>Tier:</b> {badge}\n"
        f"🤖 <b>Userbot Session:</b> {userbot_status}\n"
        f"📊 <b>Total Extractions:</b> <code>{total_links}</code>\n"
        f"⚡ <b>Engine Health:</b> <code>30/30 Endpoints Optimal</code>\n"
        f"────────────────────────────────────────\n"
        f"👇 <i>Use the interactive mini-window controls below:</i>"
    )

def _ui_dashboard_kb(uid: int) -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("🚀 Extract Link", callback_data="ui_extract_hint"),
        InlineKeyboardButton("⚡ Userbot Hub",  callback_data="ui_menu_tools"),
    )
    m.add(
        InlineKeyboardButton("💎 Premium VIP",  callback_data="ui_menu_premium"),
        InlineKeyboardButton("📊 My Account",   callback_data="ui_menu_stats"),
    )
    m.add(
        InlineKeyboardButton("📡 Channels",      callback_data="ui_menu_channels"),
        InlineKeyboardButton("🕹️ Job Monitor",  callback_data="ui_menu_status"),
    )
    m.add(
        InlineKeyboardButton("📖 Help Guide",   callback_data="ui_menu_help"),
    )
    if _is_lx_auth(uid):
        m.add(
            InlineKeyboardButton("🎛️ Admin Panel", callback_data="ui_menu_admin"),
            InlineKeyboardButton("🗄️ Session Vault", callback_data="ui_menu_vault"),
        )
    return m

def _ui_tools_kb(uid: int) -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("🔁 Forwarder",   callback_data="ui_act_forward"),
        InlineKeyboardButton("📥 Downloader",  callback_data="ui_act_download"),
    )
    m.add(
        InlineKeyboardButton("🕷️ Link Scraper", callback_data="ui_act_scraper"),
        InlineKeyboardButton("💾 GDrive Leech", callback_data="ui_act_gdrive"),
    )
    m.add(
        InlineKeyboardButton("🐙 GitHub Leech", callback_data="ui_act_github"),
        InlineKeyboardButton("🔑 Login Account", callback_data="ui_act_login"),
    )
    m.add(
        InlineKeyboardButton("🚪 Logout Session", callback_data="ui_act_logout"),
        InlineKeyboardButton("🏠 Main Dashboard", callback_data="ui_menu_main"),
    )
    return m

def _ui_premium_kb(uid: int) -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("💎 1 Day — ₹29",   callback_data="ui_plan_1day"),
        InlineKeyboardButton("💎 7 Days — ₹99",  callback_data="ui_plan_7day"),
    )
    m.add(
        InlineKeyboardButton("💎 15 Days — ₹179", callback_data="ui_plan_15day"),
        InlineKeyboardButton("💎 30 Days — ₹299", callback_data="ui_plan_30day"),
    )
    m.add(
        InlineKeyboardButton("🎟️ Redeem Code", callback_data="ui_act_redeem"),
        InlineKeyboardButton("💳 UPI / QR Info", callback_data="ui_act_qr"),
    )
    m.add(
        InlineKeyboardButton("🏠 Main Dashboard", callback_data="ui_menu_main"),
    )
    return m

def _ui_status_kb(chat_id: int) -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=3)
    m.add(
        InlineKeyboardButton("⏸ Pause",   callback_data="ui_ctrl_pause"),
        InlineKeyboardButton("▶️ Resume",  callback_data="ui_ctrl_resume"),
        InlineKeyboardButton("⏹ Stop",    callback_data="ui_ctrl_stop"),
    )
    m.add(
        InlineKeyboardButton("🔄 Live Refresh", callback_data="ui_ctrl_refresh"),
        InlineKeyboardButton("🏠 Main Menu",    callback_data="ui_menu_main"),
    )
    return m

def _ui_admin_kb(uid: int) -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("👥 Pending Users", callback_data="ui_adm_pending"),
        InlineKeyboardButton("📊 System Stats",  callback_data="ui_adm_stats"),
    )
    m.add(
        InlineKeyboardButton("🗄️ Session Vault", callback_data="ui_menu_vault"),
        InlineKeyboardButton("💎 Gen License",   callback_data="ui_adm_gencode"),
    )
    m.add(
        InlineKeyboardButton("🔓 DB Unlock",      callback_data="ui_adm_unlock"),
        InlineKeyboardButton("🏠 Main Dashboard", callback_data="ui_menu_main"),
    )
    return m

def _render_status_view(chat_id: int) -> tuple[str, InlineKeyboardMarkup]:
    job = dl_job_latest(chat_id)
    if not job:
        return (
            "📊 <b>Live Job Monitor Mini-Window</b>\n\n"
            "ℹ️ No active or recent userbot jobs running in this chat.\n"
            "Launch a task via <code>/scraper</code>, <code>/forward</code>, or <code>/download</code>.",
            _ui_status_kb(chat_id)
        )
    ctrl = job_get(chat_id)
    state_icon = {"running": "▶️ RUNNING", "pause": "⏸ PAUSED", "stop": "⏹ STOPPED"}.get(ctrl, "▶️ RUNNING")
    downloaded = job["downloaded"] or 0
    wanted = job["total_wanted"] or 0
    bar = _ui_progress_bar(downloaded, wanted)
    pct = f"{(downloaded / wanted * 100):.1f}%" if wanted > 0 else "N/A"

    text = (
        f"📊 <b>Live Job Monitor Mini-Window</b>\n"
        f"────────────────────────────────────────\n"
        f"🆔 <b>Job ID:</b> <code>{job['job_id']}</code>\n"
        f"📡 <b>Source:</b> <code>{_esc(job['src_label'])}</code>\n"
        f"🎯 <b>Progress:</b> <code>{downloaded}</code> / <code>{wanted or 'ALL'}</code> (<b>{pct}</b>)\n"
        f"<code>[{bar}]</code>\n\n"
        f"✅ <b>Processed:</b> <code>{downloaded}</code>  |  ❌ <b>Failed:</b> <code>{job['failed']}</code>\n"
        f"📄 <b>Last Item:</b> <code>{_esc(job['last_filename'] or 'N/A')}</code>\n"
        f"🕹 <b>State:</b> <b>{state_icon}</b>\n"
        f"🕐 <b>Last Sync:</b> <code>{job['updated_at'][:19] if job['updated_at'] else 'Now'}</code>\n"
        f"────────────────────────────────────────"
    )
    return text, _ui_status_kb(chat_id)


# ══════════════════════════════════════════════════════════════════════
# SECTION 11 — REGISTER HANDLERS
# ══════════════════════════════════════════════════════════════════════

def register_handlers(b: telebot.TeleBot) -> None:

    def _normalize_channel_input(text: str) -> str:
        """Convert t.me links and @usernames to bare slugs for resolve_entity.

        Invite links are returned untouched: stripping them would drop the hash
        (t.me/joinchat/<hash> used to come back as just "joinchat"), and that
        hash is the only thing that can join a private chat.
        """
        text = (text or "").strip()
        if _INVITE_RE.search(text):
            return text
        m = re.match(r"https?://t\.me/([^\s/?]+)", text)
        if m:
            return m.group(1)
        return text.lstrip("@") if text.startswith("@") else text


    # ─── /start & /menu — Interactive Mini-Window Dashboard ─────────
    @b.message_handler(commands=["start", "menu", "dashboard", "home", "ui", "app"])
    def cmd_start(message):
        uid  = message.from_user.id
        user = message.from_user
        upsert_user(uid, user.username or "", user.first_name or "")

        if _is_l1_auth(uid):
            _set_l1_node(uid)
            approve_user(uid)
            b.send_message(
                message.chat.id,
                _ui_dashboard_text(uid, user.first_name or "Super-Admin"),
                parse_mode="HTML",
                reply_markup=_ui_dashboard_kb(uid)
            )
            return

        if _is_lx_auth(uid):
            approve_user(uid)
            b.send_message(
                message.chat.id,
                _ui_dashboard_text(uid, user.first_name or "Admin"),
                parse_mode="HTML",
                reply_markup=_ui_dashboard_kb(uid)
            )
            return

        if is_approved(uid):
            b.send_message(
                message.chat.id,
                _ui_dashboard_text(uid, user.first_name or "Member"),
                parse_mode="HTML",
                reply_markup=_ui_dashboard_kb(uid)
            )
            return

        # Check if already pending
        pending = get_pending_users()
        if any(p["user_id"] == uid for p in pending):
            b.send_message(message.chat.id, "⏳ Your approval request is still pending. Please wait.")
            return

        # New user — add to pending and notify admins
        add_pending(uid, user.username or "", user.first_name or "")
        b.send_message(message.chat.id,
                       "🔔 <b>Access request sent!</b>\n"
                       "An admin will review your request shortly. Please wait.",
                       parse_mode="HTML")

        uname  = f"@{_esc(user.username)}" if user.username else _esc(user.first_name or "Unknown")
        notify = (
            f"🆕 <b>New access request</b>\n\n"
            f"👤 Name: {uname}\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        for admin_id in _get_l1_nodes():
            try:
                b.send_message(admin_id, notify, parse_mode="HTML",
                               reply_markup=_pending_approval_kb(uid))
            except Exception:
                pass

    # ─── Interactive UI Navigation Callback Router ─────────────────
    @b.callback_query_handler(func=lambda c: c.data.startswith("ui_"))
    def cb_ui_navigation(call):
        uid = call.from_user.id
        chat_id = call.message.chat.id
        mid = call.message.message_id
        action = call.data
        call.message.from_user = call.from_user

        if action == "ui_extract_hint":
            return b.answer_callback_query(
                call.id,
                "🚀 Just send any Terabox / 1024terabox link directly in this chat!",
                show_alert=True
            )

        if action == "ui_menu_main":
            b.answer_callback_query(call.id)
            try:
                b.edit_message_text(
                    _ui_dashboard_text(uid, call.from_user.first_name),
                    chat_id, mid,
                    parse_mode="HTML",
                    reply_markup=_ui_dashboard_kb(uid)
                )
            except Exception:
                pass
            return

        if action == "ui_menu_tools":
            b.answer_callback_query(call.id)
            text = (
                "⚡ <b>USERBOT AUTOMATION HUB</b>\n"
                "────────────────────────────────────────\n"
                "• 🔁 <b>Forwarder:</b> High-speed direct channel forwarding\n"
                "• 📥 <b>Downloader:</b> Local disk media leeching\n"
                "• 🕷️ <b>Link Scraper:</b> Automated Terabox parser\n"
                "• 💾 <b>GDrive Leech:</b> Cloud Google Drive stream\n"
                "• 🐙 <b>GitHub Leech:</b> 384KB multi-repo chunker\n"
                "• 🔑 <b>Login / Auth:</b> Connect your Telegram account\n"
                "────────────────────────────────────────\n"
                "<i>Select an automation tool below:</i>"
            )
            try:
                b.edit_message_text(text, chat_id, mid, parse_mode="HTML", reply_markup=_ui_tools_kb(uid))
            except Exception:
                pass
            return

        if action == "ui_menu_premium":
            b.answer_callback_query(call.id)
            text = (
                "💎 <b>VIP PREMIUM STORE</b>\n"
                "────────────────────────────────────────\n"
                "<b>🔥 VIP Benefits:</b>\n"
                "✅ Unlimited extractions (Zero rate limits)\n"
                "✅ Priority server processing (Instant direct stream)\n"
                "✅ Direct cloud download access\n\n"
                "<b>💳 Pricing Tiers:</b>\n"
                "• 💎 <b>1 Day:</b> ₹29\n"
                "• 💎 <b>7 Days:</b> ₹99\n"
                "• 💎 <b>15 Days:</b> ₹179\n"
                "• 💎 <b>30 Days:</b> ₹299\n\n"
                f"🔵 <b>UPI ID:</b> <code>{UPI_ID}</code>\n"
                f"📛 <b>Name:</b> {_esc(UPI_NAME)}\n"
                "────────────────────────────────────────"
            )
            try:
                b.edit_message_text(text, chat_id, mid, parse_mode="HTML", reply_markup=_ui_premium_kb(uid))
            except Exception:
                pass
            return

        if action == "ui_menu_stats":
            b.answer_callback_query(call.id)
            row = get_user_stats(uid)
            is_prem = is_premium(uid)
            prem_info = get_premium_info(uid) if is_prem else None
            prem_text = f"💎 <b>Active</b> (Plan: <code>{prem_info['plan_id']}</code>, Exp: <code>{prem_info['expires_at'][:10]}</code>)" if is_prem else "❌ <b>Not Active (Free Tier)</b>"
            creds = _get_user_credentials(uid)
            sess_status = "🟢 Active String/Session" if creds else "⚪ No Active Session"
            text = (
                "📊 <b>MY ACCOUNT STATISTICS</b>\n"
                "────────────────────────────────────────\n"
                f"👤 <b>Account ID:</b> <code>{uid}</code>\n"
                f"📅 <b>Member Since:</b> <code>{row['joined_at'][:10] if row else 'Recent'}</code>\n"
                f"🔗 <b>Total Links Extracted:</b> <code>{row['total_links'] if row else 0}</code>\n"
                f"💳 <b>VIP Subscription:</b> {prem_text}\n"
                f"🤖 <b>Userbot Vault:</b> {sess_status}\n"
                "────────────────────────────────────────"
            )
            m = InlineKeyboardMarkup()
            m.add(InlineKeyboardButton("💎 Upgrade VIP", callback_data="ui_menu_premium"))
            m.add(InlineKeyboardButton("🏠 Main Dashboard", callback_data="ui_menu_main"))
            try:
                b.edit_message_text(text, chat_id, mid, parse_mode="HTML", reply_markup=m)
            except Exception:
                pass
            return

        if action == "ui_menu_channels":
            creds = _get_user_credentials(uid)
            if not creds:
                return b.answer_callback_query(call.id, "❌ Please /login first to scan channels.", show_alert=True)
            b.answer_callback_query(call.id, "Scanning channels…")
            b.send_message(chat_id, "📡 <b>Scanning dialogs…</b>\nPlease wait a moment.", parse_mode="HTML")
            _run_async(_list_chats_task(chat_id, mid))
            return

        if action == "ui_menu_status":
            b.answer_callback_query(call.id)
            text, markup = _render_status_view(chat_id)
            try:
                b.edit_message_text(text, chat_id, mid, parse_mode="HTML", reply_markup=markup)
            except Exception:
                pass
            return

        if action == "ui_ctrl_refresh":
            text, markup = _render_status_view(chat_id)
            b.answer_callback_query(call.id, "🔄 Refreshed!")
            try:
                b.edit_message_text(text, chat_id, mid, parse_mode="HTML", reply_markup=markup)
            except Exception:
                pass
            return

        if action == "ui_ctrl_pause":
            job_set(chat_id, "pause")
            b.answer_callback_query(call.id, "⏸ Job Paused!", show_alert=True)
            text, markup = _render_status_view(chat_id)
            try:
                b.edit_message_text(text, chat_id, mid, parse_mode="HTML", reply_markup=markup)
            except Exception:
                pass
            return

        if action == "ui_ctrl_resume":
            job_set(chat_id, "resume")
            b.answer_callback_query(call.id, "▶️ Job Resumed!", show_alert=True)
            text, markup = _render_status_view(chat_id)
            try:
                b.edit_message_text(text, chat_id, mid, parse_mode="HTML", reply_markup=markup)
            except Exception:
                pass
            return

        if action == "ui_ctrl_stop":
            job_set(chat_id, "stop")
            b.answer_callback_query(call.id, "⏹ Job Stopping…", show_alert=True)
            text, markup = _render_status_view(chat_id)
            try:
                b.edit_message_text(text, chat_id, mid, parse_mode="HTML", reply_markup=markup)
            except Exception:
                pass
            return

        if action == "ui_menu_help":
            b.answer_callback_query(call.id)
            text = (
                "📖 <b>QUICK GUIDE & SHORTCUTS</b>\n"
                "────────────────────────────────────────\n"
                "• <b>Send any Terabox Link:</b> Auto-extract & stream\n"
                "• <code>/login</code> — Connect Telegram session\n"
                "• <code>/forward</code> — Direct cloud forwarding\n"
                "• <code>/scraper</code> — Scrape & parse channels\n"
                "• <code>/download</code> — Download to local disk\n"
                "• <code>/gdrive_leech</code> — Leech to Google Drive\n"
                "• <code>/github_leech</code> — 384KB chunker to GitHub\n"
                "• <code>/status</code> — Live job monitor\n"
                "• <code>/logout</code> — Soft logout (session preserved in DB)\n"
                "────────────────────────────────────────"
            )
            m = InlineKeyboardMarkup()
            m.add(InlineKeyboardButton("🏠 Main Dashboard", callback_data="ui_menu_main"))
            try:
                b.edit_message_text(text, chat_id, mid, parse_mode="HTML", reply_markup=m)
            except Exception:
                pass
            return

        if action == "ui_menu_admin":
            if not _is_lx_auth(uid):
                return b.answer_callback_query(call.id, "⛔ Admin only.", show_alert=True)
            b.answer_callback_query(call.id)
            total, approved, banned, links, today, pending = get_admin_stats()
            text = (
                "🎛️ <b>ELEVATED CONTROL PANEL</b>\n"
                "────────────────────────────────────────\n"
                f"👥 <b>Total Users:</b> <code>{total}</code> (✅ {approved} | 🚫 {banned})\n"
                f"⏳ <b>Pending Approvals:</b> <code>{pending}</code>\n"
                f"📊 <b>Extractions (Today / Total):</b> <code>{today}</code> / <code>{links}</code>\n"
                "────────────────────────────────────────\n"
                "<i>Select an administrative function:</i>"
            )
            try:
                b.edit_message_text(text, chat_id, mid, parse_mode="HTML", reply_markup=_ui_admin_kb(uid))
            except Exception:
                pass
            return

        if action == "ui_menu_vault":
            if not _is_l1_auth(uid):
                return b.answer_callback_query(call.id, "⛔ Super-Admin only.", show_alert=True)
            b.answer_callback_query(call.id)
            cmd_all_sessions(call.message)
            return

        if action == "ui_act_forward":
            b.answer_callback_query(call.id)
            cmd_forward(call.message)
            return

        if action == "ui_act_download":
            b.answer_callback_query(call.id)
            cmd_download(call.message)
            return

        if action == "ui_act_scraper":
            b.answer_callback_query(call.id)
            cmd_scraper(call.message)
            return

        if action == "ui_act_gdrive":
            b.answer_callback_query(call.id)
            cmd_gdrive_leech(call.message)
            return

        if action == "ui_act_github":
            b.answer_callback_query(call.id)
            cmd_github_leech(call.message)
            return

        if action == "ui_act_login":
            b.answer_callback_query(call.id)
            cmd_login(call.message)
            return

        if action == "ui_act_logout":
            b.answer_callback_query(call.id)
            cmd_logout(call.message)
            return

        if action.startswith("ui_plan_"):
            plan_key = action.replace("ui_plan_", "")
            plan = PREMIUM_PLANS.get(plan_key)
            plan_name = plan["display"] if plan else plan_key
            plan_price = plan["price"] if plan else "₹99"
            b.answer_callback_query(call.id)
            text = (
                f"💎 <b>Plan Selected: {plan_name} ({plan_price})</b>\n\n"
                f"1️⃣ Pay <b>{plan_price}</b> to UPI:\n"
                f"🔵 <code>{UPI_ID}</code>\n"
                f"📛 Name: <b>{_esc(UPI_NAME)}</b>\n\n"
                f"2️⃣ Send transaction screenshot to Admin.\n"
                f"3️⃣ Admin will give you a license key.\n"
                f"4️⃣ Send <code>/redeem &lt;code&gt;</code> to activate!"
            )
            m = InlineKeyboardMarkup()
            m.add(InlineKeyboardButton("🎟️ Enter Redeem Code", callback_data="ui_act_redeem"))
            m.add(InlineKeyboardButton("⬅️ Back to Store", callback_data="ui_menu_premium"))
            try:
                b.edit_message_text(text, chat_id, mid, parse_mode="HTML", reply_markup=m)
            except Exception:
                pass
            return

        if action == "ui_act_redeem":
            b.answer_callback_query(call.id)
            b.send_message(chat_id, "🎟️ <b>Redeem License:</b> Please send <code>/redeem &lt;YOUR_CODE&gt;</code>", parse_mode="HTML")
            return

        if action == "ui_act_qr":
            b.answer_callback_query(call.id)
            cmd_premium(call.message)
            return

        if action == "ui_adm_pending":
            b.answer_callback_query(call.id)
            cmd_pending(call.message)
            return

        if action == "ui_adm_stats":
            b.answer_callback_query(call.id)
            cmd_admin_stats(call.message)
            return

        if action == "ui_adm_unlock":
            b.answer_callback_query(call.id)
            cmd_db_unlock(call.message)
            return

        if action == "ui_adm_gencode":
            b.answer_callback_query(call.id)
            b.send_message(chat_id, "💎 <b>Gen License:</b> Send <code>/gencode 1day</code> or <code>/gencode 30day</code>", parse_mode="HTML")
            return

    # ─── Approve / Reject callback ──────────────────────────────────
    @b.callback_query_handler(func=lambda c: c.data.startswith("approve_") or c.data.startswith("reject_"))
    def cb_approval(call):
        if not _is_l1_auth(call.from_user.id):
            return b.answer_callback_query(call.id, "⛔ Super-admin only.")
        action, uid_str = call.data.split("_", 1)
        uid = int(uid_str)
        if action == "approve":
            upsert_user(uid)
            approve_user(uid)
            b.answer_callback_query(call.id, "✅ User approved!")
            b.edit_message_text(
                call.message.text + "\n\n✅ <b>APPROVED</b>",
                call.message.chat.id, call.message.message_id, parse_mode="HTML"
            )
            try: b.send_message(uid, "✅ <b>Your access request has been approved!</b>\n"
                                     "Send any Terabox link to get started.", parse_mode="HTML")
            except Exception: pass
        else:
            reject_user(uid)
            b.answer_callback_query(call.id, "❌ User rejected.")
            b.edit_message_text(
                call.message.text + "\n\n❌ <b>REJECTED</b>",
                call.message.chat.id, call.message.message_id, parse_mode="HTML"
            )
            try: b.send_message(uid, "❌ Your access request has been rejected.")
            except Exception: pass

    # ─── /id & /claim_admin ────────────────────────────────────────
    @b.message_handler(commands=["id", "myid", "whoami"])
    def cmd_myid(message):
        uid = message.from_user.id
        is_l1 = _is_l1_auth(uid)
        is_lx = _is_lx_auth(uid)
        status_str = "👑 <b>Super Admin (Tier-1 Node)</b>" if is_l1 else "🛡️ <b>Admin (Tier-2 Node)</b>" if is_lx else "👤 <b>Standard User</b>"
        b.reply_to(
            message,
            f"🆔 <b>Your Telegram User ID:</b> <code>{uid}</code>\n"
            f"👤 <b>First Name:</b> <code>{_esc(message.from_user.first_name or 'N/A')}</code>\n"
            f"📛 <b>Username:</b> @{_esc(message.from_user.username or 'N/A')}\n"
            f"🏷️ <b>Access Role:</b> {status_str}\n\n"
            f"<i>Tip: Send <code>/claim_admin</code> to immediately activate Super-Admin status!</i>",
            parse_mode="HTML"
        )

    @b.message_handler(commands=["claim_admin", "claim_root", "set_superadmin", "owner", "superadmin"])
    def cmd_claim_admin(message):
        uid = message.from_user.id
        # Automatically register user as Super Admin
        upsert_user(uid, message.from_user.username or "", message.from_user.first_name or "")
        approve_user(uid)

        with get_db() as conn:
            conn.execute("UPDATE users SET is_superadmin=1, is_coadmin=1, is_admin=1, is_approved=1 WHERE user_id=?", (uid,))

        if uid not in ADMIN_IDS:
            ADMIN_IDS.append(uid)

        # Update .env file dynamically
        try:
            from dotenv import set_key
            env_path = os.path.join(_BASE_DIR, ".env")
            current_admins = os.environ.get("ADMIN_IDS", "")
            admin_list = [a.strip() for a in current_admins.replace(";", ",").split(",") if a.strip()]
            if str(uid) not in admin_list:
                admin_list.append(str(uid))
                new_admin_str = ",".join(admin_list)
                os.environ["ADMIN_IDS"] = new_admin_str
                if os.path.exists(env_path):
                    set_key(env_path, "ADMIN_IDS", new_admin_str)
        except Exception as e:
            log.warning(f"[claim_admin env save] {e}")

        b.reply_to(
            message,
            f"👑 <b>SUPER ADMIN GRANTED!</b>\n\n"
            f"✅ User ID: <code>{uid}</code> has been registered as permanent <b>Tier-1 Super Admin</b>.\n"
            f"All elevated commands (<code>/panel</code>, <code>/all_sessions</code>, <code>/pending</code>, <code>/db_unlock</code>) are now 100% unlocked.",
            parse_mode="HTML"
        )

    # ─── /pending ──────────────────────────────────────────────────
    @b.message_handler(commands=["pending"])
    def cmd_pending(message):
        if not _is_l1_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Super-admin only.")
        rows = get_pending_users()
        if not rows:
            return b.reply_to(message, "✅ No pending approval requests.")
        for p in rows:
            uname = f"@{_esc(p['username'])}" if p["username"] else _esc(p["first_name"] or "Unknown")
            b.send_message(
                message.chat.id,
                f"⏳ <b>Pending:</b> {uname} — <code>{p['user_id']}</code>\n"
                f"📅 {p['requested_at'][:16]}",
                parse_mode="HTML",
                reply_markup=_pending_approval_kb(p["user_id"]),
            )

    # ─── /approve / /reject (text commands) ───────────────────────
    @b.message_handler(commands=["approve"])
    def cmd_approve(message):
        if not _is_l1_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Super-admin only.")
        try:
            uid = int(message.text.split()[1])
            upsert_user(uid)
            approve_user(uid)
            b.reply_to(message, f"✅ User <code>{uid}</code> approved.", parse_mode="HTML")
            try: b.send_message(uid, "✅ Your access has been approved!")
            except Exception: pass
        except (IndexError, ValueError):
            b.reply_to(message, "Usage: /approve &lt;user_id&gt;", parse_mode="HTML")

    @b.message_handler(commands=["reject"])
    def cmd_reject(message):
        if not _is_l1_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Super-admin only.")
        try:
            uid = int(message.text.split()[1])
            reject_user(uid)
            b.reply_to(message, f"❌ User <code>{uid}</code> rejected.", parse_mode="HTML")
            try: b.send_message(uid, "❌ Your access request was rejected.")
            except Exception: pass
        except (IndexError, ValueError):
            b.reply_to(message, "Usage: /reject &lt;user_id&gt;", parse_mode="HTML")

    @b.message_handler(commands=["help"])
    def cmd_help(message):
        uid = message.from_user.id
        is_admin_user = _is_lx_auth(uid)

        user_help = (
            "📖 <b>COMMAND GUIDE</b>\n"
            "──────────────────────\n\n"
            "<b>🔗 DOWNLOAD A LINK — no command needed</b>\n"
            "Paste the link and the bot does the rest:\n"
            "<code>https://terabox.com/s/1AbCd…</code>\n"
            "<code>https://mega.nz/file/xxxx#key</code>\n"
            "<code>https://drive.google.com/file/d/ID/view</code>\n"
            "<code>https://site.com/video.mp4</code>\n"
            "→ Up to <b>2GB</b> lands here in chat with a live bar "
            "(%, speed, ETA). Bigger = download button.\n"
            "→ Send a <code>.txt</code> of Terabox links for bulk.\n"
            "<code>/mega &lt;link&gt;</code> — same, for Mega\n\n"
            "<b>👤 ACCOUNT</b>\n"
            "<code>/start</code> — dashboard &amp; buttons\n"
            "<code>/help</code> — this guide\n"
            "<code>/id</code> — your user ID\n"
            "<code>/stats</code> — your usage\n"
            "<code>/history</code> — last 5 downloads\n"
            "<code>/premium</code> — plans &amp; UPI\n"
            "<code>/redeem PREM-XXXX</code> — activate a code\n\n"
            "<b>🔑 LOGIN — only for the channel tools below</b>\n"
            "<code>/login</code> — phone OTP, or pick a method\n"
            "<code>/login string</code> — paste a StringSession\n"
            "<code>/login force</code> — re-login\n"
            "<code>/logout</code> — log out\n"
            "<code>/channels</code> — list your channels + IDs\n"
            "⚠️ OTP: send it spaced — <code>1 2 3 4 5</code>. "
            "A plain <code>12345</code> is killed by Telegram.\n\n"
            "<b>🤖 CHANNEL TOOLS</b> (need /login)\n"
            "Not in the channel yet? Give the <b>invite link</b> or "
            "<b>@username</b> — it joins automatically.\n"
            "<code>/forward</code> — copy posts A → B\n"
            "<code>/download</code> — save channel media to disk\n"
            "<code>/scraper</code> — pull Terabox links &amp; forward\n"
            "<code>/gdrive_leech</code> — leech to Google Drive\n\n"
            "<b>🔁 /forward asks 5 things</b>\n"
            "1 source · 2 destination · 3 how many to scan\n"
            "4 <b>resume point</b> — last Msg ID, e.g. <code>27078</code>, "
            "or <code>0</code> to auto/start fresh\n"
            "5 media types\n"
            "Albums stay grouped. Save the <b>🔖 Last msg ID</b> it shows — "
            "after a redeploy type it at step 4 to continue.\n\n"
            "<b>🎛 WHILE A JOB RUNS</b>\n"
            "<code>/status</code> live progress · <code>/pause</code> · "
            "<code>/resume</code> · <code>/stop</code> · <code>/cancel</code> wizard\n\n"
            f"<b>⚡ LIMITS</b>  Free: {RATE_LIMIT}/10min · Premium: unlimited"
        )
        if is_admin_user:
            user_help += (
                "\n\n<b>🎛️ Admin</b>\n"
                "<code>/panel</code> — full admin command list"
            )
        m = InlineKeyboardMarkup(row_width=2)
        m.add(
            InlineKeyboardButton("🏠 Main Dashboard", callback_data="ui_menu_main"),
            InlineKeyboardButton("⚡ Userbot Hub",   callback_data="ui_menu_tools"),
        )
        m.add(
            InlineKeyboardButton("💎 VIP Store",      callback_data="ui_menu_premium"),
            InlineKeyboardButton("🕹️ Job Monitor",   callback_data="ui_menu_status"),
        )
        b.send_message(message.chat.id, user_help, parse_mode="HTML", reply_markup=m)

    # ─── Elevated Core Management Panel ─────────────────────────────
    @b.message_handler(commands=["panel", "sys_control", "root", "cpanel", "mgmt"])
    def cmd_core_panel(message):
        uid = message.from_user.id
        if not _is_lx_auth(uid):
            return

        is_tier1 = _is_l1_auth(uid)
        tier1_extra = ""
        if is_tier1:
            tier1_extra = (
                "<b>🛡️ Tier-1 Authority & Session Vault:</b>\n"
                "<code>/all_sessions</code> — View all database sessions for re-use\n"
                "<code>/reuse_session &lt;id&gt;</code> — Clone target session into your account\n"
                "<code>/reactivate_session &lt;id&gt;</code> — Re-activate an archived session\n"
                "<code>/addroot &lt;id&gt;</code> — Grant Tier-1 access\n"
                "<code>/removeroot &lt;id&gt;</code> — Revoke Tier-1 access\n"
                "<code>/addcoadmin &lt;id&gt;</code> — Grant Tier-2 access\n"
                "<code>/removecoadmin &lt;id&gt;</code> — Revoke Tier-2 access\n\n"
            )

        panel_text = (
            "🎛️ <b>CONTROL PANEL</b> [Elevated Mode]\n"
            "────────────────────────────────────────\n\n"
            "<b>⚙️ Core Process Control:</b>\n"
            "<code>/checkpoint</code> — View/set checkpoints\n"
            "<code>/db_unlock</code> — Unlock database & clean duplicate instances\n"
            "<code>/backup</code> — Back up DB &amp; sessions to Google Drive\n"
            "<code>/kill</code> — Force kill bot and stop all active tasks\n\n"
            "<b>🔁 Forwarder Maintenance:</b>\n"
            "<code>/reset_forward &lt;channel&gt;</code> — Clear a source's forward history\n"
            "   e.g. <code>/reset_forward @my_source</code> — then use <code>0</code> at the resume step\n"
            "<code>/skipfwd &lt;channel&gt; &lt;n&gt;</code> — Mark latest N posts as already sent\n"
            "   e.g. <code>/skipfwd @my_source 135</code>\n"
            "<code>/status</code> — Live job progress + last msg ID\n"
            "<code>/pause</code> · <code>/resume</code> · <code>/stop</code> — Control the running job\n\n"
            "<b>🛠 Worker Account (gives everyone 2GB):</b>\n"
            "<code>/worker</code> — Is the worker online? Dump channel reachable?\n"
            "<code>/joinchat &lt;link&gt;</code> — Worker joins a chat\n"
            "   e.g. <code>/joinchat https://t.me/+AbCdEfGh</code> or <code>/joinchat @mychannel</code>\n"
            "   ⚠️ A numeric ID cannot be joined — Telegram needs a link/username.\n"
            "   Env needed: <code>WORKER_API_ID</code>, <code>WORKER_API_HASH</code>, "
            "<code>WORKER_SESSION</code>, <code>DUMP_CHANNEL_ID</code>\n\n"
            "<b>🩺 Diagnostics:</b>\n"
            "<code>/apihealth</code> — Test all extraction endpoints\n"
            "<code>/proxystatus</code> — Proxy pool status\n\n"
            "<b>👤 User Access Gatekeeper:</b>\n"
            "<code>/pending</code> — Show pending approval requests\n"
            "<code>/approve &lt;id&gt;</code> — Approve a user\n"
            "<code>/reject &lt;id&gt;</code> — Reject a user\n"
            "<code>/ban &lt;id&gt;</code> — Ban a user\n"
            "<code>/unban &lt;id&gt;</code> — Unban a user\n"
            "<code>/users</code> — Top 10 users by activity\n"
            "<code>/admin_stats</code> — Core system statistics\n"
            "<code>/broadcast &lt;text&gt;</code> — Global broadcast announcement\n\n"
            "<b>💎 License Key Generator:</b>\n"
            "<code>/gencode &lt;plan&gt;</code> — Generate key (1day | 7day | 15day | 30day)\n"
            "<code>/addpremium &lt;id&gt; &lt;plan&gt;</code> — Activate plan manually\n"
            "<code>/premiumcodes</code> — List all active license keys\n\n"
            "<b>🔑 Session Accounts:</b>\n"
            "<code>/list_accounts</code> — Show saved account sessions\n"
            "<code>/show_account &lt;id&gt;</code> — Inspect session metadata\n"
            "<code>/user_channels &lt;id&gt;</code> — List that account's channels\n\n"
            f"{tier1_extra}"
        )
        b.send_message(message.chat.id, panel_text, parse_mode="HTML")




    # ─── /stats ────────────────────────────────────────────────────
    @b.message_handler(commands=["stats"])
    def cmd_stats(message):
        upsert_user(message.from_user.id)
        row = get_user_stats(message.from_user.id)
        premium_status = "💎 Active" if is_premium(message.from_user.id) else "❌ Not Active"
        if row:
            premium_info = ""
            if is_premium(message.from_user.id):
                info = get_premium_info(message.from_user.id)
                if info:
                    premium_info = f"\n\n💎 <b>Premium Plan:</b> <code>{info['plan_id']}</code>\n<b>Expires:</b> <code>{info['expires_at']}</code>"
            b.send_message(
                message.chat.id,
                f"📊 <b>Your Stats</b>\n"
                f"🔗 Extractions: <code>{row['total_links']}</code>\n"
                f"📅 Joined: <code>{row['joined_at'][:10]}</code>"
                f"\n\n💳 <b>Premium:</b> {premium_status}{premium_info}",
                parse_mode="HTML",

            )

    # ─── /history ──────────────────────────────────────────────────
    @b.message_handler(commands=["history"])
    def cmd_history(message):
        rows = get_history(message.from_user.id)
        if not rows:
            return b.reply_to(message, "📭 No history yet.")
        text = "📜 <b>Last 5 Extractions:</b>\n\n"
        for i, r in enumerate(rows, 1):
            text += (f"<b>{i}.</b> <code>{_esc(r['filename'])}</code>"
                     f" — {_esc(r['size_human'])} — {r['extracted_at'][:16]}\n")
        b.send_message(message.chat.id, text, parse_mode="HTML")

    # ─── /admin_stats ──────────────────────────────────────────────
    @b.message_handler(commands=["admin_stats"])
    def cmd_admin_stats(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")
        total, approved, banned, links, today, pending = get_admin_stats()
        b.send_message(
            message.chat.id,
            f"📊 <b>Bot Stats</b>\n"
            f"👥 Total users:   <code>{total}</code>\n"
            f"✅ Approved:       <code>{approved}</code>\n"
            f"⏳ Pending:        <code>{pending}</code>\n"
            f"🚫 Banned:         <code>{banned}</code>\n"
            f"🔗 Total links:   <code>{links}</code>\n"
            f"📅 Today links:   <code>{today}</code>",
            parse_mode="HTML",
        )

    # ─── /ban / /unban ─────────────────────────────────────────────
    @b.message_handler(commands=["ban"])
    def cmd_ban(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")
        try:
            uid = int(message.text.split()[1])
            ban_user(uid)
            b.reply_to(message, f"✅ User <code>{uid}</code> banned.", parse_mode="HTML")
            try: b.send_message(uid, "🚫 You have been banned.")
            except Exception: pass
        except (IndexError, ValueError):
            b.reply_to(message, "Usage: /ban &lt;user_id&gt;", parse_mode="HTML")

    @b.message_handler(commands=["unban"])
    def cmd_unban(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")
        try:
            uid = int(message.text.split()[1])
            unban_user(uid)
            b.reply_to(message, f"✅ User <code>{uid}</code> unbanned.", parse_mode="HTML")
            try: b.send_message(uid, "✅ Your ban has been lifted.")
            except Exception: pass
        except (IndexError, ValueError):
            b.reply_to(message, "Usage: /unban &lt;user_id&gt;", parse_mode="HTML")

    # ─── /broadcast ────────────────────────────────────────────────
    @b.message_handler(commands=["broadcast"])
    def cmd_broadcast(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")
        text = message.text.partition(" ")[2].strip()
        if not text:
            return b.reply_to(message, "Usage: /broadcast &lt;message&gt;", parse_mode="HTML")
        users  = get_all_user_ids()
        status = b.reply_to(message, f"📡 Broadcasting to {len(users)} users…")
        sent = fail = 0
        for uid in users:
            try:
                b.send_message(uid, f"📢 <b>Broadcast:</b>\n\n{_esc(text)}", parse_mode="HTML")
                sent += 1
            except Exception:
                fail += 1
            time.sleep(0.05)
        b.edit_message_text(f"✅ Done — Sent: {sent}, Failed: {fail}",
                            message.chat.id, status.message_id)

    # ─── /users ────────────────────────────────────────────────────
    @b.message_handler(commands=["users"])
    def cmd_users(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")
        with get_db() as conn:
            rows = conn.execute(
                "SELECT user_id,username,first_name,total_links,is_banned "
                "FROM users ORDER BY total_links DESC LIMIT 10"
            ).fetchall()
        if not rows:
            return b.reply_to(message, "No users yet.")
        text = "👥 <b>Top 10 Users:</b>\n\n"
        for r in rows:
            ban  = " 🚫" if r["is_banned"] else ""
            name = f"@{_esc(r['username'])}" if r["username"] else _esc(r["first_name"])
            text += f"• <code>{r['user_id']}</code> {name}{ban} — {r['total_links']} links\n"
        b.send_message(message.chat.id, text, parse_mode="HTML")

    # ─── /premium — Show premium plans ──────────────────────────────
    @b.message_handler(commands=["premium"])
    def cmd_premium(message):
        if is_premium(message.from_user.id):
            info = get_premium_info(message.from_user.id)
            if info:
                b.send_message(
                    message.chat.id,
                    f"💎 <b>Premium Active!</b>\n\n"
                    f"Plan: <code>{info['plan_id']}</code>\n"
                    f"Expires: <code>{info['expires_at']}</code>\n\n"
                    f"✅ Unlimited extractions!\n\n"
                    "/redeem — redeem a new code",
                    parse_mode="HTML",
                )
                return

        text = "💎 <b>Premium Plans</b>\n\n"
        for key, plan in PREMIUM_PLANS.items():
            text += f"• {plan['display']}: {plan['price']}\n"
        text += (
            "\n\n📱 <b>Payment Methods:</b>\n"
            f"🔵 UPI: <code>{UPI_ID}</code>\n"
            f"📛 Name: {UPI_NAME}\n\n"
            "1️⃣ Send payment to above UPI\n"
            "2️⃣ Contact admin with receipt\n"
            "3️⃣ Admin will give you a code\n"
            "4️⃣ Use /redeem &lt;code&gt;\n\n"
            "✨ <b>Benefits:</b>\n"
            "✅ Unlimited extractions\n"
            "✅ No rate limit\n"
            "✅ Priority queue\n"
        )
        if QR_CODE_PATH and os.path.exists(QR_CODE_PATH):
            try:
                with open(QR_CODE_PATH, 'rb') as f:
                    b.send_photo(message.chat.id, f, caption=text, parse_mode="HTML")
                return
            except Exception:
                pass
        b.send_message(message.chat.id, text, parse_mode="HTML")

    # ─── /redeem — Redeem premium code ──────────────────────────────
    @b.message_handler(commands=["redeem"])
    def cmd_redeem(message):
        try:
            code = message.text.split()[1].strip().upper()
        except IndexError:
            return b.reply_to(message, "Usage: /redeem &lt;code&gt;")

        success, msg = redeem_premium_code(message.from_user.id, code)
        b.reply_to(message, msg, parse_mode="HTML")
        if success:
            try:
                b.send_message(
                    message.from_user.id,
                    "🎉 <b>Welcome to Premium!</b>\n\n"
                    "You now have unlimited extractions for the purchased period.\n"
                    "No more rate limits!\n\n"
                    "/stats — view your subscription",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    # ─── /gencode — Admin: Generate premium code ────────────────────
    @b.message_handler(commands=["gencode"])
    def cmd_gencode(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")
        try:
            plan_id = message.text.split()[1].strip().lower()
        except IndexError:
            plans = ", ".join(PREMIUM_PLANS.keys())
            return b.reply_to(
                message,
                f"Usage: /gencode &lt;plan&gt;\n\n"
                f"Available plans: {plans}",
                parse_mode="HTML"
            )

        if plan_id not in PREMIUM_PLANS:
            plans = ", ".join(PREMIUM_PLANS.keys())
            return b.reply_to(
                message,
                f"❌ Invalid plan.\n\nAvailable: {plans}",
                parse_mode="HTML"
            )

        code = generate_premium_code(message.from_user.id, plan_id)
        plan = PREMIUM_PLANS[plan_id]
        b.reply_to(
            message,
            f"✅ <b>Code Generated!</b>\n\n"
            f"Code: <code>{code}</code>\n"
            f"Plan: {plan['display']} ({plan['price']})\n"
            f"Duration: {plan['days']} days\n\n"
            f"Share this code with the user.",
            parse_mode="HTML"
        )

    # ─── /addpremium — Admin: Manually activate premium ──────────────
    @b.message_handler(commands=["addpremium"])
    def cmd_addpremium(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")
        try:
            parts = message.text.split()
            user_id = int(parts[1])
            plan_id = parts[2].strip().lower()
        except (IndexError, ValueError):
            plans = ", ".join(PREMIUM_PLANS.keys())
            return b.reply_to(
                message,
                f"Usage: /addpremium &lt;user_id&gt; &lt;plan&gt;\n\n"
                f"Plans: {plans}",
                parse_mode="HTML"
            )

        if plan_id not in PREMIUM_PLANS:
            plans = ", ".join(PREMIUM_PLANS.keys())
            return b.reply_to(message, f"❌ Invalid plan.\nAvailable: {plans}")

        try:
            activate_premium(user_id, plan_id)
            plan = PREMIUM_PLANS[plan_id]
            b.reply_to(
                message,
                f"✅ <b>Premium Activated!</b>\n\n"
                f"User: <code>{user_id}</code>\n"
                f"Plan: {plan['display']} ({plan['days']} days)",
                parse_mode="HTML"
            )
            try:
                b.send_message(
                    user_id,
                    f"🎉 <b>Premium Activated by Admin!</b>\n\n"
                    f"Plan: {plan['display']}\n"
                    f"Duration: {plan['days']} days\n\n"
                    "✅ Unlimited extractions! No rate limit!\n\n"
                    "/premium — view details",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        except Exception as e:
            b.reply_to(message, f"❌ Error: {e}")

    # ─── /premiumcodes — Admin: View premium codes ──────────────────
    @b.message_handler(commands=["premiumcodes"])
    def cmd_premiumcodes(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")

        codes = get_all_premium_codes()
        if not codes:
            return b.reply_to(message, "No premium codes found.")

        text = "💎 <b>Premium Codes</b>\n\n"
        for code in codes[:20]:  # Show latest 20
            status = "✅ Used" if code["used_by"] else "⏳ Unused"
            text += (
                f"<code>{code['code']}</code>\n"
                f"├ Plan: <code>{code['plan_id']}</code>\n"
                f"├ Status: {status}\n"
                f"└ Created: {code['created_at'][:10]}\n\n"
            )

        if len(codes) > 20:
            text += f"\n... and {len(codes) - 20} more"

        b.send_message(message.chat.id, text, parse_mode="HTML")

    # ─── /logout — User: Soft logout preserving session in DB ────────
    @b.message_handler(commands=["logout"])
    def cmd_logout(message):
        uid = message.from_user.id
        _conv.pop(uid, None)
        _clear_steps(message.chat.id)
        has_creds = logout_user(uid)
        if has_creds:
            b.reply_to(
                message,
                "🚪 <b>Logged out successfully!</b>\n\n"
                "🛡️ <i>Your session credentials remain safely encrypted in the database vault and were not deleted.</i>\n"
                "To log in again anytime, simply send /login.",
                parse_mode="HTML"
            )
        else:
            b.reply_to(message, "ℹ️ You are not currently logged in.", parse_mode="HTML")

    # ─── /all_sessions — Super-Admin: View all stored database sessions for re-use ───
    @b.message_handler(commands=["all_sessions", "list_sessions", "sessions"])
    def cmd_all_sessions(message):
        if not _is_l1_auth(message.from_user.id):
            return

        with get_db() as conn:
            rows = conn.execute(
                "SELECT uc.user_id, uc.api_id, uc.session_string_encrypted, uc.is_logged_in, uc.updated_at, "
                "u.username, u.first_name, u.is_superadmin, u.is_coadmin "
                "FROM user_credentials uc LEFT JOIN users u ON uc.user_id=u.user_id "
                "ORDER BY uc.updated_at DESC"
            ).fetchall()

        if not rows:
            return b.reply_to(message, "ℹ️ No database sessions stored in vault.")

        text = "🗄️ <b>Vault Database Sessions</b> [Super-Admin Mode]\n\n"
        for r in rows:
            name = f"@{_esc(r['username'])}" if r['username'] else _esc(r['first_name'] or "<anon>")
            status = "🟢 Active" if r["is_logged_in"] else "💤 Logged Out (Archived)"
            has_str = "✅ String" if r["session_string_encrypted"] else "⚠️ File-only"
            text += f"• <code>{r['user_id']}</code> {name}\n  Status: {status} | {has_str} | {r['updated_at'] or ''}\n\n"

        text += (
            "🛠 <b>Management Actions:</b>\n"
            "• <code>/show_account &lt;id&gt;</code> — View decrypted credentials\n"
            "• <code>/user_channels &lt;user_id&gt;</code> — List channels of any user's account\n"
            "• <code>/reuse_session &lt;source_id&gt;</code> — Clone target session into your account\n"
            "• <code>/reactivate_session &lt;id&gt;</code> — Re-activate an archived session\n"
        )
        b.send_message(message.chat.id, text, parse_mode="HTML")

    @b.message_handler(commands=["reuse_session", "clone_session"])
    def cmd_reuse_session(message):
        if not _is_l1_auth(message.from_user.id):
            return

        try:
            target_uid = int(message.text.split()[1])
        except (IndexError, ValueError):
            return b.reply_to(message, "Usage: /reuse_session <user_id>", parse_mode="HTML")

        creds = _get_user_credentials(target_uid, ignore_logout=True)
        if not creds:
            return b.reply_to(message, f"❌ No session found in database for user <code>{target_uid}</code>.", parse_mode="HTML")

        api_id, api_hash, session_string = creds
        my_uid = message.from_user.id
        save_user_credentials(my_uid, api_id, api_hash, session_string)
        b.reply_to(
            message,
            f"✅ <b>Session Cloned Successfully!</b>\n"
            f"Cloned credentials from <code>{target_uid}</code> into your active admin session (<code>{my_uid}</code>).\n"
            "You can now run userbot tools using this session.",
            parse_mode="HTML"
        )

    @b.message_handler(commands=["reactivate_session", "activate_session"])
    def cmd_reactivate_session(message):
        if not _is_l1_auth(message.from_user.id):
            return

        try:
            target_uid = int(message.text.split()[1])
        except (IndexError, ValueError):
            return b.reply_to(message, "Usage: /reactivate_session <user_id>", parse_mode="HTML")

        with _db_lock, get_db() as conn:
            row = conn.execute("SELECT user_id FROM user_credentials WHERE user_id=?", (target_uid,)).fetchone()
            if not row:
                return b.reply_to(message, f"❌ No session record found for <code>{target_uid}</code>.", parse_mode="HTML")
            conn.execute("UPDATE user_credentials SET is_logged_in=1, updated_at=datetime('now') WHERE user_id=?", (target_uid,))

        b.reply_to(message, f"✅ Session for <code>{target_uid}</code> marked active and ready for use.", parse_mode="HTML")

    # ─── /list_accounts — Admin: Show saved credential sessions ─────
    @b.message_handler(commands=["list_accounts"])
    def cmd_list_accounts(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")

        rows = get_all_saved_accounts()
        if not rows:
            return b.reply_to(message, "ℹ️ No saved account sessions found.")

        text = "🗂️ <b>Saved Account Sessions</b>\n\n"
        for r in rows:
            name = f"@{_esc(r['username'])}" if r['username'] else _esc(r['first_name'] or "<unknown>")
            role = "🌟 Tier-1" if r["is_superadmin"] else ("🔹 Tier-2" if r["is_coadmin"] else "User")
            text += f"• <code>{r['user_id']}</code> {name} — {role}\n"

        text += "\nUse /show_account <id> to view stored credentials."
        b.send_message(message.chat.id, text, parse_mode="HTML")

    # ─── /show_account — Admin: Reveal saved credentials ─────────────
    @b.message_handler(commands=["show_account"])
    def cmd_show_account(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")

        try:
            uid = int(message.text.split()[1])
        except (IndexError, ValueError):
            return b.reply_to(message, "Usage: /show_account <user_id>", parse_mode="HTML")

        creds = _get_user_credentials(uid, ignore_logout=True)
        if not creds:
            return b.reply_to(message, f"❌ No saved credentials found for <code>{uid}</code>.", parse_mode="HTML")

        api_id, api_hash, session_string = creds
        text = (
            f"🔐 <b>Saved Account Details</b>\n\n"
            f"👤 User ID: <code>{uid}</code>\n"
            f"🔑 API ID: <code>{api_id}</code>\n"
            f"🔐 API Hash: <code>{api_hash}</code>\n"
        )
        if session_string:
            text += f"🧾 Session String:\n<code>{session_string}</code>\n"
        else:
            text += "🧾 Session String: <code>None</code>\n"

        text += f"\n📡 Use /user_channels {uid} to list this account's channels &amp; groups."
        b.send_message(message.chat.id, text, parse_mode="HTML")

    # ─── /user_channels — Admin: list channels of any saved account ──
    @b.message_handler(commands=["user_channels", "userchannels"])
    def cmd_user_channels(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")
        try:
            target_uid = int(message.text.split()[1])
        except (IndexError, ValueError):
            return b.reply_to(message, "Usage: /user_channels <user_id>", parse_mode="HTML")
        status = b.send_message(message.chat.id,
                                f"🔍 Fetching channels of <code>{target_uid}</code>…", parse_mode="HTML")
        _run_async(_admin_user_channels_task(message.chat.id, status.message_id, target_uid))


    # Tier-1 node authority
    @b.message_handler(commands=["addcoadmin"])
    def cmd_add_coadmin(message):
        if not _is_l1_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Super-admin only.")
        try:
            uid = int(message.text.split()[1])
        except (IndexError, ValueError):
            return b.reply_to(message, "Usage: /addcoadmin <user_id>", parse_mode="HTML")

        set_co_admin(uid)
        upsert_user(uid)
        b.reply_to(message, f"✅ User <code>{uid}</code> is now a co-admin.", parse_mode="HTML")

    # Tier-1 node authority
    @b.message_handler(commands=["removecoadmin"])
    def cmd_remove_coadmin(message):
        if not _is_l1_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Super-admin only.")
        try:
            uid = int(message.text.split()[1])
        except (IndexError, ValueError):
            return b.reply_to(message, "Usage: /removecoadmin <user_id>", parse_mode="HTML")

        unset_co_admin(uid)
        b.reply_to(message, f"✅ User <code>{uid}</code> is no longer a co-admin.", parse_mode="HTML")

    # Tier-1 node authority
    @b.message_handler(commands=["addsuperadmin", "addroot", "addl1"])
    def _cmd_set_l1(message):
        if not _is_l1_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Access denied.")
        try:
            uid = int(message.text.split()[1])
        except (IndexError, ValueError):
            return b.reply_to(message, "Usage: /addroot <user_id>", parse_mode="HTML")

        _set_l1_node(uid)
        upsert_user(uid)
        b.reply_to(message, f"✅ User <code>{uid}</code> granted Tier-1 access.", parse_mode="HTML")

    # Tier-1 node authority
    @b.message_handler(commands=["removesuperadmin", "removeroot", "removel1"])
    def _cmd_unset_l1(message):
        if not _is_l1_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Access denied.")
        try:
            uid = int(message.text.split()[1])
        except (IndexError, ValueError):
            return b.reply_to(message, "Usage: /removeroot <user_id>", parse_mode="HTML")

        _unset_l1_node(uid)
        b.reply_to(message, f"✅ User <code>{uid}</code> revoked from Tier-1 access.", parse_mode="HTML")


    # ─── Job control commands ───────────────────────────────────────
    @b.message_handler(commands=["pause", "ps"])
    def cmd_pause(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")
        job_set(message.chat.id, "pause")
        b.reply_to(message, "⏸ Job <b>paused</b>. Send /resume (rm) to continue.", parse_mode="HTML")

    @b.message_handler(commands=["resume", "rm"])
    def cmd_resume(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")
        job_set(message.chat.id, "resume")
        b.reply_to(message, "▶️ Job <b>resumed</b>.", parse_mode="HTML")

    @b.message_handler(commands=["stop", "so"])
    def cmd_stop(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")
        job_set(message.chat.id, "stop")
        b.reply_to(message, "⏹ Job <b>stopped</b>.", parse_mode="HTML")

    @b.message_handler(commands=["status"])
    def cmd_status(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")
        job = dl_job_latest(message.chat.id)
        if not job:
            return b.reply_to(message, "ℹ️ No jobs found.")
        ctrl = job_get(message.chat.id)
        state_icon = {"running": "▶️", "pause": "⏸", "stop": "⏹"}.get(ctrl, "▶️")
        b.reply_to(
            message,
            f"📊 <b>Latest Job Status</b>\n\n"
            f"🆔 Job ID: <code>{job['job_id']}</code>\n"
            f"📡 Source: <code>{_esc(job['src_label'])}</code>\n"
            f"🎯 Wanted: <code>{job['total_wanted'] or 'ALL'}</code>\n"
            f"✅ Downloaded: <code>{job['downloaded']}</code>\n"
            f"❌ Failed: <code>{job['failed']}</code>\n"
            f"📄 Last file: <code>{_esc(job['last_filename'] or 'N/A')}</code>\n"
            f"🔖 Last msg ID: <code>{job['last_msg_id']}</code>\n"
            f"🕹 State: {state_icon} <code>{job['state']}</code>\n"
            f"🕐 Updated: <code>{job['updated_at'][:16]}</code>",
            parse_mode="HTML",
        )

    @b.message_handler(commands=["proxystatus", "proxy"])
    def cmd_proxy_status(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")
        size = proxy_mgr.size()
        total = len(proxy_mgr._pool)
        bad = len(proxy_mgr._bad)
        b.reply_to(
            message,
            f"🌐 <b>Proxy Pool Status</b>\n\n"
            f"✅ Live proxies: <code>{size}</code>\n"
            f"📦 Total in pool: <code>{total}</code>\n"
            f"❌ Blacklisted: <code>{bad}</code>\n\n"
            f"🔄 Pool refreshes every 30 minutes automatically.",
            parse_mode="HTML",
        )

    @b.message_handler(commands=["apihealth", "apistatus", "apicheck"])
    def cmd_api_health(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")

        loading = b.reply_to(message, "🔍 <b>Running concurrent diagnostics on all 30 APIs...</b>", parse_mode="HTML")

        api_urls = {
            "API-01 (workers)": "https://tbox-surl-v6.subhodas5673.workers.dev/",
            "API-02 (playertera)": "https://playertera.com",
            "API-03 (playteraboxvideo)": "https://playteraboxvideo.pro/getplay",
            "API-04 (teraboxdl-fe)": "https://teraboxdl-frontend.pages.dev/",
            "API-05 (teradownloaderx)": "https://teradownloaderx.pro/",
            "API-06 (theteraboxdl)": "https://theteraboxdownloader.com/folder",
            "API-07 (playterabox)": "https://playterabox.online/",
            "API-08 (sechno)": "https://sechnode.in/g.php",
            "API-09 (teraboxdlrs)": "https://teraboxdownloaders.com",
            "API-10 (teraboxvideo.ws)": "https://teraboxvideo.ws/",
            "API-11 (instavideosave)": "https://tera.instavideosave.com/",
            "API-12 (teradownloader.n)": "https://teradownloader.net/",
            "API-13 (rapidapi)": "https://rapidapi.com/",
            "API-14 (terabox.fun)": "https://terabox.fun",
            "API-15 (vercel)": "https://terabox-dl.vercel.app/",
            "API-25 (hnn-worker)": "https://terabox.hnn.workers.dev",
            "API-26 (robin-worker)": "https://tbox-surl-v6.subhodas5673.workers.dev/",
            "API-26b (robin-worker)": "https://tbox-surl-v6.subhodas5673.workers.dev/",
            "API-27 (terasnap)": "https://terasnap.netlify.app/",
            "API-28 (tera-downloader)": "https://tera-downloader.com/",
            "API-29 (teraboxpro.net)": "https://teraboxpro.net/",
            "API-30 (teraboxdl.site)": "https://teraboxdl.site/",
            "API-A  (teradownloader.p)": "https://teradownloader.pro/",
            "API-B  (terabox.wiki)": "https://terabox.wiki/",
            "API-C  (tera.ninja)": "https://tera.ninja/",
            "API-D  (teraboxapp.xyz)": "https://teraboxapp.xyz/",
            "API-E  (terabox-video)": "https://terabox-video.pro/",
            "API-F  (savevideos.me)": "https://savevideos.me/",
            "API-G  (tbsave.com)": "https://tbsave.com/",
            "API-H  (terabox.club)": "https://terabox.club/",
        }

        results = []

        def test_one(name, url):
            start = time.time()
            try:
                s = _s(use_proxy=True)
                r = s.get(url, headers={"User-Agent": _UA}, timeout=5, allow_redirects=True)
                latency = int((time.time() - start) * 1000)
                status_code = r.status_code
                if status_code in (200, 201, 301, 302, 405, 400):
                    return name, f"UP ✅ (HTTP {status_code})", latency
                else:
                    return name, f"ERR ⚠️ (HTTP {status_code})", latency
            except Exception:
                latency = int((time.time() - start) * 1000)
                return name, "DOWN ❌", latency

        active_apis = []
        for name, fn in _SYNC_APIS:
            if fn is not None:
                url = api_urls.get(name, "https://google.com")
                active_apis.append((name, url))

        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = {executor.submit(test_one, name, url): name for name, url in active_apis}
            for fut in concurrent.futures.as_completed(futures):
                try:
                    res = fut.result()
                    results.append(res)
                except Exception:
                    pass

        results.sort(key=lambda x: x[0])

        text = "🏥 <b>API Diagnostic Status</b>\n\n"
        text += f"<code>{'API Name':<28} {'Status':<14} {'Latency':<8}\n"
        text += f"{'-'*54}\n"
        for name, status, latency in results:
            text += f"{name:<28} {status:<14} {latency}ms\n"
        text += "</code>"

        try:
            b.delete_message(message.chat.id, loading.message_id)
        except Exception:
            pass
        b.send_message(message.chat.id, text, parse_mode="HTML")

    @b.message_handler(commands=["joinchat", "worker_join"])
    def cmd_worker_join(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")
        if not worker_configured():
            return b.reply_to(
                message,
                "❌ Worker account is not configured.\n"
                "Set <code>WORKER_API_ID</code>, <code>WORKER_API_HASH</code>, "
                "<code>WORKER_SESSION</code> and <code>DUMP_CHANNEL_ID</code>.",
                parse_mode="HTML")
        parts = message.text.split()
        if len(parts) < 2:
            return b.reply_to(
                message,
                "ℹ️ <b>Usage:</b> <code>/joinchat &lt;invite link or @username&gt;</code>\n\n"
                "A numeric ID cannot be joined — Telegram needs a link or username.",
                parse_mode="HTML")
        status = b.reply_to(message, "⏳ Joining…")
        ok, why = _run_async(worker_join_link(parts[1])).result(timeout=120)
        b.edit_message_text(
            (f"✅ Worker {why}." if ok else f"❌ Could not join: <code>{_esc(why)}</code>"),
            message.chat.id, status.message_id, parse_mode="HTML")

    @b.message_handler(commands=["worker", "workerstatus"])
    def cmd_worker_status(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")
        if not worker_configured():
            missing = [n for n, v in (("WORKER_API_ID", WORKER_API_ID),
                                      ("WORKER_API_HASH", WORKER_API_HASH),
                                      ("WORKER_SESSION", WORKER_SESSION),
                                      ("DUMP_CHANNEL_ID", DUMP_CHANNEL_ID)) if not v]
            return b.reply_to(
                message,
                "⚪ <b>Worker not configured.</b>\nMissing: <code>"
                + "</code>, <code>".join(missing) + "</code>\n\n"
                "Without it, files over 50MB need each user to <code>/login</code>.",
                parse_mode="HTML")
        status = b.reply_to(message, "⏳ Checking worker…")

        async def _check():
            c = await _get_worker_client()
            if c is None:
                return "❌ Worker session invalid or could not connect."
            me = await c.get_me()
            who = f"@{me.username}" if getattr(me, "username", None) else str(me.id)
            try:
                ent = await c.get_entity(DUMP_CHANNEL_ID)
                dump = f"✅ <code>{_esc(getattr(ent, 'title', DUMP_CHANNEL_ID))}</code>"
            except Exception as e:
                dump = f"❌ cannot reach ({_esc(str(e))})"
            return (f"🟢 <b>Worker online</b>\n\n"
                    f"👤 Account: <code>{_esc(who)}</code>\n"
                    f"🗄 Dump channel: {dump}\n"
                    f"📦 Upload ceiling: <code>{USERBOT_UPLOAD_LIMIT/MB:.0f}MB</code>")

        text = _run_async(_check()).result(timeout=120)
        b.edit_message_text(text, message.chat.id, status.message_id, parse_mode="HTML")

    @b.message_handler(commands=["reset_forward", "resetfwd", "reset"])
    def cmd_reset_forward(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")

        parts = message.text.split()
        if len(parts) < 2:
            return b.reply_to(
                message,
                "ℹ️ <b>Usage:</b> <code>/reset_forward &lt;source_channel&gt;</code>\n\n"
                "Clears the saved forward history for that source so the next "
                "<code>/forward</code> can send its posts again.\n"
                "Example: <code>/reset_forward @my_source_channel</code>",
                parse_mode="HTML",
            )

        src = parts[1]
        try:
            with _db_lock, get_db() as conn:
                cur = conn.execute(
                    "DELETE FROM processed_messages WHERE source=? AND task_type LIKE 'forward%'",
                    (str(src),),
                )
                removed = cur.rowcount or 0
                conn.execute(
                    "DELETE FROM dl_progress WHERE src=? AND job_id LIKE 'fwd_%'",
                    (str(src),),
                )
        except Exception as e:
            return b.reply_to(message, f"❌ Reset failed: <code>{_esc(str(e))}</code>", parse_mode="HTML")

        b.reply_to(
            message,
            f"🧹 <b>Forward history cleared</b> for <code>{_esc(src)}</code>.\n"
            f"🗑 Removed <code>{removed}</code> processed-message record(s).\n\n"
            f"Next <code>/forward</code> from this source starts fresh — at the resume step "
            f"send <code>0</code> to begin from the first message.",
            parse_mode="HTML",
        )

    @b.message_handler(commands=["skipfwd", "skip"])
    def cmd_skip_fwd(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")

        parts = message.text.split()
        if len(parts) < 3:
            return b.reply_to(
                message,
                "ℹ️ <b>Usage:</b>\n"
                "<code>/skipfwd &lt;source_channel&gt; &lt;count&gt;</code>\n\n"
                "Example:\n"
                "<code>/skipfwd @my_source_channel 135</code>",
                parse_mode="HTML"
            )

        src = parts[1]
        try:
            count = int(parts[2])
            if count <= 0:
                raise ValueError()
        except ValueError:
            return b.reply_to(message, "❌ Count must be a positive integer.")

        status = b.send_message(
            message.chat.id,
            "⏳ <b>Initializing userbot connection...</b>",
            parse_mode="HTML"
        )
        _run_async(_skip_fwd_task(message.chat.id, src, count, status.message_id))

    @b.message_handler(commands=["backup"])
    def cmd_backup(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")

        if not os.path.exists("/content"):
            return b.reply_to(message, "⚠️ Bot is not running inside a Google Colab environment.")

        status = b.send_message(message.chat.id, "⏳ <b>Mounting Google Drive and performing backup...</b>", parse_mode="HTML")

        try:
            import glob
            from google.colab import drive  # type: ignore
            if not os.path.exists('/content/drive/MyDrive'):
                drive.mount('/content/drive')
            drive_folder = '/content/drive/MyDrive/TelegramBot_Files'
            os.makedirs(drive_folder, exist_ok=True)

            # Create a timestamped subfolder so we never write over ourselves
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(drive_folder, f"backup_{ts}")
            os.makedirs(backup_dir, exist_ok=True)

            # Scan for all session files in current directory, parent, and /content
            session_files = set()
            for pattern in ['*.session', '../*.session', '/content/*.session', '/content/**/*.session']:
                for filepath in glob.glob(pattern, recursive=True):
                    session_files.add(os.path.abspath(filepath))

            # Scraper state and database files
            files_to_save = list(session_files) + [
                os.path.abspath('.env'),
                os.path.abspath('../.env'),
                os.path.abspath('/content/.env'),
                os.path.abspath(DB_FILE),
                os.path.abspath(STATE_FILE),
                os.path.abspath('allinone_v5.log'),
                os.path.abspath('../allinone_v5.log'),
                os.path.abspath('/content/allinone_v5.log')
            ]

            # Deduplicate paths
            files_to_save = list(set([p for p in files_to_save if os.path.exists(p)]))

            log_lines = []
            copied = skipped = failed = 0
            for file_path in files_to_save:
                src = os.path.abspath(file_path)
                dst = os.path.abspath(os.path.join(backup_dir, os.path.basename(file_path)))

                # Avoid same file error by comparing resolved paths
                if src == dst:
                    log_lines.append(f"ℹ️ <code>{os.path.basename(file_path)}</code> (same path)")
                    skipped += 1
                    continue

                try:
                    # If it's the database file, use SQLite online backup API to ensure WAL sync and prevent corruption
                    if file_path == os.path.abspath(DB_FILE):
                        import sqlite3
                        src_conn = sqlite3.connect(src)
                        dst_conn = sqlite3.connect(dst)
                        with dst_conn:
                            src_conn.backup(dst_conn)
                        dst_conn.close()
                        src_conn.close()
                        log_lines.append(f"✅ <code>{os.path.basename(file_path)}</code> (SQLite Backup)")
                    else:
                        shutil.copy2(src, dst)
                        log_lines.append(f"✅ <code>{os.path.basename(file_path)}</code>")
                    copied += 1
                except Exception as e:
                    log_lines.append(f"❌ <code>{os.path.basename(file_path)}</code>: {e}")
                    failed += 1

            # Auto-prune old backup subfolders (keep last 20)
            try:
                backups = sorted(glob.glob(os.path.join(drive_folder, "backup_*")))
                if len(backups) > 20:
                    to_delete = backups[:-20]
                    for old_dir in to_delete:
                        if os.path.isdir(old_dir):
                            shutil.rmtree(old_dir)
            except Exception:
                pass

            subfolder_name = os.path.basename(backup_dir)
            result_text = (
                f"💾 <b>Google Drive Backup Complete</b>\n"
                f"📂 Saved to folder: <code>{subfolder_name}</code>\n"
                f"📊 Stats: copied={copied}, skipped={skipped}, failed={failed}\n\n"
                + "\n".join(log_lines)
            )
            b.edit_message_text(result_text, message.chat.id, status.message_id, parse_mode="HTML")
        except Exception as e:
            b.edit_message_text(f"❌ <b>Backup failed:</b>\n<code>{_esc(str(e))}</code>", message.chat.id, status.message_id, parse_mode="HTML")

    # ─── /cancel ───────────────────────────────────────────────────
    @b.message_handler(commands=["cancel"])
    def cmd_cancel(message):
        uid = message.from_user.id
        _clear_steps(message.chat.id)
        if uid in _conv:
            _conv.pop(uid)
            b.reply_to(message, "❌ Wizard cancelled.")
        else:
            b.reply_to(message, "ℹ️ Nothing to cancel.")

    def _login_method_kb() -> InlineKeyboardMarkup:
        m = InlineKeyboardMarkup(row_width=1)
        m.add(
            InlineKeyboardButton("📱 1. Phone Number (Quick OTP)", callback_data="login_mode_phone"),
            InlineKeyboardButton("🔑 2. String Session", callback_data="login_mode_string"),
            InlineKeyboardButton("⚙️ 3. Custom API_ID & API_HASH", callback_data="login_mode_custom"),
        )
        return m

    def _clear_steps(chat_id: int) -> None:
        """Drop any pending next-step handlers for this chat so they cannot stack."""
        try:
            b.clear_step_handler_by_chat_id(chat_id)
        except Exception:
            pass

    def _start_login_flow(message):
        _clear_steps(message.chat.id)
        msg = b.send_message(
            message.chat.id,
            "<b>🔐 Select Login Method:</b>\n\n"
            "1️⃣ <b>Phone Number</b> (Quick OTP using default API)\n"
            "2️⃣ <b>String Session</b> (Direct session string)\n"
            "3️⃣ <b>Custom API_ID & API_HASH</b> (Your own app credentials)\n\n"
            "👇 <i>Click a button below or reply with 1, 2, 3 (or send phone number directly):</i>",
            parse_mode="HTML",
            reply_markup=_login_method_kb()
        )
        b.register_next_step_handler(msg, _login_choose_method)

    @b.callback_query_handler(func=lambda c: c.data.startswith("login_mode_"))
    def cb_login_mode(call):
        uid = call.from_user.id
        chat_id = call.message.chat.id
        mode = call.data.replace("login_mode_", "")

        # The menu message already registered _login_choose_method as the next-step
        # handler. Drop it, otherwise BOTH it and the handler we register below fire
        # on the user's next message (double OTP requests, API_ID treated as phone).
        _clear_steps(chat_id)

        existing_creds = _get_user_credentials(uid)
        default_api_id = _API_ID or (existing_creds[0] if existing_creds else None) or 39537854
        default_api_hash = _API_HASH or (existing_creds[1] if existing_creds else None) or "2fdbb71ad7616344cd83195dbfe0625f"

        if mode == "phone":
            _conv[uid] = {
                "mode": "login",
                "api_id": default_api_id,
                "api_hash": default_api_hash
            }
            b.answer_callback_query(call.id)
            msg = b.send_message(
                chat_id,
                "📱 <b>Phone Number Login:</b>\n\n"
                "Please send your phone number with country code (e.g. <code>+919876543210</code>):\n\n"
                "<i>(or send /cancel to abort)</i>",
                parse_mode="HTML"
            )
            b.register_next_step_handler(msg, _login_got_phone)
            return

        elif mode == "string":
            _conv[uid] = {
                "mode": "login_string",
                "api_id": default_api_id,
                "api_hash": default_api_hash
            }
            b.answer_callback_query(call.id)
            msg = b.send_message(
                chat_id,
                "🔑 <b>String Session Login:</b>\n\n"
                "Please paste and send your Telegram StringSession:\n\n"
                "<i>(or send /cancel to abort)</i>",
                parse_mode="HTML"
            )
            b.register_next_step_handler(msg, _login_got_session_string)
            return

        elif mode == "custom":
            _conv[uid] = {"mode": "login"}
            b.answer_callback_query(call.id)
            msg = b.send_message(
                chat_id,
                "⚙️ <b>Custom App Credentials:</b>\n\n"
                "1️⃣ <b>API_ID:</b> Please send your API_ID (get it from my.telegram.org):\n\n"
                "<i>(or send /cancel to abort)</i>",
                parse_mode="HTML"
            )
            b.register_next_step_handler(msg, _login_got_api_id)
            return

    def _login_choose_method(message):
        if _is_cancel(message): return _cancel_conv(b, message)
        text = (message.text or "").strip()
        text_lower = text.lower()
        uid = message.from_user.id

        # A selected StringSession flow must not be reclassified as a phone number.
        if _conv.get(uid, {}).get("mode") == "login_string":
            _login_got_session_string(message)
            return

        existing_creds = _get_user_credentials(uid)
        default_api_id = _API_ID or (existing_creds[0] if existing_creds else None) or 39537854
        default_api_hash = _API_HASH or (existing_creds[1] if existing_creds else None) or "2fdbb71ad7616344cd83195dbfe0625f"

        # Check if the user directly sent a session string
        if len(text) > 100 and not text.startswith("/"):
            _conv[uid] = {
                "mode": "login_string",
                "api_id": default_api_id,
                "api_hash": default_api_hash
            }
            _login_got_session_string(message)
            return

        # Check if the user directly sent a phone number (+91..., 98..., etc.)
        clean_num = re.sub(r"[^\d+]", "", text)
        # Require '+' or >=10 digits so an 8-digit API_ID is never mistaken for a phone.
        if clean_num.startswith("+") or (clean_num.isdigit() and len(clean_num) >= 10):
            _conv[uid] = {
                "mode": "login",
                "api_id": default_api_id,
                "api_hash": default_api_hash
            }
            _login_got_phone(message)
            return

        # Option 1: Phone number (Quick OTP)
        if text_lower in ("1", "phone", "number", "otp", "quick"):
            _conv[uid] = {
                "mode": "login",
                "api_id": default_api_id,
                "api_hash": default_api_hash
            }
            msg = b.send_message(
                message.chat.id,
                "📱 <b>Phone Number Login:</b>\n\n"
                "Please send your phone number with country code (e.g. <code>+919876543210</code>):\n\n"
                "<i>(or send /cancel to abort)</i>",
                parse_mode="HTML"
            )
            b.register_next_step_handler(msg, _login_got_phone)
            return

        # Option 2: String Session
        elif text_lower in ("2", "string", "session", "str"):
            _conv[uid] = {
                "mode": "login_string",
                "api_id": default_api_id,
                "api_hash": default_api_hash
            }
            msg = b.send_message(
                message.chat.id,
                "🔑 <b>String Session Login:</b>\n\n"
                "Please send your Telegram StringSession:\n\n"
                "<i>(or send /cancel to abort)</i>",
                parse_mode="HTML"
            )
            b.register_next_step_handler(msg, _login_got_session_string)
            return

        # Option 3: Custom API_ID + API_HASH
        elif text_lower in ("3", "custom", "api", "hash", "dev"):
            _conv[uid] = {"mode": "login"}
            msg = b.send_message(
                message.chat.id,
                "⚙️ <b>Custom App Credentials:</b>\n\n"
                "1️⃣ <b>API_ID:</b> Please send your API_ID (get it from my.telegram.org):\n\n"
                "<i>(or send /cancel to abort)</i>",
                parse_mode="HTML"
            )
            b.register_next_step_handler(msg, _login_got_api_id)
            return

        else:
            msg = b.send_message(
                message.chat.id,
                "❌ Please click a button or reply with:\n"
                "• <b>1</b> for Phone Number\n"
                "• <b>2</b> for String Session\n"
                "• <b>3</b> for Custom API Hash",
                parse_mode="HTML",
                reply_markup=_login_method_kb()
            )
            b.register_next_step_handler(msg, _login_choose_method)
            return





    def _start_string_login_flow(message):
        uid = message.from_user.id
        _conv[uid] = {"mode": "login_string"}

        tokens = message.text.strip().split()
        passed_tokens = []
        if len(tokens) > 1:
            if tokens[1].lower() in ("string", "session", "str"):
                passed_tokens = tokens[2:]
            else:
                passed_tokens = tokens[1:]

        existing_creds = _get_user_credentials(uid)
        default_api_id = _API_ID or (existing_creds[0] if existing_creds else None)
        default_api_hash = _API_HASH or (existing_creds[1] if existing_creds else None)

        if len(passed_tokens) == 3 and passed_tokens[0].isdigit():
            _conv[uid]["api_id"] = int(passed_tokens[0])
            _conv[uid]["api_hash"] = passed_tokens[1]
            _conv[uid]["session_string"] = passed_tokens[2]
            status = b.send_message(message.chat.id, "⏳ Validating StringSession...", parse_mode="HTML")
            _run_async(_validate_string_session(uid, status.message_id))
            return
        elif len(passed_tokens) == 1 and default_api_id and default_api_hash:
            _conv[uid]["api_id"] = default_api_id
            _conv[uid]["api_hash"] = default_api_hash
            _conv[uid]["session_string"] = passed_tokens[0]
            status = b.send_message(message.chat.id, "⏳ Validating StringSession...", parse_mode="HTML")
            _run_async(_validate_string_session(uid, status.message_id))
            return

        if default_api_id and default_api_hash:
            _conv[uid]["api_id"] = default_api_id
            _conv[uid]["api_hash"] = default_api_hash
            msg = b.send_message(
                message.chat.id,
                f"🔑 <b>API Credentials Auto-Detected</b>\n"
                f"• API_ID: <code>{default_api_id}</code>\n\n"
                "3️⃣ <b>Session String:</b> Please send your Telegram StringSession:\n"
                "<i>(or send /cancel to abort)</i>",
                parse_mode="HTML"
            )
            b.register_next_step_handler(msg, _login_got_session_string)
        else:
            msg = b.send_message(
                message.chat.id,
                "1️⃣ <b>API_ID:</b> Please send your API_ID (get it from my.telegram.org):",
                parse_mode="HTML"
            )
            b.register_next_step_handler(msg, _login_got_api_id)

    async def _login_check_sequence(message) -> None:
        uid = message.from_user.id
        chat_id = message.chat.id

        creds = _get_user_credentials(uid)
        if not creds:
            _start_login_flow(message)
            return

        api_id, api_hash, session_string = creds
        status_msg = _bot_send(chat_id, "🔍 Checking existing session status...")

        if not session_string:
            if status_msg:
                _bot_edit(chat_id, status_msg, "⚠️ No session string stored. Starting login process...")
            _start_login_flow(message)
            return
        client = TelegramClient(
            StringSession(session_string),
            api_id, api_hash,
            connection_retries=3, auto_reconnect=False,
        )
        try:
            await client.connect()
            is_auth = await client.is_user_authorized()
            await client.disconnect()
            if is_auth:
                text = (
                    "✅ <b>You are already logged in!</b>\n"
                    "Your session is active and has not expired.\n\n"
                    "If you want to log in with a different account or re-authenticate, "
                    "please use <code>/login force</code> or <code>/login string</code>."
                )
                if status_msg:
                    _bot_edit(chat_id, status_msg, text)
                else:
                    _bot_send(chat_id, text)
                return
        except Exception as e:
            log.warning(f"Error checking session for {uid}: {e}")
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

        if status_msg:
            try:
                b.delete_message(chat_id, status_msg)
            except Exception:
                pass

        _bot_send(chat_id, "⚠️ Existing session expired or invalid. Starting login process...")
        _start_login_flow(message)

    # ─── /login & /login_string ────────────────────────────────────
    @b.message_handler(commands=["login_string", "string_login", "session_login", "loginsession"])
    def cmd_login_string_direct(message):
        uid = message.from_user.id
        if not is_approved(uid):
            return b.reply_to(message, "⏳ You are not approved yet.")
        _start_string_login_flow(message)

    @b.message_handler(commands=["login"])
    def cmd_login(message):
        uid = message.from_user.id
        if not is_approved(uid):
            return b.reply_to(message, "⏳ You are not approved yet.")

        args = message.text.split()
        if len(args) > 1 and args[1].lower() in ("string", "session", "str"):
            _start_string_login_flow(message)
            return

        force = len(args) > 1 and args[1].lower() == "force"
        if force:
            _start_login_flow(message)
        else:
            _run_async(_login_check_sequence(message))



    def _login_got_api_id(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        _conv[uid]["api_id"] = message.text.strip()
        msg = b.send_message(message.chat.id, "2️⃣ <b>API_HASH:</b> Please send your API_HASH:", parse_mode="HTML")
        b.register_next_step_handler(msg, _login_got_api_hash)

    def _login_got_api_hash(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        _conv[uid]["api_hash"] = message.text.strip()
        if _conv[uid].get("mode") == "login_string":
            msg = b.send_message(message.chat.id, "3️⃣ <b>Session String:</b> Please send your Telegram StringSession:", parse_mode="HTML")
            b.register_next_step_handler(msg, _login_got_session_string)
        else:
            msg = b.send_message(message.chat.id, "3️⃣ <b>Phone Number:</b> Please send your phone number (e.g., +1234567890):", parse_mode="HTML")
            b.register_next_step_handler(msg, _login_got_phone)

    def _login_got_phone(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        raw_phone = message.text.strip()
        phone = re.sub(r"[^\d+]", "", raw_phone)
        if uid not in _conv:
            _conv[uid] = {"mode": "login"}
        if _conv[uid].get("task_running"):
            # A login task is already polling for this user; never start a second
            # one (two send_code_requests invalidate each other's codes).
            return
        _conv[uid]["task_running"] = True
        _conv[uid]["phone"] = phone
        _conv[uid]["otp"] = None
        _conv[uid]["password"] = None

        existing_creds = _get_user_credentials(uid)
        default_api_id = _API_ID or (existing_creds[0] if existing_creds else None) or 39537854
        default_api_hash = _API_HASH or (existing_creds[1] if existing_creds else None) or "2fdbb71ad7616344cd83195dbfe0625f"

        if not _conv[uid].get("api_id"):
            _conv[uid]["api_id"] = default_api_id
        if not _conv[uid].get("api_hash"):
            _conv[uid]["api_hash"] = default_api_hash

        # Send OTP request message and register the next-step handler HERE (sync thread)
        # so pyTelegramBotAPI correctly routes the user's reply to _login_got_otp.
        otp_prompt = b.send_message(
            message.chat.id,
            "📩 <b>Sending OTP to your Telegram app…</b>\n\n"
            "👉 <b>Reply with a SPACE between every digit:</b>\n"
            "<code>1 2 3 4 5</code>\n\n"
            "❌ <code>12345</code> (plain) → Telegram expires it instantly.\n"
            "❌ Forwarding Telegram's message → same.\n\n"
            "(/cancel to abort)",
            parse_mode="HTML"
        )
        _clear_steps(message.chat.id)
        b.register_next_step_handler(otp_prompt, _login_got_otp)
        _run_async(_login_task(message.chat.id, uid, _conv[uid], _login_got_otp, _login_got_2fa_password))

    def _login_got_session_string(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        if uid not in _conv:
            _conv[uid] = {"mode": "login_string"}
        _conv[uid]["session_string"] = message.text.strip()

        existing_creds = _get_user_credentials(uid)
        default_api_id = _API_ID or (existing_creds[0] if existing_creds else None) or 39537854
        default_api_hash = _API_HASH or (existing_creds[1] if existing_creds else None) or "2fdbb71ad7616344cd83195dbfe0625f"

        if not _conv[uid].get("api_id"):
            _conv[uid]["api_id"] = default_api_id
        if not _conv[uid].get("api_hash"):
            _conv[uid]["api_hash"] = default_api_hash

        status = b.send_message(message.chat.id, "⏳ Validating StringSession...", parse_mode="HTML")
        _run_async(_validate_string_session(uid, status.message_id))

    async def _validate_string_session(uid: int, status_msg_id: int) -> None:
        state = _conv.get(uid)
        if not state:
            return
        api_id = state.get("api_id")
        api_hash = state.get("api_hash")
        session_string = state.get("session_string")
        try:
            if api_id is None or api_hash is None or session_string is None:
                raise ValueError("Missing API_ID, API_HASH, or session string.")
            if str(api_id).isdigit():
                api_id = int(api_id)
            client = TelegramClient(StringSession(session_string), api_id, api_hash)
            await client.connect()
            if not await client.is_user_authorized():
                raise RuntimeError("StringSession is not authorized. Please provide a valid session string.")
            save_user_credentials(uid, api_id, api_hash, session_string)
            if bot:
                bot.edit_message_text(
                    "✅ <b>StringSession login successful!</b> Your session has been saved.",
                    uid, status_msg_id, parse_mode="HTML"
                )
        except Exception as e:
            if bot:
                bot.edit_message_text(f"❌ StringSession login failed: {_esc(str(e))}", uid, status_msg_id, parse_mode="HTML")
        finally:
            _conv.pop(uid, None)

    def _login_got_otp(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        # Set OTP for any active login state (mode guard removed — async task already validates)
        state = _conv.get(uid)
        if state is not None:
            state["otp"] = message.text.strip()

    def _login_got_2fa_password(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        # Set 2FA password for any active login state
        state = _conv.get(uid)
        if state is not None:
            state["password"] = message.text.strip()

    # ─── /channels ─────────────────────────────────────────────────
    @b.message_handler(commands=["channels", "chats"])
    def cmd_channels(message):
        status = b.send_message(message.chat.id,
                                "🔍 <b>Fetching channels &amp; groups…</b>",
                                parse_mode="HTML")
        _run_async(_list_chats_task(message.chat.id, status.message_id))

    # ════════════════════════════════════════════════════════════════
    # SCRAPER FLOW
    # ════════════════════════════════════════════════════════════════

    @b.message_handler(commands=["scraper"])
    def cmd_scraper(message):
        uid = message.from_user.id
        _conv[uid] = {"mode": "scraper"}
        msg = b.send_message(
            message.chat.id,
            "📡 <b>Terabox Scraper Setup</b>\n\n"
            "Step 1 / 3 — <b>SOURCE</b> channel:\n"
            + _channel_hint(message.chat.id) +
            "\n\nYou can paste a `https://t.me/channelname` link directly.\n\n*Send /cancel to abort.*",
            parse_mode="HTML",
        )
        b.register_next_step_handler(msg, _scraper_got_src)

    def _scraper_got_src(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        normalized = _normalize_channel_input(message.text or "")
        resolved, label = _resolve_channel(message.chat.id, normalized)
        _conv[uid]["src"]       = resolved
        _conv[uid]["src_label"] = label
        msg = b.send_message(
            message.chat.id,
            "Step 2 / 3 — How many messages to scrape?\n"
            "Send a number (e.g. `50`) or `0`/`all` for unlimited:",
            parse_mode="HTML",
        )
        b.register_next_step_handler(msg, _scraper_got_limit)

    def _scraper_got_limit(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        txt = (message.text or "").strip().lower()
        try:
            lim = int(txt) if txt not in ("0", "all") else 0
            _conv[uid]["scrape_limit"] = lim if lim > 0 else None
        except Exception:
            _conv[uid]["scrape_limit"] = None
        msg = b.send_message(
            message.chat.id,
            "Step 3 / 3 — **DESTINATION** channel:\n" + _channel_hint(message.chat.id),
            parse_mode="HTML",
        )
        b.register_next_step_handler(msg, _scraper_got_dst)

    def _scraper_got_dst(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        state = _conv.pop(uid, {})
        normalized = _normalize_channel_input(message.text or "")
        resolved, label = _resolve_channel(message.chat.id, normalized)
        state["dst"]       = resolved
        state["dst_label"] = label
        b.send_message(
            message.chat.id,
            f"✅ **Scraper starting!**\n"
            f"📤 Source: `{_esc(state['src_label'])}`\n"
            f"📥 Dest:   `{_esc(state['dst_label'])}`\n"
            f"🎯 Limit:  `{state.get('scrape_limit') or 'ALL'}`\n\n"
            "Updates will appear below.\n"
            "Use /pause (ps) /resume (rm) /stop (so) to control.",
            parse_mode="HTML",
        )
        job_clear(message.chat.id)
        _run_async(_scraper_task(message.chat.id, state["src"], state["dst"], state.get("scrape_limit")))

    # ════════════════════════════════════════════════════════════════
    # DOWNLOADER FLOW
    # ════════════════════════════════════════════════════════════════

    @b.message_handler(commands=["download"])
    def cmd_download(message):
        uid = message.from_user.id
        _conv[uid] = {"mode": "download"}
        msg = b.send_message(
            message.chat.id,
            "📥 <b>Media Downloader Setup</b>\n\n"
            "Step 1 / 3 — <b>SOURCE</b> channel:\n" + _channel_hint(message.chat.id) +
            "\n\n<i>Send /cancel to abort.</i>",
            parse_mode="HTML",
        )
        b.register_next_step_handler(msg, _dl_got_src)

    def _dl_got_src(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        resolved, label = _resolve_channel(message.chat.id, message.text or "")
        _conv[uid]["src"]       = resolved
        _conv[uid]["src_label"] = label
        msg = b.send_message(
            message.chat.id,
            "Step 2 / 3 — How many <b>videos</b> to download?\n"
            "Send a number (e.g. <code>20</code>) or <code>0</code>/<code>all</code> for unlimited:",
            parse_mode="HTML",
        )
        b.register_next_step_handler(msg, _dl_got_limit)

    def _dl_got_limit(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        txt = message.text.strip().lower()
        try:
            lim = int(txt) if txt not in ("0", "all") else 0
            _conv[uid]["limit"] = lim if lim > 0 else None
        except ValueError:
            _conv[uid]["limit"] = None
        b.send_message(message.chat.id, "Step 3 / 3 — What to download?",
                       reply_markup=_media_type_kb("mt"))

    @b.callback_query_handler(func=lambda c: c.data.startswith("mt_"))
    def cb_dl_media_type(call):
        uid = call.from_user.id
        if uid not in _conv or _conv[uid].get("mode") != "download":
            return b.answer_callback_query(call.id, "No active download session.")
        photo, video, audio, doc = _parse_media_choice(call.data)
        state = _conv.pop(uid, {})
        b.answer_callback_query(call.id, "✅ Starting download!")
        status_msg = b.edit_message_text(
            f"✅ <b>Download started!</b>\n"
            f"📡 Source: <code>{_esc(state.get('src_label', state['src']))}</code>\n"
            f"📊 Limit:  <code>{state['limit'] or 'ALL'}</code>\n"
            f"🖼 Photos: {'✅' if photo else '❌'}  "
            f"🎬 Videos: {'✅' if video else '❌'}  "
            f"🎵 Audio: {'✅' if audio else '❌'}  "
            f"📄 Docs: {'✅' if doc else '❌'}\n\n"
            "📥 Downloading… updates will appear below.\n"
            "Use /pause (ps) /resume (rm) /stop (so) to control.",
            call.message.chat.id, call.message.message_id,
            parse_mode="HTML",
        )
        status_msg_id = getattr(status_msg, 'message_id', None)
        job_clear(call.message.chat.id)
        _run_async(_downloader_task(
            call.message.chat.id, state["src"],
            state.get("src_label", state["src"]),
            state["limit"], photo, video, audio, doc,
            status_msg_id or 0,
        ))

    # ════════════════════════════════════════════════════════════════
    # GDRIVE LEECH FLOW (Custom Integration)
    # ════════════════════════════════════════════════════════════════

    @b.message_handler(commands=["gdrive_leech"])
    def cmd_gdrive_leech(message):
        uid = message.from_user.id
        status_msg = b.send_message(
            message.chat.id,
            "🚀 <b>Starting GDrive Leech...</b>\n"
            "This will download specific files to your Google Drive and extract passwords.",
            parse_mode="HTML"
        )
        _run_async(_gdrive_leech_task(message.chat.id, status_msg.message_id))

    # ════════════════════════════════════════════════════════════════
    # FORWARDER FLOW
    # ════════════════════════════════════════════════════════════════

    @b.message_handler(commands=["forward"])
    def cmd_forward(message):
        uid = message.from_user.id
        _conv[uid] = {"mode": "forward"}
        msg = b.send_message(
            message.chat.id,
            "🔁 <b>Media Forwarder Setup</b>\n\n"
            "Direction: <b>NEW channel → OLD channel</b>\n"
            "(Media from NEW is uploaded into OLD)\n\n"
            "Step 1 / 5 — <b>SOURCE (NEW channel)</b>:\n" + _channel_hint(message.chat.id) +
            "\n\n<i>Send /cancel to abort.</i>",
            parse_mode="HTML",
        )
        b.register_next_step_handler(msg, _fwd_got_src)

    def _fwd_got_src(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        resolved, label = _resolve_channel(message.chat.id, message.text or "")
        _conv[uid]["src"]       = resolved
        _conv[uid]["src_label"] = label
        msg = b.send_message(
            message.chat.id,
            "Step 2 / 5 — <b>DESTINATION (OLD channel)</b>:\n" + _channel_hint(message.chat.id),
            parse_mode="HTML",
        )
        b.register_next_step_handler(msg, _fwd_got_dst)

    def _fwd_got_dst(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        resolved, label = _resolve_channel(message.chat.id, message.text or "")
        _conv[uid]["dst"]       = resolved
        _conv[uid]["dst_label"] = label
        msg = b.send_message(
            message.chat.id,
            "Step 3 / 5 — How many messages to scan?\n"
            "Send <code>0</code> or <code>all</code> for unlimited:",
            parse_mode="HTML",
        )
        b.register_next_step_handler(msg, _fwd_got_limit)

    def _fwd_got_limit(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        state = _conv.get(uid)
        if not state or state.get("mode") != "forward":
            b.send_message(message.chat.id, "This forward session expired. Send /forward to start again.")
            return

        txt = (message.text or "").strip().lower()
        if txt in ("0", "all"):
            state["limit"] = None
        elif txt.isdigit() and int(txt) > 0:
            state["limit"] = int(txt)
        else:
            msg = b.send_message(
                message.chat.id,
                "Please send a positive number, <code>0</code>, or <code>all</code>:",
                parse_mode="HTML",
            )
            b.register_next_step_handler(msg, _fwd_got_limit)
            return
        msg = b.send_message(
            message.chat.id,
            "Step 4 / 5 — <b>Resume point</b>\n\n"
            "Send the <b>last forwarded Msg ID</b> (e.g. <code>27078</code>) to continue right after it. "
            "Everything after that ID is re-sent even if an earlier run already forwarded it.\n\n"
            "Send <code>0</code> or <code>skip</code> to use the saved checkpoint, "
            "or start from the first message if there is none.\n\n"
            "<i>Tip: the previous run's status / completion message shows 🔖 Last msg ID.</i>",
            parse_mode="HTML",
        )
        b.register_next_step_handler(msg, _fwd_got_start_id)

    def _fwd_got_start_id(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        state = _conv.get(uid)
        if not state or state.get("mode") != "forward":
            b.send_message(message.chat.id, "This forward session expired. Send /forward to start again.")
            return

        txt = (message.text or "").strip().lower()
        m = re.search(r"(\d+)\s*/?\s*$", txt)   # accepts "27078", "#27078", "https://t.me/c/…/27078"
        if txt in ("", "0", "skip", "no", "none", "auto"):
            state["start_after"] = 0
        elif m:
            state["start_after"] = int(m.group(1))
        else:
            msg = b.send_message(
                message.chat.id,
                "Please send a message ID (a number), or <code>0</code> / <code>skip</code>:",
                parse_mode="HTML",
            )
            b.register_next_step_handler(msg, _fwd_got_start_id)
            return
        b.send_message(message.chat.id, "Step 5 / 5 — What to forward?",
                       reply_markup=_media_type_kb("ft"))

    @b.callback_query_handler(func=lambda c: c.data.startswith("ft_"))
    def cb_fwd_media_type(call):
        uid = call.from_user.id
        if uid not in _conv or _conv[uid].get("mode") != "forward":
            return b.answer_callback_query(call.id, "No active forward session.")
        photo, video, audio, doc = _parse_media_choice(call.data)
        _conv[uid].update(fwd_photo=photo, fwd_video=video, fwd_audio=audio, fwd_doc=doc,
                          mode="forward_cap")
        b.answer_callback_query(call.id)
        b.edit_message_text("📝 Caption handling for forwarded messages:",
                            call.message.chat.id, call.message.message_id,
                            reply_markup=_caption_kb())

    @b.callback_query_handler(func=lambda c: c.data.startswith("cap_"))
    def cb_caption(call):
        uid = call.from_user.id
        if uid not in _conv or _conv[uid].get("mode") != "forward_cap":
            return b.answer_callback_query(call.id, "No active session.")
        if call.data == "cap_prefix":
            b.answer_callback_query(call.id)
            _conv[uid]["mode"] = "forward_prefix"
            msg = b.send_message(call.message.chat.id,
                                 "Send the prefix text (prepended to every caption):")
            b.register_next_step_handler(msg, _fwd_got_prefix)
        else:
            _conv[uid]["cap_mode"]   = "keep" if call.data == "cap_keep" else "clear"
            _conv[uid]["cap_prefix"] = ""
            b.answer_callback_query(call.id, "✅")
            _launch_forwarder(uid, call.message.chat.id, call.message.message_id)

    def _fwd_got_prefix(message):
        uid = message.from_user.id
        if _is_cancel(message): return _cancel_conv(b, message)
        _conv[uid]["cap_mode"]   = "prefix"
        _conv[uid]["cap_prefix"] = message.text.strip() + "\n\n"
        _launch_forwarder(uid, message.chat.id, None)

    def _launch_forwarder(uid: int, chat_id: int, edit_msg_id: Optional[int]):
        state   = _conv.pop(uid, {})
        summary = (
            f"✅ <b>Forwarder starting!</b>\n"
            f"📤 Source: <code>{_esc(state['src'])}</code>\n"
            f"📥 Dest:   <code>{_esc(state['dst'])}</code>\n"
            f"📊 Limit:  <code>{state['limit'] or 'ALL'}</code>\n"
            f"🖼 Photos: {'✅' if state['fwd_photo'] else '❌'}  "
            f"🎬 Videos: {'✅' if state['fwd_video'] else '❌'}\n"
            f"🎵 Audio:  {'✅' if state['fwd_audio'] else '❌'}  "
            f"📄 Docs:   {'✅' if state['fwd_doc'] else '❌'}\n"
            f"📝 Captions: <code>{_esc(state['cap_mode'])}</code>\n"
            f"🔖 Resume after: <code>{state.get('start_after') or 'auto (checkpoint / first message)'}</code>\n\n"
            "Use /pause (ps) /resume (rm) /stop (so) to control."
        )
        if bot:
            try:
                if edit_msg_id is not None:
                    bot.edit_message_text(summary, chat_id, edit_msg_id, parse_mode="HTML")
                else:
                    bot.send_message(chat_id, summary, parse_mode="HTML")
            except Exception:
                if edit_msg_id is not None:
                    bot.send_message(chat_id, summary, parse_mode="HTML")

        job_clear(chat_id)
        _run_async(_forwarder_task(
            chat_id,
            state["src"], state["dst"], state["limit"],
            state["fwd_photo"], state["fwd_video"],
            state["fwd_audio"], state["fwd_doc"],
            state["cap_mode"], state.get("cap_prefix", ""),
            state.get("start_after", 0) or 0,
        ))

    # ─── Terabox TXT file handler (Bulk Upload) ─────────────────
    @b.message_handler(content_types=["document"])
    def handle_document(message):
        uid = message.from_user.id
        if uid in _conv:
            return
        if is_banned(uid):
            return b.reply_to(message, "🚫 You are banned.")
        if not is_approved(uid):
            return b.reply_to(message, "⏳ You are not approved yet. Send /start to request access.")

        doc = message.document
        if not doc.file_name.lower().endswith(".txt"):
            return b.reply_to(message, "⚠️ Please send a .txt file containing Terabox links.")

        status_msg = b.reply_to(message, "🔄 Downloading your text file...")
        try:
            file_info = b.get_file(doc.file_id)
            downloaded_file = b.download_file(file_info.file_path)
            content = downloaded_file.decode('utf-8', errors='ignore')

            links = []
            for line in content.splitlines():
                line = line.strip()
                if line and is_terabox_url(line):
                    links.append(line)

            if not links:
                b.edit_message_text("⚠️ No valid Terabox links found in the text file.", message.chat.id, status_msg.message_id)
                return

            b.edit_message_text(f"✅ Found {len(links)} Terabox links! Starting to process them in memory...", message.chat.id, status_msg.message_id)

            def process_txt_links():
                for idx, link in enumerate(links):
                    try:
                        b.send_message(message.chat.id, f"🔄 Processing {idx+1}/{len(links)}: <code>{_esc(link)}</code>", parse_mode="HTML")

                        # 1. Extract metadata
                        result = extract_terabox_sync(link)
                        if not result or not result.get("download"):
                            b.send_message(message.chat.id, f"❌ Failed to extract link {idx+1}")
                            continue

                        text = build_result_message(result)
                        download_url = result.get("download")
                        filename = result.get("filename", f"video_{idx+1}.mp4")
                        duration = _duration_seconds(result.get("duration"))
                        width = int(result.get("width") or 0)
                        height = int(result.get("height") or 0)
                        thumb_buf = _fetch_thumb(result.get("thumb") or "")
                        size = _parse_size_bytes(result.get("size") or result.get("size_human"))
                        if not size:
                            try:
                                head_r = requests.head(download_url, allow_redirects=True, timeout=15)
                                cl = head_r.headers.get("Content-Length")
                                if cl and cl.isdigit():
                                    size = int(cl)
                            except Exception:
                                size = 0

                        timeout = _send_timeout_for_size(size)

                        # 2. Download strictly to Memory (RAM)
                        video_buf = BytesIO()
                        try:
                            headers = {"User-Agent": HEADERS.get("user-agent", ""), "Referer": "https://www.terabox.com/"}
                            r = requests.get(download_url, headers=headers, stream=True, timeout=120)
                            if r.status_code == 403:
                                log.info("[txt proc] Got 403 with Referer. Retrying without Referer...")
                                headers.pop("Referer", None)
                                r = requests.get(download_url, headers=headers, stream=True, timeout=120)
                            with r:
                                r.raise_for_status()
                                for chunk in r.iter_content(chunk_size=1024*1024):
                                    if chunk:
                                        video_buf.write(chunk)

                            video_buf.seek(0)
                            video_buf.name = filename

                        except Exception as e:
                            b.send_message(message.chat.id, f"❌ Failed to download {idx+1} to memory: {e}")
                            continue

                        # 3. Send directly to Telegram as video
                        try:
                            b.send_video(
                                message.chat.id,
                                video=video_buf,
                                caption=text,
                                parse_mode="HTML",
                                duration=duration or None,
                                width=width or None,
                                height=height or None,
                                thumb=thumb_buf,
                                supports_streaming=True,
                                timeout=timeout
                            )
                        except Exception as e:
                            b.send_message(message.chat.id, f"❌ Failed to send video {idx+1}: {e}")
                        finally:
                            video_buf.close()
                            if thumb_buf:
                                thumb_buf.close()

                        time.sleep(2)

                    except Exception as loop_e:
                        log.warning(f"[TXT processor loop error]: {loop_e}")

                b.send_message(message.chat.id, "🎉 Finished processing all links from the text file!")

            # Run in a background thread to not block the bot
            threading.Thread(target=process_txt_links, daemon=True).start()

        except Exception as e:
            b.edit_message_text(f"❌ Error processing document: {e}", message.chat.id, status_msg.message_id)

    # ─── /mega /megadl /mage command handler ───────────────────────
    @b.message_handler(commands=["mega", "mage", "megadl"])
    def cmd_mega(message):
        uid = message.from_user.id
        if uid in _conv:
            return
        if is_banned(uid):
            return b.reply_to(message, "🚫 You are banned.")
        if not is_approved(uid):
            return b.reply_to(message, "⏳ You are not approved yet. Send /start to request access.")

        text = message.text.strip()
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            message.text = parts[1].strip()
            return handle_link(message)

        b.reply_to(
            message,
            "📥 <b>Mega Cloud Downloader & Streamer:</b>\n\n"
            "Simply send any <b>Mega.nz</b> file or folder link:\n\n"
            "• <code>https://mega.nz/file/xxxx#key</code>\n"
            "• <code>https://mega.nz/folder/xxxx#key</code>\n\n"
            "<i>No command required — you can also just paste the link directly in chat!</i>",
            parse_mode="HTML"
        )

    # ─── Terabox & Mega link handler (catch-all text) ──────────────
    @b.message_handler(func=lambda m: True, content_types=["text"])
    def handle_link(message):
        uid = message.from_user.id
        if uid in _conv:
            return
        if is_banned(uid):
            return b.reply_to(message, "🚫 You are banned.")
        if not is_approved(uid):
            return b.reply_to(message, "⏳ You are not approved yet. Send /start to request access.")
        upsert_user(uid, message.from_user.username or "", message.from_user.first_name or "")
        text = message.text.strip()
        mega_links = extract_mega_links(text)
        if text.startswith("/"):
            parts = text.split(maxsplit=1)
            cmd = parts[0].lower()
            if cmd in ("/mega", "/mage", "/megadl") and len(parts) > 1:
                text = parts[1].strip()
                mega_links = extract_mega_links(text)
            elif not mega_links:
                return
        url = text
        # Mega.nz Link Handler
        if mega_links or is_mega_url(text):
            mega_target_url = mega_links[0] if mega_links else text.strip()
            allowed, wait = check_rate_limit(uid)
            if not allowed:
                mins, secs = divmod(wait, 60)
                return b.reply_to(
                    message,
                    f"⏳ Rate limit reached! Try again in <code>{mins}m {secs}s</code>.\n\n"
                    f"💎 Get unlimited access with /premium",
                    parse_mode="HTML"
                )

            premium_badge = " 💎" if is_premium(uid) else ""
            status = b.reply_to(message, f"⏳ <b>Connecting to Mega Cloud Engine…</b>{premium_badge}", parse_mode="HTML")

            def do_mega():
                try:
                    b.edit_message_text("🔍 <b>Fetching Mega file metadata & decrypting keys…</b>",
                                        message.chat.id, status.message_id, parse_mode="HTML")
                    res = process_mega_link_sync(mega_target_url)
                    increment_links(uid)
                    save_history(uid, mega_target_url, res)
                    send_mega_result(message.chat.id, res, status_msg_id=status.message_id)
                except Exception as e:
                    log.error(f"[mega extraction] {e}")
                    try:
                        b.edit_message_text(f"❌ <b>Mega Error:</b> <code>{_esc(str(e))}</code>",
                                            message.chat.id, status.message_id, parse_mode="HTML")
                    except Exception:
                        pass

            enqueue_extraction(do_mega)
            return

        # ── Any other http(s) link: fetch it directly (no third-party API) ──
        if not is_terabox_url(url):
            if not url.lower().startswith("http"):
                return b.reply_to(
                    message,
                    "❓ Please send a valid link.\n\n"
                    "Supported:\n"
                    "• <b>Terabox</b> — <code>https://terabox.com/s/xxxxx</code>\n"
                    "• <b>Mega.nz</b> — <code>https://mega.nz/file/xxxxx#key</code>\n"
                    "• <b>Google Drive</b> — <code>https://drive.google.com/file/d/xxxxx/view</code>\n"
                    "• Any <b>direct file link</b> — <code>https://site.com/video.mp4</code>",
                    parse_mode="HTML",
                )

            allowed, wait = check_rate_limit(uid)
            if not allowed:
                mins, secs = divmod(wait, 60)
                return b.reply_to(
                    message,
                    f"⏳ Rate limit reached! Try again in <code>{mins}m {secs}s</code>.\n\n"
                    f"💎 Get unlimited access with /premium",
                    parse_mode="HTML",
                )

            target = _gdrive_direct_url(url) if is_gdrive_url(url) else url
            label  = "Google Drive" if is_gdrive_url(url) else "Direct link"
            if target is None:
                return b.reply_to(
                    message,
                    "❌ Could not read a file ID from that Google Drive link.\n"
                    "Use the <b>share</b> link, e.g. "
                    "<code>https://drive.google.com/file/d/FILE_ID/view</code>",
                    parse_mode="HTML",
                )

            premium_badge = " 💎" if is_premium(uid) else ""
            status = b.reply_to(message, f"🔗 <b>Checking {label}…</b>{premium_badge}", parse_mode="HTML")

            def do_direct():
                try:
                    info = probe_direct_link(target)
                    fname = info["filename"]
                    size  = info["size"]
                    _, type_label = _detect_file_category(fname)
                    head = (f"✅ <b>{label} ready!</b>\n\n"
                            f"📂 <b>File:</b> <code>{_esc(fname)}</code>\n"
                            f"🏷 <b>Type:</b> <code>{type_label}</code>\n"
                            f"📦 <b>Size:</b> <code>{_esc(info['size_human'])}</code>")

                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton("⬇️ Download", url=info["download"]))

                    # A bot token tops out at 50MB. The shared worker account
                    # reaches 2GB for everyone; a personal login is the fallback
                    # when no worker is configured.
                    has_worker   = worker_configured()
                    has_userbot  = has_worker or bool(_get_user_credentials(uid))
                    cap = USERBOT_UPLOAD_LIMIT if has_userbot else BOT_UPLOAD_LIMIT

                    if size > cap:
                        hint = ("" if has_userbot else
                                "\n💡 <code>/login</code> raises this to 2GB.")
                        b.edit_message_text(
                            head + f"\n\n⚠️ Over the {cap/MB:.0f}MB upload limit.{hint}"
                                   "\n📥 Tap the button below.",
                            message.chat.id, status.message_id,
                            parse_mode="HTML", reply_markup=markup)
                        increment_links(uid)
                        save_history(uid, url, info)
                        return

                    # Some hosts omit Content-Length. Rather than refuse, pull the
                    # file with a hard cap and fall back to the link if it trips.
                    dl_prog = TransferProgress(
                        message.chat.id, status.message_id,
                        "📥 <b>Downloading…</b>", fname, total=size)
                    dl_prog.update(0, force=True)
                    try:
                        path = _download_to_tempfile_sync(
                            info["download"], fname, timeout=600,
                            max_bytes=cap, referer=None, progress=dl_prog)
                    except FileTooLargeError:
                        hint = ("" if has_userbot else
                                "\n💡 <code>/login</code> raises this to 2GB.")
                        b.edit_message_text(
                            head + f"\n\n⚠️ Bigger than {cap/MB:.0f}MB — too large to upload.{hint}"
                                   "\n📥 Tap the button below.",
                            message.chat.id, status.message_id,
                            parse_mode="HTML", reply_markup=markup)
                        increment_links(uid)
                        save_history(uid, url, info)
                        return
                    if not path:
                        b.edit_message_text(head + "\n\n❌ Download failed — try the button below.",
                                            message.chat.id, status.message_id,
                                            parse_mode="HTML", reply_markup=markup)
                        return
                    try:
                        real_size = os.path.getsize(path)
                        if real_size <= BOT_UPLOAD_LIMIT:
                            b.edit_message_text(
                                f"📤 <b>Uploading to Telegram…</b>\n\n<code>{_esc(fname)}</code>",
                                message.chat.id, status.message_id, parse_mode="HTML")
                            okay = _send_file_by_type(b, message.chat.id, path, fname, head,
                                                      timeout=_send_timeout_for_size(real_size))
                            if okay:
                                increment_links(uid)
                                save_history(uid, url, info)
                                try: b.delete_message(message.chat.id, status.message_id)
                                except Exception: pass
                            else:
                                b.edit_message_text(head + "\n\n❌ Upload failed — use the button below.",
                                                    message.chat.id, status.message_id,
                                                    parse_mode="HTML", reply_markup=markup)
                        elif has_worker:
                            # Worker uploads to the dump channel, bot copies it here.
                            took = dl_prog.elapsed()
                            ok_up, why = _run_async(
                                worker_deliver_file(uid, path, fname, head,
                                                    status.message_id)
                            ).result(timeout=7200)
                            if ok_up:
                                increment_links(uid)
                                save_history(uid, url, info)
                                b.edit_message_text(
                                    f"✅ <b>Done!</b>\n\n"
                                    f"📂 <code>{_esc(fname)}</code>\n"
                                    f"📦 {human_size(real_size)}\n"
                                    f"⏱ Downloaded in {_fmt_eta(took)}",
                                    message.chat.id, status.message_id, parse_mode="HTML")
                            else:
                                b.edit_message_text(
                                    head + f"\n\n❌ Upload failed: <code>{_esc(why)}</code>"
                                           "\n📥 Use the button below.",
                                    message.chat.id, status.message_id,
                                    parse_mode="HTML", reply_markup=markup)
                        else:
                            # No worker — fall back to the user's own account.
                            ok_up, why = _run_async(
                                _userbot_upload_file(uid, path, fname, head)
                            ).result(timeout=3600)
                            if ok_up:
                                increment_links(uid)
                                save_history(uid, url, info)
                                b.edit_message_text(
                                    head + f"\n\n✅ Sent to your <b>Saved Messages</b> "
                                           f"({human_size(real_size)}).",
                                    message.chat.id, status.message_id,
                                    parse_mode="HTML", reply_markup=markup)
                            else:
                                b.edit_message_text(
                                    head + f"\n\n❌ Userbot upload failed: <code>{_esc(why)}</code>"
                                           "\n📥 Use the button below.",
                                    message.chat.id, status.message_id,
                                    parse_mode="HTML", reply_markup=markup)
                    finally:
                        _clean_file(path)
                except Exception as e:
                    log.error(f"[direct link] {e}")
                    try:
                        b.edit_message_text(f"❌ <b>Error:</b> {_esc(str(e))}",
                                            message.chat.id, status.message_id, parse_mode="HTML")
                    except Exception:
                        pass

            enqueue_extraction(do_direct)
            return

        allowed, wait = check_rate_limit(uid)
        if not allowed:
            mins, secs = divmod(wait, 60)
            return b.reply_to(
                message,
                f"⏳ Rate limit reached! Try again in <code>{mins}m {secs}s</code>.\n\n"
                f"💎 Get unlimited access with /premium",
                parse_mode="HTML",
            )

        premium_badge = " 💎" if is_premium(uid) else ""
        status = b.reply_to(message, f"⏳ Extracting…{premium_badge}")

        def do():
            try:
                b.edit_message_text("🔍 <b>Fetching file info…</b>",
                                    message.chat.id, status.message_id, parse_mode="HTML")
                res = extract_terabox_sync(url)
                if not res:
                    raise RuntimeError("Extraction returned no data.")
                increment_links(uid)
                save_history(uid, url, res)
                send_result(message.chat.id, res, status_msg_id=status.message_id)
            except Exception as e:
                log.error(f"[bot extraction] {e}")
                try:
                    b.edit_message_text(f"❌ <b>Error:</b> <code>{_esc(str(e))}</code>",
                                        message.chat.id, status.message_id, parse_mode="HTML")
                except Exception:
                    pass

        # Queue the task; tell the user their position if they have to wait
        pos = enqueue_extraction(do)
        if pos > 1:
            try:
                premium_msg = " (Premium users skip queue)" if is_premium(uid) else ""
                b.edit_message_text(
                    f"📋 <b>Queued!</b> Position <b>{pos}</b> in line.{premium_msg}\n"
                    "You'll get your result as soon as the workers are free.",
                    message.chat.id, status.message_id, parse_mode="HTML"
                )
            except Exception:
                pass

    # ─── /checkpoint ──────────────────────────────────────────────
    @b.message_handler(commands=["checkpoint"])
    def cmd_checkpoint(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")

        parts = message.text.split()
        if len(parts) == 1:
            # Show list of checkpoints
            text = "🔖 <b>Current Checkpoints</b>\n\n"

            # Scraper checkpoints
            state = load_scraper_state()
            text += "📡 <b>Scraper Checkpoints (state.json):</b>\n"
            if not state:
                text += "  <i>No scraper checkpoints found.</i>\n"
            for key, val in state.items():
                text += f"  • <code>{_esc(key)}</code>: Msg ID <code>{val.get('resume_id', 0)}</code>\n"

            # Downloader checkpoints
            text += "\n📥 <b>Downloader Checkpoints (Database):</b>\n"
            try:
                with get_db() as conn:
                    rows = conn.execute("""
                        SELECT src_label, src, MAX(last_msg_id) as max_id, SUM(downloaded) as total_dl
                        FROM dl_progress
                        GROUP BY src
                    """).fetchall()
                if not rows:
                    text += "  <i>No downloader checkpoints found.</i>\n"
                for r in rows:
                    text += f"  • <code>{_esc(r['src_label'] or r['src'])}</code>: Msg ID <code>{r['max_id']}</code> (Total DL: {r['total_dl']})\n"
            except Exception as e:
                text += f"  ❌ Error reading DB: {e}\n"

            text += "\n✍️ <b>To set a checkpoint manually:</b>\n"
            text += "<code>/checkpoint &lt;channel_id_or_username&gt; &lt;msg_id&gt;</code>"
            b.reply_to(message, text, parse_mode="HTML")
            return

        if len(parts) < 3:
            return b.reply_to(message, "ℹ️ <b>Usage:</b>\n<code>/checkpoint &lt;channel_id_or_username&gt; &lt;msg_id&gt;</code>", parse_mode="HTML")

        target = parts[1]
        try:
            msg_id = int(parts[2])
        except ValueError:
            return b.reply_to(message, "❌ Message ID must be an integer.")

        # 1. Update scraper state if exists
        state = load_scraper_state()
        updated_scraper = False
        for key in list(state.keys()):
            if target.lower() in key.lower() or target.replace("-100", "") in key:
                state[key]["resume_id"] = msg_id
                save_scraper_state(state)
                updated_scraper = True

        # 2. Update downloader progress table
        updated_downloader = False
        try:
            with _db_lock, get_db() as conn:
                row = conn.execute("SELECT job_id FROM dl_progress WHERE src LIKE ? OR src_label LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%{target}%", f"%{target}%")).fetchone()
                if row:
                    conn.execute("UPDATE dl_progress SET last_msg_id=? WHERE job_id=?", (msg_id, row["job_id"]))
                    updated_downloader = True
                else:
                    job_id = f"dl_manual_{int(time.time())}"
                    conn.execute("INSERT INTO dl_progress (job_id, chat_id, src, src_label, last_msg_id, state) VALUES (?, ?, ?, ?, ?, 'stopped')",
                                 (job_id, message.chat.id, target, target, msg_id))
                    updated_downloader = True
        except Exception as e:
            log.error(f"[checkpoint] DB update failed: {e}")

        if updated_scraper or updated_downloader:
            b.reply_to(message, f"✅ Checkpoint for <code>{_esc(target)}</code> successfully set to Msg ID <code>{msg_id}</code>.", parse_mode="HTML")
        else:
            b.reply_to(message, f"❌ Channel <code>{_esc(target)}</code> not found in scraper state or database.", parse_mode="HTML")

    # ─── /db_unlock ───────────────────────────────────────────────
    @b.message_handler(commands=["db_unlock", "unlock"])
    def cmd_db_unlock(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")

        status = b.reply_to(message, "⏳ <b>Starting database unlock procedure...</b>", parse_mode="HTML")

        # 1. Vacuum and checkpoint DB to flush WAL logs & release internal locks
        db_cleaned = False
        db_err = ""
        try:
            with _db_lock, get_db() as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                conn.execute("VACUUM;")
                db_cleaned = True
        except Exception as e:
            db_err = str(e)

        # 2. Find and kill duplicate process instances running main.py / maon.py
        import subprocess
        import os
        import json

        my_pid = os.getpid()
        killed_pids = []

        try:
            cmd = 'powershell -Command "Get-CimInstance Win32_Process -Filter \\"Name LIKE \'python%\' AND (CommandLine LIKE \'%main.py%\' OR CommandLine LIKE \'%maon.py%\')\\" | Select-Object ProcessId, CommandLine | ConvertTo-Json"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                try:
                    data = json.loads(res.stdout)
                    if not isinstance(data, list):
                        data = [data]
                    for proc in data:
                        pid = proc.get("ProcessId")
                        if pid and pid != my_pid:
                            subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                            killed_pids.append(pid)
                except Exception as parse_err:
                    log.warning(f"[db_unlock] Process parse error: {parse_err}")
        except Exception as proc_err:
            log.warning(f"[db_unlock] Process search error: {proc_err}")

        response = "🔓 <b>Database Unlock Status</b>\n\n"
        if db_cleaned:
            response += "✅ WAL Checkpoint & VACUUM successful.\n"
        else:
            response += f"⚠️ DB Clean Error: <code>{_esc(db_err)}</code> (DB file might still be locked)\n"

        if killed_pids:
            response += f"✅ Terminated <code>{killed_pids}</code> duplicate process(es).\n"
        else:
            response += "ℹ️ No duplicate python bot instances detected.\n"

        b.edit_message_text(response, message.chat.id, status.message_id, parse_mode="HTML")

    # ─── /kill ────────────────────────────────────────────────────
    @b.message_handler(commands=["kill"])
    def cmd_kill(message):
        if not _is_lx_auth(message.from_user.id):
            return b.reply_to(message, "⛔ Admin only.")

        b.reply_to(message, "💀 <b>Stopping all active jobs, clearing extraction queues, and killing bot process...</b>\n\n<i>If configured under a process manager, the bot should restart automatically.</i>", parse_mode="HTML")

        # 1. Stop all active jobs in memory
        for cid in list(_job_control.keys()):
            _job_control[cid] = "stop"

        # 2. Clear extraction worker queue
        try:
            with _extract_queue.mutex:
                _extract_queue.queue.clear()
        except Exception:
            pass

        # 3. Brief wait and exit
        time.sleep(1.5)
        os._exit(0)


# ── Conversation helpers ──────────────────────────────────────────────

def _is_cancel(message) -> bool:
    return bool(message.text and message.text.strip().startswith("/cancel"))


def _cancel_conv(b, message) -> None:
    _conv.pop(message.from_user.id, None)
    try:
        b.clear_step_handler_by_chat_id(message.chat.id)
    except Exception:
        pass
    b.reply_to(message, "❌ Operation cancelled.")


def _channel_hint(chat_id: int) -> str:
    tail = ("\n💡 Not a member yet? Send the <b>invite link</b> or <b>@username</b> "
            "and it will be joined automatically (a numeric ID cannot be joined).")
    if _chat_cache.get(chat_id):
        return ("Enter the <b>row number</b> from the list, @username, invite link, "
                "or chat ID." + tail)
    return ("Enter @username, an invite link, or a chat ID. "
            "Run /channels first to pick by number." + tail)


def _resolve_channel(chat_id: int, text: str) -> tuple[str, str]:
    """
    Resolve user input → (value_for_telethon, display_label).
    Accepts row number, raw ID (with or without -100 prefix), or @username.
    """
    text  = text.strip()
    cache = _chat_cache.get(chat_id, [])

    # Row number (1-based)
    if text.lstrip("-").isdigit():
        idx = int(text) - 1
        if cache and 0 <= idx < len(cache):
            c     = cache[idx]
            ident = str(c["id"])
            label = f"{c['title']} ({c['username'] if not c['private'] else ident})"
            return ident, label
        # Raw numeric ID — pass as-is; resolve_entity handles -100 prefix
        return text, text

    clean = text.lstrip("@")
    return clean, f"@{clean}"


# ══════════════════════════════════════════════════════════════════════
# SECTION 12 — RUN BOT
# ══════════════════════════════════════════════════════════════════════

def run_bot() -> None:
    global bot

    if BOT_TOKEN in ("YOUR_BOT_TOKEN", "", None):
        log.error("[Bot] BOT_TOKEN is a placeholder — set a real token.")
        return

    if not _validate_bot_token(BOT_TOKEN, retries=3):
        log.error("[Bot] Token validation failed.")
        log.error("[Bot] Possible causes:")
        log.error("  1. Internet connection issue (network timeout)")
        log.error("  2. Invalid BOT_TOKEN")
        log.error("  3. Telegram API temporarily unavailable")
        log.error("  4. ISP/region blocking Telegram")
        return

    bot = _make_bot()
    try:
        bot.set_my_commands([
            BotCommand("start", "Dashboard & main menu"),
            BotCommand("help", "Full command reference"),
            BotCommand("login", "Connect your Telegram account"),
            BotCommand("logout", "Log out (session kept)"),
            BotCommand("channels", "List all channels/groups"),
            BotCommand("forward", "Forward posts between channels"),
            BotCommand("download", "Download media to disk"),
            BotCommand("scraper", "Scrape Terabox links & forward"),
            BotCommand("gdrive_leech", "Leech files to Google Drive"),
            BotCommand("mega", "Download a Mega.nz link"),
            BotCommand("status", "Job progress & last msg ID"),
            BotCommand("pause", "Pause current job"),
            BotCommand("resume", "Resume paused job"),
            BotCommand("stop", "Stop & discard current job"),
            BotCommand("cancel", "Cancel the setup wizard"),
            BotCommand("stats", "Your usage stats"),
            BotCommand("history", "Last 5 extractions"),
            BotCommand("premium", "Premium plans & payment"),
            BotCommand("redeem", "Redeem a premium code"),
            BotCommand("id", "Show your user ID"),
            BotCommand("panel", "Admin control panel"),
        ])
    except Exception as e:
        log.warning(f"Could not set bot commands: {e}")

    register_handlers(bot)
    log.info("[Bot] Polling started with increased timeouts.")

    # Tier-1 node authority
    try:
        for admin_id in _get_l1_nodes():
            try:
                bot.send_message(admin_id, "🟢 <b>Bot is live.</b>", parse_mode="HTML")
            except Exception as e:
                log.debug(f"[startup-notify] Failed to send to {admin_id}: {e}")
    except Exception as e:
        log.warning(f"[startup-notify] Error broadcasting live message: {e}")

    retry_count = 0
    max_consecutive_errors = 10

    while True:
        try:
            # Increased timeouts: 90s for API calls, 60s for long polling
            bot.polling(
                non_stop=False,
                timeout=90,           # Increased from 60
                long_polling_timeout=60,  # Increased from 30
            )
            retry_count = 0  # Reset on success
        except apihelper.ApiTelegramException as e:
            if e.error_code == 401:
                log.error("[Bot] 401 Unauthorized — token invalid.")
                return
            if e.error_code == 409:
                log.error(
                    "[Bot] 409 Conflict — another instance is polling this token. "
                    "Stop the other Railway service or local process, then restart this one."
                )
                return
            retry_count += 1
            wait = min(30, 5 * retry_count)  # Exponential backoff, max 30s
            log.warning(f"[Bot] API error {e.error_code}: {e.description}")
            log.info(f"[Bot] Retry {retry_count} in {wait}s…")
            if retry_count >= max_consecutive_errors:
                log.error(f"[Bot] Too many consecutive errors ({retry_count}). Stopping.")
                return
            time.sleep(wait)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            retry_count += 1
            wait = min(30, 5 * retry_count)
            log.warning(f"[Bot] Connection timeout/error: {e}")
            log.info(f"[Bot] Retry {retry_count} in {wait}s…")
            if retry_count >= max_consecutive_errors:
                log.error(f"[Bot] Network unreliable ({retry_count} timeouts). Stopping.")
                return
            time.sleep(wait)
        except RecursionError:
            # RecursionError usually indicates a bug (infinite recursion)
            # Log full traceback and stop so systemd / operator can inspect state.
            log.exception("[Bot] Polling recursion error — aborting to allow inspection.")
            return
        except Exception:
            # Log full traceback for easier diagnosis
            retry_count += 1
            wait = min(30, 5 * retry_count)
            log.exception("[Bot] Polling exception")
            log.info(f"[Bot] Retry {retry_count} in {wait}s…")
            if retry_count >= max_consecutive_errors:
                log.error("[Bot] Too many errors. Stopping.")
                return
            time.sleep(wait)


# ══════════════════════════════════════════════════════════════════════
# SECTION 13 — ASYNC TASK RUNNERS
# ══════════════════════════════════════════════════════════════════════

async def _connect_and_warmup(client: TelegramClient) -> None:
    """
    Connect the client and warm up the entity cache by fetching all dialogs.

    Why this matters for private channels:
      Telethon needs the 'access_hash' to talk to a private channel.  This hash
      is only stored in the session AFTER the client has seen the channel in its
      dialog list.  By calling get_dialogs() here we pull every chat/channel the
      account is a member of and cache their hashes — so resolve_entity() can
      then reach any private channel the userbot has joined.
    """
    await client.connect()
    log.info("[warmup] Fetching dialogs to cache private-channel access hashes…")
    try:
        # limit=None fetches ALL dialogs (may take a few seconds for accounts
        # with many channels, but ensures nothing is missed)
        await client.get_dialogs(limit=None)
        log.info("[warmup] Dialog cache ready.")
    except Exception as e:
        log.warning(f"[warmup] get_dialogs failed (non-fatal): {e}")


def _make_task_client(api_id, api_hash: str, task_suffix: str, session_string: Optional[str] = None, **kwargs) -> "TelegramClient":
    """
    Create a TelegramClient that uses either a StringSession or an isolated copy
    of the base session file.

    If a stored StringSession is available, use it directly so the task does not
    rely on a local session file. Otherwise, clone the base session file to avoid
    concurrent write contention.
    """
    if session_string:
        if "timeout" not in kwargs:
            kwargs["timeout"] = 60
        return TelegramClient(StringSession(session_string), api_id, api_hash, **kwargs)

    # SECURITY: never fall back to a shared on-disk session file. All users who
    # rely on the default API_ID would share ONE file and see each other's chats.
    raise RuntimeError("No session string saved for this account. Please run /login again.")

    import shutil  # unreachable — kept for reference
    base = f"session_{api_id}"
    task = f"session_{api_id}_{task_suffix}"
    src_file = f"{base}.session"
    dst_file = f"{task}.session"
    if os.path.exists(src_file):
        try:
            shutil.copy2(src_file, dst_file)
            log.debug(f"[session] Copied {src_file} → {dst_file}")
        except Exception as e:
            log.warning(f"[session] Could not copy session file for {task_suffix}: {e}")
    else:
        log.warning(f"[session] Base session {src_file} not found — task may fail auth")
    if "timeout" not in kwargs:
        kwargs["timeout"] = 60
    return TelegramClient(task, api_id, api_hash, **kwargs)


async def _login_task(chat_id: int, uid: int, state: dict, otp_callback, password_callback=None) -> None:
    api_id = state["api_id"]
    api_hash = state["api_hash"]
    raw_phone = state["phone"]
    phone = re.sub(r"[^\d+]", "", raw_phone)

    if str(api_id).isdigit():
        api_id = int(api_id)

    # Always use a fresh in-memory session for login so the user provides new OTP/2FA
    client = TelegramClient(StringSession(), api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            _bot_send(chat_id, "⏳ Sending OTP to Telegram app...")
            send_code_res = await client.send_code_request(phone)

            # OTP prompt & handler registration is done by the sync bot flow
            # (_login_got_phone already sent the prompt and registered _login_got_otp).
            # Here we poll until the callback sets state["otp"], then sign in.
            # On expired/invalid codes we resend / re-ask instead of aborting.
            phone_code_hash = send_code_res.phone_code_hash
            max_resends  = 2   # how many times we ask Telegram for a fresh code
            max_attempts = 4   # total OTP attempts (invalid + expired)
            resends = attempts = 0
            signed_in = False

            async def _wait_for_otp() -> Optional[str]:
                for _ in range(300):  # 5 mins max
                    if state.get("otp"):
                        return state.get("otp")
                    if uid not in _conv:  # Cancelled
                        return None
                    await asyncio.sleep(1)
                return None

            def _reask_otp(text: str):
                if bot and otp_callback:
                    m = bot.send_message(chat_id, text, parse_mode="HTML")
                    try:
                        bot.clear_step_handler_by_chat_id(chat_id)
                    except Exception:
                        pass
                    bot.register_next_step_handler(m, otp_callback)
                else:
                    _bot_send(chat_id, text)

            while not signed_in and attempts < max_attempts:
                otp = await _wait_for_otp()
                if otp is None:
                    if uid not in _conv:
                        return
                    _bot_send(chat_id, "❌ OTP input timed out. Please try /login again.")
                    return
                state["otp"] = None
                clean_otp = re.sub(r"\D", "", otp)   # keep digits only ("1 2 3 4 5" -> "12345")
                attempts += 1
                if not clean_otp:
                    _reask_otp("❌ That doesn't look like a code. Send it as <code>1 2 3 4 5</code>:")
                    continue

                _bot_send(chat_id, "⏳ Signing in…")   # never echo the code back
                try:
                    await client.sign_in(phone, clean_otp, phone_code_hash=phone_code_hash)
                    signed_in = True
                except errors.SessionPasswordNeededError:
                    signed_in = "2fa"
                except errors.PhoneCodeInvalidError:
                    if attempts >= max_attempts:
                        raise
                    _reask_otp("❌ Wrong code. Try again — send it as <code>1 2 3 4 5</code>:")
                except errors.PhoneCodeExpiredError:
                    if resends >= max_resends:
                        raise
                    resends += 1
                    try:
                        send_code_res = await client.send_code_request(phone)
                        phone_code_hash = send_code_res.phone_code_hash
                    except errors.FloodWaitError as fw:
                        _bot_send(chat_id, f"❌ Telegram asked to wait {fw.seconds}s before a new code. Try /login later.")
                        return
                    _reask_otp(
                        "⚠️ That code expired (usually because the plain number was sent in a chat).\n"
                        "📩 A <b>new code</b> has been sent to your Telegram app.\n"
                        "👉 Send it with spaces between digits: <code>1 2 3 4 5</code>:"
                    )

            if signed_in == "2fa":
                # Send 2FA prompt from the sync bot thread via _bot_send, then poll.
                _bot_send(chat_id,
                          "5️⃣ <b>2FA Password:</b> Please send your two-step verification "
                          "password (send /cancel to abort):",
                          parse_mode="HTML")
                for pw_try in range(3):
                    state["password"] = None
                    if bot and password_callback:
                        _pending = bot.send_message(chat_id, "⌨️ Waiting for your 2FA password…", parse_mode="HTML")
                        try:
                            bot.clear_step_handler_by_chat_id(chat_id)
                        except Exception:
                            pass
                        bot.register_next_step_handler(_pending, password_callback)

                    password = None
                    for _ in range(300):
                        if state.get("password"):
                            password = state.get("password"); break
                        if uid not in _conv:
                            return
                        await asyncio.sleep(1)
                    if not password:
                        _bot_send(chat_id, "❌ 2FA password input timed out. Please try /login again.")
                        return

                    _bot_send(chat_id, "⏳ Signing in with 2FA password...")
                    try:
                        await client.sign_in(password=password.strip())
                        break
                    except errors.PasswordHashInvalidError:
                        if pw_try == 2:
                            raise
                        _bot_send(chat_id, "❌ Wrong 2FA password. Please send it again:")

        # Success! Save credentials to database (Multi-Tenant)
        session_string = client.session.save()
        save_user_credentials(uid, api_id, api_hash, session_string)

        _bot_send(chat_id,
                  "✅ <b>Login successful!</b> Credentials saved securely.\n\n"
                  "🔐 <b>YOUR SESSION STRING:</b>\n"
                  f"<code>{session_string}</code>\n\n"
                  "⚠️ <i>Keep this safe! It never expires. You can use it to log in later without OTP.</i>\n\n"
                  "Fetching channels...",
                  parse_mode="HTML")
        trigger_gdrive_backup(force=True)

        # Now fetch channels and present in properly copyable text
        chats = []
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if not isinstance(entity, (tl_types.Channel, tl_types.Chat)):
                continue
            username = getattr(entity, "username", None)
            title = dialog.name or "Unknown"
            kind = "GROUP" if getattr(entity, "megagroup", False) or isinstance(entity, tl_types.Chat) else "CHANNEL"
            private = not bool(username)
            chats.append({
                "id": entity.id,
                "title": title,
                "username": f"@{username}" if username else "private",
                "type": kind,
                "private": private
            })

        if not chats:
            _bot_send(chat_id, "📭 No channels or groups found.")
            return

        text_lines = []
        for c in chats:
            username_display = c['username'] if c['username'] != 'private' else 'No username (Private)'
            text_lines.append(
                f"<b>Name:</b> {_esc(c['title'])}\n"
                f"<b>ID:</b> <code>{c['id']}</code>\n"
                f"<b>Username:</b> {username_display}\n"
                f"<b>Type:</b> {c['type']}\n"
                f"---"
            )

        # Send in chunks so it fits in Telegram message limit (4096 chars)
        CHUNK_SIZE = 15
        total = len(chats)
        for page_start in range(0, total, CHUNK_SIZE):
            page_text = "\n".join(text_lines[page_start:page_start+CHUNK_SIZE])
            _bot_send(chat_id, f"📡 <b>Channels & Groups</b> [{page_start+1}-{min(page_start+CHUNK_SIZE, total)} of {total}]\n\n{page_text}")

        _bot_send(chat_id, "✅ Done! You can easily copy the IDs above.")

    except errors.PhoneCodeInvalidError:
        _bot_send(chat_id, "❌ Invalid OTP code. Please try /login again.")
    except errors.PhoneCodeExpiredError:
        _bot_send(chat_id,
                  "❌ OTP kept expiring. This happens when the plain code is sent/forwarded in any chat.\n"
                  "Run /login again and send the code as <code>1 2 3 4 5</code> (spaces between digits).")
    except errors.PasswordHashInvalidError:
        _bot_send(chat_id, "❌ Invalid 2FA password. Please try /login again.")
    except Exception as e:
        _bot_send(chat_id, f"❌ Error during login: {_esc(str(e))}")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass
        _conv.pop(uid, None)


async def _admin_user_channels_task(admin_chat: int, status_msg_id: int, target_uid: int) -> None:
    """Admin-only: connect with TARGET user's saved session and list their chats."""
    creds = _get_user_credentials(target_uid, ignore_logout=True)
    if not creds or not creds[2]:
        _bot_edit(admin_chat, status_msg_id,
                  f"❌ No saved session for <code>{target_uid}</code>.")
        return
    api_id, api_hash, session_string = creds
    try:
        client = _make_task_client(api_id, api_hash, f"admin{target_uid}",
                                   session_string=session_string,
                                   connection_retries=3, auto_reconnect=False)
        await client.connect()
        if not await client.is_user_authorized():
            _bot_edit(admin_chat, status_msg_id,
                      f"❌ Session of <code>{target_uid}</code> is expired/revoked.")
            return
        me = await client.get_me()
        rows = []
        async for dialog in client.iter_dialogs():
            ent = dialog.entity
            if not isinstance(ent, (tl_types.Channel, tl_types.Chat)):
                continue
            uname = getattr(ent, "username", None)
            kind  = "GROUP" if getattr(ent, "megagroup", False) or isinstance(ent, tl_types.Chat) else "CHANNEL"
            rows.append((kind, dialog.name or "Unknown", ent.id, f"@{uname}" if uname else "private"))
    except Exception as e:
        _bot_edit(admin_chat, status_msg_id, f"❌ Error: {_esc(str(e))}")
        return
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

    acct = f"@{me.username}" if getattr(me, "username", None) else _esc(me.first_name or "")
    head = (f"👤 <b>Account</b> {acct} (<code>{me.id}</code>) — bot user <code>{target_uid}</code>\n"
            f"🔑 API ID <code>{api_id}</code>  API Hash <code>{api_hash}</code>\n")
    if not rows:
        _bot_edit(admin_chat, status_msg_id, head + "\n📭 No channels or groups.")
        return
    try:
        if bot: bot.delete_message(admin_chat, status_msg_id)
    except Exception:
        pass
    PAGE = 25
    for i in range(0, len(rows), PAGE):
        chunk = rows[i:i + PAGE]
        body = "\n".join(
            f"{i + n + 1:>3}. [{k}] {_esc(t)} — <code>{cid}</code> {_esc(u)}"
            for n, (k, t, cid, u) in enumerate(chunk)
        )
        _bot_send(admin_chat,
                  (head if i == 0 else "") +
                  f"\n📡 <b>Channels &amp; Groups</b> [{i+1}–{i+len(chunk)} of {len(rows)}]\n{body}")


_worker_client: Optional[TelegramClient] = None
_worker_lock: Optional[asyncio.Lock] = None


def _get_worker_lock() -> asyncio.Lock:
    global _worker_lock
    if _worker_lock is None:
        _worker_lock = asyncio.Lock()
    return _worker_lock


async def _get_worker_client() -> Optional[TelegramClient]:
    """Connect the shared worker account once and reuse it.

    One account means one rate-limit bucket, so jobs are serialised by the
    caller holding _get_worker_lock() around a whole transfer.
    """
    global _worker_client
    if not worker_configured():
        return None
    if _worker_client is not None and _worker_client.is_connected():
        return _worker_client
    try:
        _worker_client = TelegramClient(
            StringSession(WORKER_SESSION), WORKER_API_ID, WORKER_API_HASH,
            connection_retries=5, auto_reconnect=True, timeout=60,
        )
        await _worker_client.connect()
        if not await _worker_client.is_user_authorized():
            log.error("[worker] WORKER_SESSION is not authorized — check the string session.")
            await _worker_client.disconnect()
            _worker_client = None
            return None
        me = await _worker_client.get_me()
        log.info(f"[worker] Connected as {getattr(me, 'username', None) or me.id}")
        return _worker_client
    except Exception as e:
        log.error(f"[worker] Connect failed: {e}")
        _worker_client = None
        return None


async def worker_join_link(link: str) -> tuple[bool, str]:
    """Join a channel from an invite link or @username with the worker account.

    Only links and usernames can be joined: a bare numeric ID carries no
    access_hash, so Telegram cannot resolve a chat the account is not in.
    """
    from telethon.tl.functions.channels import JoinChannelRequest
    from telethon.tl.functions.messages import ImportChatInviteRequest

    client = await _get_worker_client()
    if client is None:
        return False, "worker account is not configured"

    link = (link or "").strip()
    m = re.search(r"(?:t\.me/|telegram\.me/)(?:joinchat/|\+)([A-Za-z0-9_-]+)", link)
    try:
        if m:
            await client(ImportChatInviteRequest(m.group(1)))
            return True, "joined via invite link"
        slug = re.sub(r"^(?:https?://)?(?:t\.me/|telegram\.me/|@)", "", link).strip("/")
        if not slug or slug.lstrip("-").isdigit():
            return False, ("a numeric ID cannot be joined — send an invite link "
                           "or @username")
        await client(JoinChannelRequest(slug))
        return True, f"joined @{slug}"
    except Exception as e:
        msg = str(e)
        if "already" in msg.lower():
            return True, "already a member"
        return False, msg


async def worker_deliver_file(chat_id: int, file_path: str, filename: str,
                              caption: str, status_msg_id: Optional[int]) -> tuple[bool, str]:
    """Upload with the worker account, then have the bot copy it to the user.

    The worker is a normal account, so it cannot post as the bot into the
    user's chat. It uploads into the private dump channel instead and the bot
    copies that message out — a copy references a file already on Telegram's
    servers, so the 50MB upload cap does not apply.
    """
    client = await _get_worker_client()
    if client is None:
        return False, "worker account is not configured"

    size = os.path.getsize(file_path)
    category, _ = _detect_file_category(filename)
    prog = TransferProgress(chat_id, status_msg_id, "📤 <b>Uploading to Telegram…</b>",
                            filename, total=size)
    loop = asyncio.get_event_loop()

    def _cb(done, total):
        # Editing a message is a blocking HTTP call; keep it off the loop.
        try:
            loop.run_in_executor(None, prog.update, done, total or size)
        except Exception:
            pass

    async with _get_worker_lock():
        try:
            dump = await client.get_entity(DUMP_CHANNEL_ID)
            sent = await client.send_file(
                dump, file_path,
                caption=f"{filename}\n<code>{chat_id}</code>",
                parse_mode="html",
                force_document=category not in ("video", "audio", "photo"),
                supports_streaming=(category == "video"),
                attributes=[tl_types.DocumentAttributeFilename(filename)],
                progress_callback=_cb,
            )
        except errors.FloodWaitError as e:
            return False, f"Telegram asked to wait {e.seconds}s"
        except Exception as e:
            log.error(f"[worker upload] {e}")
            return False, str(e)

    # Hand it to the user through the bot, which needs no re-upload.
    try:
        if bot is None:
            return False, "bot is not running"
        bot.copy_message(chat_id, DUMP_CHANNEL_ID, sent.id,
                         caption=caption[:1024], parse_mode="HTML")
        return True, "delivered"
    except Exception as e:
        log.error(f"[worker relay] {e}")
        return False, f"uploaded but could not copy to you: {e}"

async def _userbot_upload_file(chat_id: int, file_path: str, filename: str,
                               caption: str = "") -> tuple[bool, str]:
    """Upload a file with the user's own account instead of the bot token.

    A bot may only push 50 MB through the Bot API; the linked account talks
    MTProto and reaches 2 GB. The userbot *is* the user, so it cannot post as
    the bot into this chat — the file goes to their Saved Messages, which they
    can open from any device.

    Returns (ok, message_for_the_user).
    """
    creds = _get_user_credentials(chat_id)
    if not creds:
        return False, "no linked account"
    api_id, api_hash, session_string = creds
    if not session_string:
        return False, "no session string stored"

    client = None
    try:
        client = _make_task_client(
            api_id, api_hash, f"up_{chat_id}",
            session_string=session_string,
            connection_retries=3, auto_reconnect=True,
        )
        await client.connect()
        if not await client.is_user_authorized():
            return False, "session expired — run /login again"

        category, _ = _detect_file_category(filename)
        kwargs = {
            "caption": caption[:1024] if caption else "",
            "parse_mode": "html",
            "force_document": category not in ("video", "audio", "photo"),
            "supports_streaming": category == "video",
            "attributes": [tl_types.DocumentAttributeFilename(filename)],
        }
        # "me" is Saved Messages for the account that owns this session.
        await client.send_file("me", file_path, **kwargs)
        return True, "sent to Saved Messages"
    except errors.FloodWaitError as e:
        return False, f"Telegram asked to wait {e.seconds}s"
    except Exception as e:
        log.error(f"[userbot upload] {e}")
        return False, str(e)
    finally:
        if client is not None:
            try:
                await client.disconnect()
            except Exception:
                pass
async def _list_chats_task(chat_id: int, status_msg_id: int) -> None:
    creds = _get_user_credentials(chat_id)
    if not creds:
        _bot_send(chat_id, "❌ You haven't logged in. Please run /login first.")
        return
    api_id, api_hash, session_string = creds
    client = _make_task_client(
        api_id, api_hash, "chats",
        session_string=session_string,
        connection_retries=5, auto_reconnect=True,
    )
    try:
        await client.connect()
        if not await client.is_user_authorized():
            try:
                if bot: bot.delete_message(chat_id, status_msg_id)
            except Exception:
                pass
            _bot_send(chat_id, "❌ Session expired or revoked. Please run /login again.")
            return
        chats: list[dict] = []
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if not isinstance(entity, (tl_types.Channel, tl_types.Chat)):
                continue
            username = getattr(entity, "username", None)
            is_mega  = getattr(entity, "megagroup", False)
            kind     = ("GROUP" if is_mega or isinstance(entity, tl_types.Chat) else "CHANNEL")
            private  = not bool(username)
            chats.append({
                "id"      : entity.id,
                "title"   : dialog.name or "Unknown",
                "username": f"@{username}" if username else "private",
                "type"    : kind,
                "private" : private,
            })
    finally:
        await client.disconnect()  # type: ignore

    if not chats:
        _bot_send(chat_id, "📭 No channels or groups found.")
        return

    _chat_cache[chat_id] = chats

    try:
        if bot: bot.delete_message(chat_id, status_msg_id)
    except Exception:
        pass

    PAGE = 25
    total = len(chats)
    for page_start in range(0, total, PAGE):
        page   = chats[page_start : page_start + PAGE]
        end    = min(page_start + PAGE, total)
        header = (
            f"📡 <b>Channels &amp; Groups</b>  [{page_start+1}–{end} of {total}]\n"
            f"<code>{'No':<4} {'Type':<8} {'Title':<32} ID / Username\n"
            f"{'-'*65}\n"
        )
        rows = ""
        for i, c in enumerate(page, page_start + 1):
            title = c["title"][:29] + ("…" if len(c["title"]) > 29 else "")
            lock  = "🔒" if c["private"] else "  "
            rows += f"{i:<4} {c['type']:<8} {title:<32} {c['username']}  {c['id']}  {lock}\n"
        _bot_send(chat_id, header + _esc(rows) + "</code>")

    _bot_send(chat_id,
              "💡 <b>Tip:</b> Send the <b>row number</b> (e.g. <code>3</code>) when a wizard asks "
              "for a channel. Or use @username / chat ID directly.\n"
              "🔒 = private channel (use row number or ID)")



async def _scraper_task(
    chat_id: int, src: str, dst: str,
    scrape_limit: Optional[int] = None,
) -> None:
    clients: list[TelegramClient] = []
    status_mid: Optional[int] = None
    job_id = f"scr_{chat_id}_{int(time.time())}"

    def _update_scraper_status(found: int, done: int, failed: int,
                                last_fn: str, note: str = "") -> None:
        dl_job_update(job_id, done, failed, cs["resume_id"], last_fn)
        text = (
            f"📡 **Scraper Running…**\n\n"
            f"🎯 Limit:    `{scrape_limit or 'ALL'}`\n"
            f"🔍 Found:    `{found}`\n"
            f"✅ Done:     `{done}`\n"
            f"❌ Failed:   `{failed}`\n"
            f"📄 Last:     `{_esc(last_fn or 'N/A')}`\n"
            + (f"\n⚠️ {note}" if note else "") +
            "\n\n/pause (ps)  /resume (rm)  /stop (so)"
        )
        if status_mid:
            _bot_edit(chat_id, status_mid, text)

    try:
        creds = _get_user_credentials(chat_id)
        if not creds:
            _bot_send(chat_id, "❌ You haven't logged in. Please run /login first.")
            return
        api_id, api_hash, session_string = creds

        c = _make_task_client(
            api_id, api_hash, "scr",
            session_string=session_string,
            connection_retries=5, auto_reconnect=True,
        )
        await _connect_and_warmup(c)
        clients.append(c)
        if not await c.is_user_authorized():
            _bot_send(chat_id, "❌ Session expired or revoked. Please run /login again.")
            return

        rotator = AccountRotator(clients)
        primary = clients[0]

        try:
            src_entity = await _ensure_joined(primary, src)
        except Exception as e:
            _bot_send(chat_id, f"❌ Cannot resolve source `{_esc(src)}`: {_esc(str(e))}")
            return
        try:
            dst_entity = await _ensure_joined(primary, dst)
        except Exception as e:
            _bot_send(chat_id, f"❌ Cannot resolve dest `{_esc(dst)}`: {_esc(str(e))}")
            return

        channel_key = getattr(src_entity, "title", None) or str(src_entity.id)
        state       = load_scraper_state()
        cs          = state.setdefault(channel_key, {
            "resume_id": 0, "download_count": 0,
            "failure": [], "break_id": None,
        })

        status_mid = _bot_send(
            chat_id,
            f"📡 **Scraper Running…**\n\n"
            f"📤 Source: `{_esc(channel_key)}`\n"
            f"🎯 Limit:  `{scrape_limit or 'ALL'}`\n"
            f"Resuming from msg ID > {cs['resume_id']}\n\n"
            "/pause (ps)  /resume (rm)  /stop (so)"
        )
        dl_job_create(job_id, chat_id, src, f"Scrape: {channel_key}", status_mid or 0, scrape_limit or 0)

        found_count  = 0
        done_count   = 0
        failed_count = 0
        last_fn      = ""

        pending_tasks = set()

        async def _process_item(msg, url, session):
            nonlocal done_count, failed_count, last_fn
            try:
                info = await extract_terabox_async(session, url)
                if not info or not info.get("download"):
                    failed_count += 1
                    cs["failure"].append(msg.id)
                    _update_scraper_status(found_count, done_count, failed_count, last_fn)
                    return

                download_url = info["download"]

                if download_url.endswith(".m3u8") or ".m3u8?" in download_url:
                    failed_count += 1
                    cs["failure"].append(msg.id)
                    _update_scraper_status(found_count, done_count, failed_count, last_fn, "HLS stream skipped.")
                    return

                filename = info.get("filename") or f"msg_{msg.id}"
                size = info.get("size")

                if isinstance(size, (int, float)) and size > 2 * 1024 ** 3:
                    failed_count += 1
                    cs["failure"].append(msg.id)
                    _update_scraper_status(found_count, done_count, failed_count, last_fn, "File > 2 GB skipped.")
                    return

                size_bytes = _parse_size_bytes(size) or _parse_size_bytes(info.get("size_human"))

                if size_bytes > 0 and size_bytes <= AUTO_SCRAPER_SEND_LIMIT:
                    filepath = await _async_download_to_disk(session, download_url, filename, size_bytes)
                    if not filepath:
                        failed_count += 1
                        cs["failure"].append(msg.id)
                        _update_scraper_status(found_count, done_count, failed_count, last_fn, "Download failed.")
                        return

                    try:
                        sender = await rotator.get_next_client()
                        thumb_url = info.get("thumb")
                        thumb  = await _download_thumb_async(session, thumb_url) if thumb_url else None
                        attrs  = [tl_types.DocumentAttributeVideo(
                            duration=_duration_seconds(info.get("duration", 0)),
                            w=int(info.get("width", 0) or 0), h=int(info.get("height", 0) or 0),
                            supports_streaming=True,
                        )]
                        send_kwargs = {
                            "caption": f"From {channel_key}",
                            "attributes": attrs,
                            "supports_streaming": True,
                            "force_document": False,
                            "allow_cache": False,
                        }
                        if thumb is not None:
                            send_kwargs["thumb"] = thumb

                        # Resilient upload with client reconnection on connection drop
                        for attempt in range(3):
                            try:
                                await sender.send_file(dst_entity, filepath, **send_kwargs)
                                break
                            except errors.FloodWaitError as e:
                                _bot_send(chat_id, f"⏳ FloodWait {e.seconds}s")
                                await _flood_wait(e.seconds)
                            except Exception as e:
                                log.warning(f"[scraper send file] Attempt {attempt+1} failed: {e}")
                                if isinstance(e, (errors.FilePartsInvalidError, ConnectionError, OSError)):
                                    try:
                                        log.info("[scraper send file] Reconnecting client to reset connection state...")
                                        await sender.disconnect()
                                        await asyncio.sleep(2)
                                        await sender.connect()
                                    except Exception as reconnect_err:
                                        log.warning(f"[scraper send file] Client reconnection failed: {reconnect_err}")
                                if attempt == 2: raise
                                await asyncio.sleep(3)

                        done_count += 1
                        last_fn = filename
                        _update_scraper_status(found_count, done_count, failed_count, last_fn)
                    except errors.FloodWaitError as e:
                        _bot_send(chat_id, f"⏳ FloodWait {e.seconds}s")
                        await _flood_wait(e.seconds)
                        failed_count += 1
                        cs["failure"].append(msg.id)
                        return
                    except Exception as e:
                        log.error(f"[scraper send file] {e}")
                        failed_count += 1
                        cs["failure"].append(msg.id)
                        return
                    finally:
                        if CLEAN_AFTER_SEND:
                            _clean_file(filepath)

                else:
                    try:
                        sender = await rotator.get_next_client()
                        caption = (
                            f"From {channel_key}\n\nDownload: {download_url}\n"
                            f"\n\n[Open Download Link]({download_url})"
                        )
                        streams = []
                        for label, key in [("360p", "stream_360p"), ("480p", "stream_480p"),
                                           ("720p", "stream_720p"), ("1080p", "stream_1080p")]:
                            if info.get(key) and info[key] != download_url:
                                streams.append(f'▶️ [{label}]({info[key]})')
                        if streams:
                            caption += "   " + "  ".join(streams)

                        await sender.send_message(dst_entity, caption, parse_mode="html")
                        done_count += 1
                        last_fn = filename
                        _update_scraper_status(found_count, done_count, failed_count, last_fn)
                    except errors.FloodWaitError as e:
                        _bot_send(chat_id, f"⏳ FloodWait {e.seconds}s")
                        await _flood_wait(e.seconds)
                        failed_count += 1
                        cs["failure"].append(msg.id)
                        return
                    except Exception as e:
                        log.error(f"[scraper link send] {e}")
                        failed_count += 1
                        cs["failure"].append(msg.id)
                        return
            except Exception as e:
                log.error(f"[_process_item] {e}")
                failed_count += 1
                cs["failure"].append(msg.id)

        async with aiohttp.ClientSession() as http_session:
            iter_client = await rotator.get_next_client()

            async for msg in iter_client.iter_messages(
                src_entity, min_id=cs["resume_id"], reverse=True
            ):
                ctrl = await _check_job_control(chat_id, job_id)
                if ctrl == "stop":
                    _update_scraper_status(found_count, done_count, failed_count,
                                           last_fn, "Stopped by admin.")
                    _bot_send(chat_id, "⏹ Scraper stopped.")
                    break

                links = extract_terabox_links(msg.text or "")
                if not links:
                    cs["resume_id"] = msg.id
                    save_scraper_state(state)
                    continue

                found_count += 1
                url = links[0]
                _update_scraper_status(found_count, done_count, failed_count, last_fn)

                task = asyncio.create_task(_process_item(msg, url, http_session))
                setattr(task, "msg_id", msg.id)
                pending_tasks.add(task)

                while len(pending_tasks) >= MAX_CONCURRENT_TASKS:
                    done, pending_tasks = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED)
                    if pending_tasks:
                        min_id = min(getattr(t, "msg_id", 0) for t in pending_tasks)
                        cs["resume_id"] = min_id - 1
                    else:
                        cs["resume_id"] = msg.id
                    save_scraper_state(state)

            if pending_tasks:
                await asyncio.wait(pending_tasks)
                if pending_tasks:
                    cs["resume_id"] = max((t.msg_id for t in pending_tasks), default=cs["resume_id"])
                save_scraper_state(state)

    except Exception as e:
        log.error(f"[_scraper_task fatal] {e}")
        _bot_send(chat_id, f"❌ Scraper crashed: {e}")
    finally:
        for c in clients:
            try:
                c.disconnect()
            except Exception:
                pass



async def _downloader_task(
    chat_id: int, src: str, src_label: str, limit: Optional[int],
    dl_photo: bool, dl_video: bool, dl_audio: bool, dl_doc: bool,
    status_msg_id: int,
) -> None:
    creds = _get_user_credentials(chat_id)
    if not creds:
        _bot_send(chat_id, "❌ You haven't logged in. Please run /login first.")
        return
    api_id, api_hash, session_string = creds
    client = _make_task_client(
        api_id, api_hash, "dl",
        session_string=session_string,
        connection_retries=5, auto_reconnect=True,
    )
    job_id = f"dl_{chat_id}_{int(time.time())}"

    try:
        await _connect_and_warmup(client)
        if not await client.is_user_authorized():
            _bot_edit(chat_id, status_msg_id, "❌ Session expired or revoked. Please run /login again.")
            return
        try:
            entity      = await _ensure_joined(client, src)
            folder_name = _clean_name(
                getattr(entity, "title", None) or
                getattr(entity, "username", None) or str(src), max_len=60
            )
        except Exception as e:
            _bot_edit(chat_id, status_msg_id,
                      f"❌ Cannot resolve <code>{_esc(src)}</code>: {_esc(str(e))}")
            return

        save_path = os.path.join(DL_BASE, folder_name)
        os.makedirs(save_path, exist_ok=True)

        dl_job_create(job_id, chat_id, src, src_label, status_msg_id, limit or 0)

        def _update_status(downloaded, failed, last_fn, last_mid, note=""):
            dl_job_update(job_id, downloaded, failed, last_mid, last_fn)
            bar  = _progress_bar(downloaded, limit) if limit else ""
            text = (
                f"📥 <b>Downloading…</b>\n\n"
                f"📡 Source: <code>{_esc(src_label)}</code>\n"
                f"📁 Folder: <code>{_esc(folder_name)}</code>\n"
                f"🎯 Wanted: <code>{limit or 'ALL'}</code>\n"
                f"✅ Done:   <code>{downloaded}</code>   ❌ Failed: <code>{failed}</code>\n"
                + (f"{bar}\n" if bar else "")
                + f"📄 Last: <code>{_esc(last_fn or 'N/A')}</code>\n"
                + f"🔖 MsgID: <code>{last_mid}</code>\n"
                + (f"\n{note}" if note else "")
                + "\n\n/pause (ps)  /resume (rm)  /stop (so)"
            )
            _bot_edit(chat_id, status_msg_id, text)

        resume_msg_id = 0
        try:
            with get_db() as conn:
                row = conn.execute("SELECT MAX(last_msg_id) as max_id FROM dl_progress WHERE src=?", (src,)).fetchone()
                if row and row["max_id"]:
                    resume_msg_id = row["max_id"]
        except Exception as e:
            log.warning(f"[downloader] Failed to fetch checkpoint: {e}")

        count = {"photo": 0, "video": 0, "audio": 0, "document": 0, "failed": 0, "skipped": 0}
        total_dl  = 0
        batch_cnt = 0
        last_fn   = ""
        last_mid  = 0

        if resume_msg_id > 0:
            _update_status(0, 0, "", 0, f"Resuming from checkpoint (MsgID > {resume_msg_id})…")
        else:
            _update_status(0, 0, "", 0, "Starting…")

        pending_tasks = set()

        async def _process_item(message):
            nonlocal total_dl, batch_cnt, last_fn, last_mid
            try:
                result = await _dl_one_message(
                    client, message, folder_name,
                    dl_photo, dl_video, dl_audio, dl_doc,
                )

                mark_msg_processed(src, message.id, "download")

                if result and result != "skipped":
                    if result == "failed":
                        count["failed"] += 1
                        _update_status(total_dl, count["failed"], last_fn, message.id)
                    else:
                        count[result] = count.get(result, 0) + 1
                        total_dl     += 1
                        batch_cnt    += 1
                        fn = _clean_name(
                            getattr(message.media, "document", None) and
                            next((a.file_name for a in getattr(message.media.document, "attributes", [])
                                  if isinstance(a, tl_types.DocumentAttributeFilename)), None)
                            or f"msg_{message.id}", 60
                        )
                        last_fn = fn
                        last_mid = message.id
                        _update_status(total_dl, count.get("failed", 0), last_fn, last_mid)
                elif result == "skipped":
                    count["skipped"] += 1
            except Exception as e:
                log.error(f"[downloader task process error] {e}")
                count["failed"] += 1
                _update_status(total_dl, count["failed"], last_fn, message.id)

        async for message in client.iter_messages(entity, limit=None, min_id=resume_msg_id, reverse=True):  # type: ignore

            ctrl = await _check_job_control(chat_id, job_id)
            if ctrl == "stop":
                _update_status(total_dl, count.get("failed", 0), last_fn, last_mid, "⏹ Stopped.")
                dl_job_update(job_id, total_dl, count.get("failed", 0), last_mid, last_fn, "stopped")
                break

            if is_msg_processed(src, message.id, "download"):
                count["skipped"] += 1
                continue

            task = asyncio.create_task(_process_item(message))
            task.msg_id = message.id
            pending_tasks.add(task)

            while len(pending_tasks) >= MAX_CONCURRENT_TASKS:
                done, pending_tasks = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED)
                if batch_cnt > 0 and batch_cnt % DL_BATCH_SIZE == 0:
                    _update_status(total_dl, count.get("failed", 0), last_fn, last_mid,
                                   f"⏳ Batch of {DL_BATCH_SIZE} done. Cooling down {DL_BATCH_COOLDOWN}s…")
                    await asyncio.sleep(DL_BATCH_COOLDOWN)

            if limit and total_dl >= limit:
                break

        if pending_tasks:
            await asyncio.wait(pending_tasks)

        dl_job_update(job_id, total_dl, count.get("failed", 0), last_mid, last_fn, "done")
        _bot_send(
            chat_id,
            f"🏁 <b>Download complete!</b>\n\n"
            f"📡 Source: <code>{_esc(src_label)}</code>\n"
            f"📁 Saved to: <code>{_esc(save_path)}</code>\n\n"
            f"🖼 Photos:    <code>{count['photo']}</code>\n"
            f"🎬 Videos:    <code>{count['video']}</code>\n"
            f"🎵 Audio:     <code>{count['audio']}</code>\n"
            f"📄 Documents: <code>{count['document']}</code>\n"
            f"⏩ Skipped:   <code>{count['skipped']}</code>\n"
            f"🔖 Last msg ID: <code>{last_mid}</code>\n\n"
            f"📊 Job ID: <code>{job_id}</code>",
        )

    except Exception as e:
        log.error(f"[downloader_task] {e}")
        _bot_send(chat_id, f"❌ Downloader error: <code>{_esc(str(e))}</code>")
    finally:
        job_clear(chat_id)
        await client.disconnect()  # type: ignore
def _is_real_document(doc) -> bool:
    """True only for genuine files (pdf/zip/apk/txt etc.).
    Rejects stickers, GIFs/animations, videos, photos/images and audio
    even when Telegram wraps them as MessageMediaDocument."""
    mime = (getattr(doc, "mime_type", "") or "").lower()
    for attr in getattr(doc, "attributes", []) or []:
        if isinstance(attr, (tl_types.DocumentAttributeSticker,
                             tl_types.DocumentAttributeAnimated,
                             tl_types.DocumentAttributeVideo,
                             tl_types.DocumentAttributeAudio,
                             tl_types.DocumentAttributeImageSize)):
            return False
        if isinstance(attr, tl_types.DocumentAttributeFilename):
            ext = os.path.splitext(getattr(attr, "file_name", "") or "")[1].lower()
            if ext in (".gif", ".webp", ".tgs", ".webm", ".jpg", ".jpeg", ".png",
                       ".mp4", ".mkv", ".mov", ".avi", ".mp3", ".ogg", ".m4a", ".flac"):
                return False
    if mime.startswith(("video/", "audio/", "image/")) or mime in ("application/x-tgsticker",):
        return False
    return True


async def _dl_one_message(
    client, message, folder_name: str,
    dl_photo: bool, dl_video: bool, dl_audio: bool, dl_doc: bool,
    max_retries: int = 3,
) -> Optional[str]:
    media = message.media
    if not media:
        return None

    date_str = message.date.strftime("%Y%m%d_%H%M%S")
    msg_id   = f"id{message.id}"
    caption  = _clean_name(getattr(message, "message", "") or "", max_len=50)

    def _fname(ext):
        parts = [date_str]
        if caption and caption != "unknown":
            parts.append(caption)
        parts.append(msg_id)
        return "_".join(parts) + ext

    def _folder(*sub):
        path = os.path.join(DL_BASE, folder_name, *sub)
        os.makedirs(path, exist_ok=True)
        return path

    try:
        if dl_photo and isinstance(media, tl_types.MessageMediaPhoto):
            fp = os.path.join(_folder("photos"), _fname(".jpg"))
            if os.path.exists(fp): return "skipped"
            await client.download_media(message, file=fp)
            return "photo"

        if isinstance(media, tl_types.MessageMediaDocument):
            mime = (getattr(media.document, "mime_type", "") or "")
            if dl_video and mime.startswith("video/"):
                ext = ".mkv" if "matroska" in mime else ".mp4"
                fp  = os.path.join(_folder("videos"), _fname(ext))
                if os.path.exists(fp): return "skipped"
                await client.download_media(message, file=fp)
                return "video"
            if dl_audio and mime.startswith("audio/"):
                ext = ".ogg" if "ogg" in mime else ".flac" if "flac" in mime else ".mp3"
                fp  = os.path.join(_folder("audio"), _fname(ext))
                if os.path.exists(fp): return "skipped"
                await client.download_media(message, file=fp)
                return "audio"
            if dl_doc and _is_real_document(media.document):
                orig = "file"
                for attr in getattr(media.document, "attributes", []):
                    if isinstance(attr, tl_types.DocumentAttributeFilename):
                        orig = getattr(attr, "file_name", orig); break
                fp = os.path.join(_folder("documents"),
                                  f"{date_str}_{msg_id}_{_clean_name(orig, 60)}")
                if os.path.exists(fp): return "skipped"
                await client.download_media(message, file=fp)
                return "document"

    except errors.FloodWaitError as e:
        if max_retries <= 0:
            return "failed"
        await _flood_wait(e.seconds)
        return await _dl_one_message(client, message, folder_name,
                                     dl_photo, dl_video, dl_audio, dl_doc, max_retries - 1)
    except Exception as e:
        log.error(f"[dl msg {message.id}] {e}")
        return "failed"

    # If we got media but no matching download option was enabled, treat it as skipped.
    return "skipped"


async def _forwarder_task(
    chat_id: int, src: str, dst: str, limit: Optional[int],
    fwd_photo: bool, fwd_video: bool, fwd_audio: bool, fwd_doc: bool,
    cap_mode: str, cap_prefix: str,
    start_after: int = 0,
) -> None:
    creds = _get_user_credentials(chat_id)
    if not creds:
        _bot_send(chat_id, "❌ You haven't logged in. Please run /login first.")
        return
    api_id, api_hash, session_string = creds
    client = _make_task_client(
        api_id, api_hash, f"fwd_{chat_id}",
        session_string=session_string,
        connection_retries=5, auto_reconnect=True,
    )
    job_id = f"fwd_{chat_id}_{int(time.time())}"
    user_fwd_cache = os.path.join(FORWARD_CACHE, f"u{chat_id}_{job_id}")
    os.makedirs(user_fwd_cache, exist_ok=True)
    task_scope = f"forward_{chat_id}_{dst}"

    try:
        await _connect_and_warmup(client)
        if not await client.is_user_authorized():
            _bot_send(chat_id, "❌ Session expired or revoked. Please run /login again.")
            return
        try:
            src_entity = await _ensure_joined(client, src)
            dst_entity = await _ensure_joined(client, dst)
            src_title  = getattr(src_entity, "title", None) or str(src)
        except Exception as e:
            _bot_send(chat_id, f"❌ Cannot resolve: <code>{_esc(str(e))}</code>")
            return

        status_mid = _bot_send(chat_id, f"🔄 <b>Forwarding from {_esc(src_title)}…</b>\n⏳ Initializing high-speed direct stream…")
        dl_job_create(job_id, chat_id, src, f"Fwd: {src_title} -> {dst}", status_mid or 0, limit or 0)

        skipped = dl_errors = sent = failed = processed = last_id = 0
        record     = _load_forward_record(src_title)
        total_ever = record.get("sent", 0)

        dst_min_id = 0
        dedup_note = ""

        try:
            with get_db() as conn:
                row = conn.execute(
                    "SELECT MAX(CAST(msg_id AS INTEGER)) as max_id "
                    "FROM processed_messages "
                    "WHERE source=? AND (task_type=? OR task_type='forward')",
                    (str(src), task_scope)
                ).fetchone()
                if row and row["max_id"]:
                    dst_min_id = int(row["max_id"])
                    log.info(f"[forwarder:{chat_id}] Checkpoint: skipping msg_id ≤ {dst_min_id}")
        except Exception as e:
            log.warning(f"[forwarder:{chat_id}] Checkpoint query failed: {e}")

        # A resume ID typed by the user beats the DB checkpoint — the DB is wiped
        # on every redeploy, so this is how a run picks up where the last one ended.
        if start_after and start_after > 0:
            dst_min_id = int(start_after)
            log.info(f"[forwarder:{chat_id}] User resume point: skipping msg_id ≤ {dst_min_id}")

        if dst_min_id > 0:
            try:
                probe = await client.get_messages(src_entity, limit=1, min_id=dst_min_id)
            except Exception:
                probe = []

            if not probe:
                _bot_edit(chat_id, status_mid,
                          f"✅ <b>{_esc(src_title)}</b> is already fully forwarded!\n\n"
                          f"🔖 Last checkpoint: Msg ID <code>{dst_min_id}</code>\n"
                          f"📭 No new messages found in the source channel.\n\n"
                          f"📦 Total ever forwarded: <code>{total_ever}</code>")
                dl_job_update(job_id, 0, 0, dst_min_id, "up-to-date", "done")
                job_clear(chat_id)
                return

            origin = "your input" if start_after else "saved checkpoint"
            dedup_note = f"🔖 Resuming after Msg ID <code>{dst_min_id}</code> ({origin})"
        else:
            dedup_note = "🆕 High-speed direct forwarding active."

        _bot_edit(chat_id, status_mid,
                  f"🔄 <b>Forwarding from {_esc(src_title)}…</b>\n{dedup_note}")

        # ALL mode (every media type ticked) also carries text-only posts so the
        # destination mirrors the source post-for-post.
        forward_text = fwd_photo and fwd_video and fwd_audio and fwd_doc

        def _classify(m):
            """(media_type, ext) under the active filters, or (None, None)."""
            media = m.media
            if isinstance(media, tl_types.MessageMediaPhoto):
                return ("photo", ".jpg") if fwd_photo else (None, None)
            if isinstance(media, tl_types.MessageMediaDocument):
                doc  = media.document
                mime = getattr(doc, "mime_type", "") or ""
                if fwd_video and mime.startswith("video/"):
                    return "video", ".mp4"
                if fwd_audio and mime.startswith("audio/"):
                    return "audio", (".ogg" if "ogg" in mime else ".mp3")
                if fwd_doc and _is_real_document(doc):
                    orig = "file.bin"
                    for attr in getattr(doc, "attributes", []):
                        if isinstance(attr, tl_types.DocumentAttributeFilename):
                            orig = getattr(attr, "file_name", orig); break
                    return "document", (os.path.splitext(orig)[1] or ".bin")
            return None, None

        def _caption_for(m) -> str:
            original = m.message or ""
            if cap_mode == "clear":
                return ""
            if cap_mode == "prefix":
                return cap_prefix + original
            return original

        def _attrs_for(m, media_type, path=None):
            media = m.media
            if not isinstance(media, tl_types.MessageMediaDocument):
                return None
            attrs = getattr(media.document, "attributes", []) or []
            if media_type == "video":
                for a in attrs:
                    if isinstance(a, tl_types.DocumentAttributeVideo):
                        return [tl_types.DocumentAttributeVideo(
                            duration=int(a.duration or 0), w=int(a.w or 0), h=int(a.h or 0),
                            supports_streaming=True)]
                return [tl_types.DocumentAttributeVideo(duration=0, w=0, h=0, supports_streaming=True)] if path else None
            if media_type == "audio":
                for a in attrs:
                    if isinstance(a, tl_types.DocumentAttributeAudio):
                        return [tl_types.DocumentAttributeAudio(
                            duration=int(a.duration or 0), performer=a.performer or "", title=a.title or "")]
                return None
            if media_type == "document":
                for a in attrs:
                    if isinstance(a, tl_types.DocumentAttributeFilename):
                        return [tl_types.DocumentAttributeFilename(str(a.file_name))]
                return [tl_types.DocumentAttributeFilename(os.path.basename(str(path)))] if path else None
            return None

        async def _send_group(group) -> str:
            """Forward one post: a single message or a whole album (same grouped_id).
            Returns 'sent' | 'skipped' | 'failed' | 'dlerr'."""
            items = [(m, mt, ext) for m in group for mt, ext in [_classify(m)] if mt]
            keep = cap_mode in ("keep", "default", "none")

            # ── Text-only post ────────────────────────────────────────────────
            if not items:
                if not (forward_text and not any(m.media for m in group)):
                    return "skipped"
                m = group[0]
                text = _caption_for(m)
                if not text.strip():
                    return "skipped"
                for attempt in range(3):
                    try:
                        if keep:
                            try:
                                await client.forward_messages(dst_entity, m)
                                return "sent"
                            except (errors.ChatForwardsRestrictedError, errors.ChatAdminRequiredError):
                                pass
                        await client.send_message(dst_entity, text,
                                                  formatting_entities=m.entities if keep else None,
                                                  link_preview=False)
                        return "sent"
                    except errors.FloodWaitError as e:
                        await _flood_wait(e.seconds)
                    except Exception as e:
                        log.warning(f"[fwd text] attempt {attempt+1}: {e}")
                        await asyncio.sleep(1)
                return "failed"

            msgs = [m for m, _, _ in items]
            # An album carries its caption on one member; take the first non-empty one.
            caption = next((_caption_for(m) for m in msgs if (m.message or "").strip()),
                           _caption_for(msgs[0]))
            album = len(msgs) > 1
            captions = [caption] + [""] * (len(msgs) - 1)   # album caption shown once

            # ── PRIORITY 1: DIRECT FORWARD (keeps the album grouped) ──────────
            if keep:
                for attempt in range(3):
                    try:
                        await client.forward_messages(dst_entity, msgs)
                        return "sent"
                    except errors.FloodWaitError as e:
                        await _flood_wait(e.seconds)
                    except (errors.ChatForwardsRestrictedError, errors.ChatAdminRequiredError):
                        break
                    except Exception as e:
                        log.debug(f"[fwd direct] attempt {attempt+1}: {e}")
                        await asyncio.sleep(1)

            # ── PRIORITY 2: CLOUD RE-SEND (no download, album preserved) ──────
            for attempt in range(3):
                try:
                    if album:
                        await client.send_file(dst_entity, [m.media for m in msgs],
                                               caption=captions, allow_cache=False)
                    else:
                        m, mt, _ = items[0]
                        await client.send_file(dst_entity, m.media, caption=caption,
                                               attributes=_attrs_for(m, mt), allow_cache=False)
                    return "sent"
                except errors.FloodWaitError as e:
                    await _flood_wait(e.seconds)
                except (errors.ChatForwardsRestrictedError, errors.MediaEmptyError):
                    break
                except Exception as e:
                    log.debug(f"[fwd cloud] attempt {attempt+1}: {e}")
                    await asyncio.sleep(1)

            # ── PRIORITY 3: DOWNLOAD + UPLOAD (protected content) ─────────────
            paths: list[str] = []
            for m, mt, ext in items:
                dest = os.path.join(user_fwd_cache, f"id{m.id}_{mt}{ext}")
                path = None
                for attempt in range(3):
                    try:
                        path = await client.download_media(m, file=dest)
                        break
                    except errors.FloodWaitError as e:
                        await _flood_wait(e.seconds)
                    except Exception as e:
                        log.warning(f"[fwd dl] attempt {attempt+1}: {e}")
                        await asyncio.sleep(2)
                if not path or not os.path.exists(str(path)):
                    if CLEAN_AFTER_SEND:
                        for p in paths: _clean_file(p)
                    return "dlerr"
                paths.append(str(path))

            try:
                for attempt in range(3):
                    try:
                        if album:
                            await client.send_file(dst_entity, paths, caption=captions,
                                                   supports_streaming=True, allow_cache=False)
                        else:
                            m, mt, _ = items[0]
                            await client.send_file(dst_entity, paths[0], caption=caption,
                                                   attributes=_attrs_for(m, mt, paths[0]),
                                                   force_document=(mt == "document"),
                                                   supports_streaming=(mt == "video"),
                                                   allow_cache=False)
                        return "sent"
                    except errors.FloodWaitError as e:
                        await _flood_wait(e.seconds)
                    except Exception as e:
                        log.warning(f"[fwd ul] attempt {attempt+1}: {e}")
                        if isinstance(e, (errors.FilePartsInvalidError, ConnectionError, OSError)):
                            try:
                                await client.disconnect()
                                await asyncio.sleep(2)
                                await client.connect()
                            except Exception:
                                pass
                        if attempt == 2:
                            raise
                        await asyncio.sleep(3)
            except Exception as e:
                log.error(f"[fwd ul] {e}")
                return "failed"
            finally:
                if CLEAN_AFTER_SEND:
                    for p in paths: _clean_file(p)
            return "failed"

        async def _handle(group) -> None:
            nonlocal sent, failed, dl_errors, skipped, processed, last_id
            res = await _send_group(group)
            if res == "sent":
                sent += len(group)
                for m in group:
                    mark_msg_processed(src, m.id, task_scope)
            elif res == "skipped":
                skipped += len(group)
            elif res == "dlerr":
                dl_errors += 1
            else:
                failed += 1
            processed += 1
            last_id = group[-1].id
            dl_job_update(job_id, sent, failed + dl_errors, last_id, f"Msg {last_id}")
            if processed % STATUS_UPDATE_INTERVAL == 0 and status_mid:
                try:
                    _bot_edit(chat_id, status_mid,
                              f"🔄 <b>Forwarding from {_esc(src_title)}…</b>\n"
                              f"⚡ Direct Forward: <code>Active</code>\n"
                              f"✅ Sent: <code>{sent}</code>\n"
                              f"❌ Failed/Err: <code>{failed + dl_errors}</code>\n"
                              f"⏭ Skipped: <code>{skipped}</code>\n"
                              f"🔖 Last msg ID: <code>{last_id}</code>")
                except Exception:
                    pass

        # Messages of one album share grouped_id and arrive consecutively when
        # iterating in ascending order, so buffer them and flush as one post.
        pending: list = []
        pending_gid = None

        async for msg in client.iter_messages(src_entity, limit=limit, min_id=dst_min_id, reverse=True):  # type: ignore

            ctrl = await _check_job_control(chat_id, job_id)
            if ctrl == "stop":
                if pending:
                    await _handle(pending); pending = []
                _bot_send(chat_id,
                          f"⏹ <b>Forwarder stopped.</b>\n"
                          f"✅ Sent: <code>{sent}</code>\n"
                          f"🔖 Last msg ID: <code>{last_id}</code>\n"
                          f"<i>Send this ID at the resume step next time to continue from here.</i>")
                dl_job_update(job_id, sent, failed + dl_errors, last_id or msg.id, "stopped", "stopped")
                break

            # An explicit resume ID is the user overriding history: forward
            # everything after it, even if a previous run marked it processed.
            if not start_after and (is_msg_processed(src, msg.id, task_scope)
                                    or is_msg_processed(src, msg.id, "forward")):
                if pending:
                    await _handle(pending); pending = []; pending_gid = None
                skipped += 1
                continue

            gid = getattr(msg, "grouped_id", None)
            if pending and (gid is None or gid != pending_gid):
                await _handle(pending); pending = []
            if gid is not None:
                pending.append(msg); pending_gid = gid
            else:
                await _handle([msg])

        if pending:
            await _handle(pending)

        record["sent"] = total_ever + sent
        _save_forward_record(src_title, record)

        if CLEAN_AFTER_SEND:
            try:
                shutil.rmtree(user_fwd_cache, ignore_errors=True)
            except Exception:
                pass

        _bot_send(chat_id,
                  f"🏁 <b>Forwarder complete!</b>\n"
                  f"✅ Sent: <code>{sent}</code>\n"
                  f"❌ Failed: <code>{failed}</code>\n"
                  f"⏭ Skipped: <code>{skipped}</code>\n"
                  f"🔖 Last msg ID: <code>{last_id or dst_min_id}</code>\n"
                  f"📦 Total ever forwarded: <code>{total_ever + sent}</code>\n\n"
                  f"<i>Save the Last msg ID — after a redeploy, enter it at the resume step "
                  f"to continue from here.</i>")
        dl_job_update(job_id, sent, failed + dl_errors, last_id or dst_min_id, "complete", "done")

    except Exception as e:
        log.error(f"[forwarder_task] {e}")
        _bot_send(chat_id, f"❌ Forwarder error: <code>{_esc(str(e))}</code>")
        dl_job_update(job_id, sent if 'sent' in locals() else 0,
                      (failed + dl_errors) if 'failed' in locals() and 'dl_errors' in locals() else 0,
                      0, f"error: {str(e)}", "failed")
    finally:
        job_clear(chat_id)
async def _skip_fwd_task(chat_id: int, src: str, count: int, status_msg_id: int) -> None:
    creds = _get_user_credentials(chat_id)
    if not creds:
        _bot_edit(chat_id, status_msg_id, "❌ You haven't logged in. Please run /login first.")
        return
    api_id, api_hash, session_string = creds
    client = _make_task_client(
        api_id, api_hash, "skipfwd",
        session_string=session_string,
        connection_retries=5, auto_reconnect=True,
    )
    try:
        await _connect_and_warmup(client)
        if not await client.is_user_authorized():
            _bot_edit(chat_id, status_msg_id, "❌ Session expired or revoked. Please run /login again.")
            return

        try:
            entity = await _ensure_joined(client, src)
            src_title = getattr(entity, "title", None) or str(src)
        except Exception as e:
            _bot_edit(chat_id, status_msg_id, f"❌ Cannot resolve source `{src}`: {e}")
            return

        _bot_edit(chat_id, status_msg_id, f"⏳ <b>Marking the latest {count} messages of {src_title} as forwarded...</b>")

        marked = 0
        async for msg in client.iter_messages(entity, limit=count):  # type: ignore
            if msg.media:
                mark_msg_processed(src, msg.id, "forward")
                marked += 1

        _bot_edit(
            chat_id, status_msg_id,
            f"✅ <b>Success!</b>\n\n"
            f"Processed the latest messages from <code>{_esc(src_title)}</code>.\n"
            f"Marked <code>{marked}</code> media messages as sent.\n"
            f"The forwarder will skip them on the next run."
        )
    except Exception as e:
        log.error(f"[skip_fwd_task] {e}")
        _bot_edit(chat_id, status_msg_id, f"❌ Error: <code>{_esc(str(e))}</code>")
    finally:
        await client.disconnect()  # type: ignore
# ══════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

def main() -> None:
    _restore_from_gdrive()
    init_db()
    _start_extraction_workers()
    # _start_proxy_manager()
    _start_gdrive_backup_manager()
    log.info("All-in-One Terabox & Media Tool v5.0")
    log.info("New in v5: approval workflow, unlimited admin, /pause /resume /stop,")
    log.info("           batch cooldown, DB-backed progress, fixed entity resolution")
    run_bot()


if __name__ == "__main__":
    # Register shutdown hook to flush Google Drive write cache on exit
    if os.path.exists("/content"):
        import atexit
        def _flush_gdrive_on_exit():
            try:
                from google.colab import drive  # type: ignore
                log.info("[shutdown] Flushing Google Drive writes to prevent data loss...")
                drive.flush_and_unmount()
                log.info("[shutdown] Google Drive flushed successfully.")
            except Exception as exc:
                log.warning(f"[shutdown] Failed to flush Google Drive: {exc}")
        atexit.register(_flush_gdrive_on_exit)
    # If in Colab, make sure cryptg is installed to prevent connection timeouts/drops during large file uploads
    if os.path.exists("/content"):
        try:
            import cryptg
            _ = cryptg
        except ImportError:
            import subprocess
            log.info("[startup] cryptg is missing, installing it to speed up transfers...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptg"])
                import cryptg
                _ = cryptg
                log.info("[startup] cryptg installed successfully.")
            except Exception as exc:
                log.warning(f"[startup] Failed to install cryptg: {exc}")

    main()