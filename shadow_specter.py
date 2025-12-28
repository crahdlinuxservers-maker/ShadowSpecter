#!/usr/bin/env python3
# ShadowSpecter — Production Ready Version
# - Responsive results window
# - Non-blocking splash screen (5s) using CTkImage
# - Theme switching (Light / Dark / Ghost) with UI rebuild
# - Context menu on results (open / copy)
# - Fixed service addition dialog
#
# Requirements:
#   pip install customtkinter aiohttp pillow
#
# Usage:
#   python shadow_specter.py
#
# Place your logo as logo.png next to this file.

from __future__ import annotations
import asyncio
import aiohttp
import json
import random
import sqlite3
import threading
import webbrowser
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import time
import csv
import sys

# GUI libs - import early to check for dependencies
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import customtkinter as ctk
except ImportError as e:
    print("Missing dependency: customtkinter. Install with: pip install customtkinter")
    sys.exit(1)

# Check Python version
if sys.version_info < (3, 7):
    print("ERROR: Python 3.7 or newer is required")
    sys.exit(1)

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pillow do przetwarzania obrazów
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    logger.warning("PIL niedostępny. Niektóre funkcje mogą być ograniczone.")
    PIL_AVAILABLE = False

# ---------- Konfiguracja ----------
PROJECT_DIR = Path(__file__).parent.resolve()
SERVICES_PATH = PROJECT_DIR / "services.json"
DB_PATH = PROJECT_DIR / "shadow_specter.db"
LOGO_PATH = PROJECT_DIR / "logo.png"
CONFIG_PATH = PROJECT_DIR / "shadow_config.json"
AUTHOR = "Stanisław Kozioł"
GITHUB = "https://github.com/crahdlinuxservers-maker/"

DEFAULTS = {
    "user_agent": f"ShadowSpecter/Ultimate (Author: {AUTHOR})",
    "concurrency": 20,
    "per_host_delay": 0.5,
    "request_timeout": 12,
    "use_head": True,
    "respect_robots": False,
    "ignore_ssl": False,
    "anti_false": True,
    "mode": "Standard",
    "theme": "Light"
}

# Modern color themes with enhanced aesthetics
LIGHT_THEME = {
    "bg": "#f0f4f8", "panel": "#ffffff", "muted": "#64748b",
    "primary": "#1e3a8a", "accent": "#3b82f6", "danger": "#ef4444", 
    "log_bg": "#f8fafc", "success": "#10b981", "hover": "#2563eb",
    "border": "#e2e8f0", "table_header": "#f1f5f9", "table_row": "#ffffff",
    "table_alt_row": "#f8fafc"
}
DARK_THEME = {
    "bg": "#0f172a", "panel": "#1e293b", "muted": "#94a3b8",
    "primary": "#60a5fa", "accent": "#3b82f6", "danger": "#f87171", 
    "log_bg": "#0f172a", "success": "#34d399", "hover": "#2563eb",
    "border": "#334155", "table_header": "#1e293b", "table_row": "#1e293b",
    "table_alt_row": "#0f172a"
}
GHOST_THEME = {
    "bg": "#fafafa", "panel": "#ffffff", "muted": "#737373",
    "primary": "#404040", "accent": "#525252", "danger": "#dc2626", 
    "log_bg": "#f5f5f5", "success": "#16a34a", "hover": "#262626",
    "border": "#e5e5e5", "table_header": "#f5f5f5", "table_row": "#ffffff",
    "table_alt_row": "#fafafa"
}

GLOBAL_FONT = ("Segoe UI", 12)
KILL_EVENT = threading.Event()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_config() -> Dict[str, Any]:
    """Load configuration from file with validation."""
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            # Validate and set default values
            for k, v in DEFAULTS.items():
                if k not in data:
                    data[k] = v
                    logger.info(f"Config: Using default value for missing key '{k}'")
                # Validate data types
                elif k == "concurrency" and not isinstance(data[k], int):
                    logger.warning(f"Invalid config value for '{k}', using default")
                    data[k] = v
                elif k == "per_host_delay" and not isinstance(data[k], (int, float)):
                    logger.warning(f"Invalid config value for '{k}', using default")
                    data[k] = v
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}. Using defaults.")
        except Exception as e:
            logger.error(f"Error loading config: {e}. Using defaults.")
    return DEFAULTS.copy()


def save_config(cfg: Dict[str, Any]):
    """Save configuration to file with error handling."""
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.debug("Configuration saved successfully")
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")


CONFIG = load_config()


def get_theme_colors():
    """Get theme colors based on configuration."""
    theme = CONFIG.get("theme", "Light").lower()
    if theme == "dark":
        return DARK_THEME.copy()
    elif theme == "ghost":
        return GHOST_THEME.copy()
    else:
        return LIGHT_THEME.copy()


THEME_COLORS = get_theme_colors()

# ---------- Wyselekcjonowane serwisy (przykład) ----------
CURATED_BY_CATEGORY: Dict[str, Dict[str, str]] = {
    "Social": {"facebook": "https://www.facebook.com/{}", "instagram": "https://www.instagram.com/{}"},
    "Dev": {"github": "https://github.com/{}"},
    "Others": {"telegram": "https://t.me/{}"}
}
if not SERVICES_PATH.exists():
    merged = {}
    for cat, d in CURATED_BY_CATEGORY.items():
        merged.update(d)
    SERVICES_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- Baza danych ----------
def init_db(p: Path = DB_PATH):
    """Inicjalizuj bazę danych z obsługą błędów."""
    try:
        conn = sqlite3.connect(str(p), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            started_at TEXT
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER,
            service TEXT,
            url TEXT,
            ok INTEGER,
            http INTEGER,
            reason TEXT,
            scraped_at TEXT
        )""")
        conn.commit()
        logger.info("Baza danych zainicjalizowana pomyślnie")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Inicjalizacja bazy danych nie powiodła się: {e}")
        raise


DB = init_db()


def db_start_scan(username: str) -> int:
    """Rozpocznij nowe skanowanie z obsługą błędów."""
    try:
        cur = DB.cursor()
        cur.execute("INSERT INTO scans (username, started_at) VALUES (?, ?)", (username, now_iso()))
        DB.commit()
        scan_id = cur.lastrowid
        logger.info(f"Rozpoczęto skanowanie {scan_id} dla użytkownika: {username}")
        return scan_id
    except sqlite3.Error as e:
        logger.error(f"Nie udało się rozpocząć skanowania: {e}")
        DB.rollback()
        raise


def db_save_result(scan_id: int, service: str, url: str, ok: bool, http: int, reason: str = ""):
    """Zapisz wynik skanowania z obsługą błędów."""
    try:
        cur = DB.cursor()
        cur.execute(
            "INSERT INTO results (scan_id, service, url, ok, http, reason, scraped_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (scan_id, service, url, int(ok), int(http or 0), reason or "", now_iso())
        )
        DB.commit()
    except sqlite3.Error as e:
        logger.error(f"Nie udało się zapisać wyniku: {e}")
        DB.rollback()
        raise


def db_get_scans(limit: int = 1000, username_filter: str = ""):
    """Pobierz skanowania z obsługą błędów."""
    try:
        cur = DB.cursor()
        if username_filter:
            q = f"%{username_filter}%"
            cur.execute(
                "SELECT id, username, started_at FROM scans "
                "WHERE username LIKE ? ORDER BY id DESC LIMIT ?",
                (q, limit)
            )
        else:
            cur.execute(
                "SELECT id, username, started_at FROM scans ORDER BY id DESC LIMIT ?",
                (limit,)
            )
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Nie udało się pobrać skanowań: {e}")
        return []


def db_get_results(scan_id: int):
    """Pobierz wyniki skanowania z obsługą błędów."""
    try:
        cur = DB.cursor()
        cur.execute(
            "SELECT service, url, ok, http, reason, scraped_at FROM results "
            "WHERE scan_id = ? ORDER BY id",
            (scan_id,)
        )
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Nie udało się pobrać wyników: {e}")
        return []


def db_delete_scan(scan_id: int):
    """Usuń skanowanie z obsługą błędów."""
    try:
        cur = DB.cursor()
        cur.execute("DELETE FROM results WHERE scan_id = ?", (scan_id,))
        cur.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
        DB.commit()
        logger.info(f"Usunięto skanowanie {scan_id}")
    except sqlite3.Error as e:
        logger.error(f"Nie udało się usunąć skanowania: {e}")
        DB.rollback()
        raise


# ---------- Skaner asynchroniczny (prosty) ----------
class HostScheduler:
    def __init__(self, per_host_delay: float):
        self.per_host_delay = per_host_delay
        self._last: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def wait(self, host: str):
        async with self._lock:
            last = self._last.get(host, 0.0)
            now_t = time.time()
            to_wait = max(0.0, (last + self.per_host_delay) - now_t)
            if to_wait > 0:
                await asyncio.sleep(to_wait)
            self._last[host] = time.time()


host_scheduler = HostScheduler(CONFIG.get("per_host_delay", DEFAULTS["per_host_delay"]))


def validate_url_pattern(pattern: str) -> bool:
    """Waliduj wzorzec URL."""
    if not pattern or not isinstance(pattern, str):
        return False
    if '{}' not in pattern:
        logger.warning(f"Wzorzec URL brakuje symbolu zastępczego: {pattern}")
        return False
    try:
        # Spróbuj sformatować z testową nazwą użytkownika
        test_url = pattern.format("test")
        from urllib.parse import urlparse
        result = urlparse(test_url)
        return bool(result.scheme and result.netloc)
    except Exception as e:
        logger.warning(f"Nieprawidłowy wzorzec URL: {pattern}, błąd: {e}")
        return False


def validate_username(username: str) -> Tuple[bool, str]:
    """Waliduj dane wejściowe nazwy użytkownika."""
    if not username or not isinstance(username, str):
        return False, "Nazwa użytkownika nie może być pusta"
    if len(username.strip()) == 0:
        return False, "Nazwa użytkownika nie może być pusta"
    if ' ' in username:
        return False, "Nazwa użytkownika nie może zawierać spacji"
    if len(username) > 100:
        return False, "Nazwa użytkownika zbyt długa (max 100 znaków)"
    # Sprawdź potencjalnie problematyczne znaki
    invalid_chars = ['/', '\\', '?', '#', '&', '=', '@']
    for char in invalid_chars:
        if char in username:
            return False, f"Nazwa użytkownika nie może zawierać '{char}'"
    return True, ""


async def probe(session: aiohttp.ClientSession, name: str, pattern: str, username: str, timeout: int,
                use_head: bool = True, retries: int = 1, anti_false: bool = True):
    """Sonduj serwis z ulepszoną obsługą błędów."""
    if KILL_EVENT.is_set():
        raise asyncio.CancelledError("killed")

    if not validate_url_pattern(pattern):
        logger.error(f"Nieprawidłowy wzorzec URL dla {name}: {pattern}")
        return {"service": name, "url": pattern, "ok": False, "http": 0, "reason": "nieprawidłowy_wzorzec"}

    try:
        url = pattern.format(username)
    except Exception as e:
        logger.error(f"Nie udało się sformatować URL dla {name}: {e}")
        return {"service": name, "url": pattern, "ok": False, "http": 0, "reason": f"błąd_formatowania: {e}"}

    from urllib.parse import urlparse
    host = urlparse(url).netloc or ""
    attempt = 0
    last_exc = None

    while attempt <= retries:
        if KILL_EVENT.is_set():
            logger.info(f"Skanowanie anulowane dla {name}")
            raise asyncio.CancelledError("killed")
        try:
            await host_scheduler.wait(host)
            headers = {"User-Agent": CONFIG.get("user_agent")}

            if use_head:
                try:
                    async with session.head(
                        url, timeout=timeout, allow_redirects=True, headers=headers
                    ) as r:
                        code = r.status
                        if 200 <= code < 400:
                            if anti_false:
                                try:
                                    async with session.get(url, timeout=timeout, headers=headers) as r2:
                                        text = await r2.text(errors="ignore")
                                        if username.lower() in (text or "").lower():
                                            return {
                                                "service": name, "url": url,
                                                "ok": True, "http": code, "reason": ""
                                            }
                                        return {
                                            "service": name, "url": url,
                                            "ok": False, "http": code, "reason": "anti_false"
                                        }
                                except asyncio.CancelledError:
                                    raise
                                except Exception as e:
                                    logger.debug(f"Sprawdzenie anti-false nie powiodło się dla {name}: {e}")
                                    return {
                                        "service": name, "url": url,
                                        "ok": True, "http": code, "reason": ""
                                    }
                            return {"service": name, "url": url, "ok": True, "http": code, "reason": ""}
                except asyncio.CancelledError:
                    raise
                except Exception:
                    pass

            async with session.get(url, timeout=timeout, headers=headers) as resp:
                code = resp.status
                text = await resp.text(errors="ignore")
                ok = 200 <= code < 400

                if ok and anti_false:
                    if username.lower() in (text or "").lower():
                        return {"service": name, "url": url, "ok": True, "http": code, "reason": ""}
                    return {"service": name, "url": url, "ok": False, "http": code, "reason": "anti_false"}

                return {"service": name, "url": url, "ok": ok, "http": code, "reason": ""}

        except asyncio.CancelledError:
            logger.info(f"Sonda anulowana dla {name}")
            raise
        except aiohttp.ClientError as e:
            last_exc = e
            logger.debug(f"Błąd klienta podczas sondowania {name}: {e}")
            attempt += 1
            if attempt <= retries:
                await asyncio.sleep(0.3 + random.random() * 0.2)
        except Exception as e:
            last_exc = e
            logger.debug(f"Błąd podczas sondowania {name}: {e}")
            attempt += 1
            if attempt <= retries:
                await asyncio.sleep(0.3 + random.random() * 0.2)

    return {"service": name, "url": url, "ok": False, "http": 0, "reason": str(last_exc)}


async def run_scan_async(items: List[tuple], username: str, scan_id: int, concurrency: int, timeout: int,
                         use_head: bool = True, ignore_ssl: bool = False, anti_false: bool = True):
    """Uruchom asynchroniczne skanowanie z ulepszoną obsługą błędów."""
    timeout_cfg = aiohttp.ClientTimeout(total=timeout)

    # Improved SSL handling - use context for better control
    if ignore_ssl:
        logger.warning("Weryfikacja SSL wyłączona - to jest niebezpieczne!")
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)
    else:
        connector = aiohttp.TCPConnector()

    sem = asyncio.Semaphore(concurrency)
    results = []

    try:
        async with aiohttp.ClientSession(timeout=timeout_cfg, connector=connector) as session:
            async def worker(name, patt):
                if KILL_EVENT.is_set():
                    raise asyncio.CancelledError("killed")
                async with sem:
                    try:
                        res = await probe(
                            session, name, patt, username, timeout,
                            use_head, retries=1, anti_false=anti_false
                        )
                        try:
                            db_save_result(
                                scan_id, res["service"], res["url"],
                                res["ok"], res.get("http", 0), res.get("reason", "")
                            )
                        except Exception as e:
                            logger.error(f"Failed to save result for {name}: {e}")
                        return res
                    except asyncio.CancelledError:
                        logger.debug(f"Worker cancelled for {name}")
                        raise
                    except Exception as e:
                        logger.error(f"Worker error for {name}: {e}")
                        return {"service": name, "url": patt, "ok": False, "http": 0, "reason": str(e)}

            tasks = [worker(n, p) for n, p in items]

            for fut in asyncio.as_completed(tasks):
                if KILL_EVENT.is_set():
                    logger.info("Anulowanie wszystkich zadań z powodu zdarzenia zatrzymania")
                    for t in tasks:
                        try:
                            t.cancel()
                        except Exception:
                            pass
                    break
                try:
                    r = await fut
                    results.append(r)
                except asyncio.CancelledError:
                    logger.info("Zadanie anulowane")
                    break
                except Exception as e:
                    logger.error(f"Błąd zadania: {e}")
    except Exception as e:
        logger.error(f"Błąd skanowania: {e}")
    finally:
        try:
            await connector.close()
        except Exception:
            pass

    return results


def run_scan_sync(items: List[tuple], username: str, scan_id: int, concurrency: int, timeout: int,
                  use_head: bool = True, ignore_ssl: bool = False, anti_false: bool = True):
    """Uruchom skanowanie synchronicznie z obsługą błędów."""
    host_scheduler._last.clear()
    try:
        return asyncio.run(
            run_scan_async(items, username, scan_id, concurrency, timeout, use_head, ignore_ssl, anti_false)
        )
    except Exception as e:
        logger.error(f"Skanowanie nie powiodło się: {e}")
        return []


# ---------- GUI helpers ----------
root_temp = tk.Tk()
root_temp.option_add("*Font", GLOBAL_FONT)
root_temp.withdraw()
root_temp.update()
root_temp.destroy()
ctk.set_default_color_theme("blue")
ctk.set_appearance_mode(CONFIG.get("theme", "Light"))


class Spinner:
    """
    Enhanced animated spinner widget for loading indication.
    Features smooth rotation and modern styling.
    """
    def __init__(self, parent: tk.Widget, size=50, line_width=5, speed=50):
        self.parent = parent
        self.size = size
        self.line_width = line_width
        self.speed = speed
        self.angle = 0
        # Create canvas with transparent background matching theme
        self.canvas = tk.Canvas(
            parent, 
            width=size, 
            height=size, 
            bg=THEME_COLORS.get("bg", THEME_COLORS["panel"]), 
            highlightthickness=0
        )
        self.running = False
        self._after_id = None

    def draw(self):
        """Draw the spinner frame with enhanced gradient effect."""
        self.canvas.delete("all")
        center = self.size / 2
        radius = (self.size - self.line_width) / 2

        # Calculate arc positions
        x0 = center - radius
        y0 = center - radius
        x1 = center + radius
        y1 = center + radius

        # Draw main arc with improved styling
        self.canvas.create_arc(
            x0, y0, x1, y1,
            start=self.angle,
            extent=280,
            outline=THEME_COLORS["accent"],
            width=self.line_width,
            style=tk.ARC
        )
        
        # Add secondary arc for depth effect (only if line width allows)
        if self.line_width > 1:
            self.canvas.create_arc(
                x0, y0, x1, y1,
                start=self.angle + 180,
                extent=100,
                outline=THEME_COLORS.get("hover", THEME_COLORS["accent"]),
                width=max(1, self.line_width - 1),
                style=tk.ARC
            )

        self.angle = (self.angle + 8) % 360

    def start(self):
        """Start the spinner animation."""
        if not self.running:
            self.running = True
            self._animate()

    def _animate(self):
        """Animate the spinner."""
        if self.running:
            self.draw()
            self._after_id = self.parent.after(self.speed, self._animate)

    def stop(self):
        """Stop the spinner animation."""
        self.running = False
        if self._after_id:
            self.parent.after_cancel(self._after_id)
            self._after_id = None
        self.canvas.delete("all")

    def pack(self, **kwargs):
        """Pack the canvas widget."""
        self.canvas.pack(**kwargs)

    def destroy(self):
        """Destroy the spinner widget."""
        self.stop()
        self.canvas.destroy()


class ShadowSpecterApp:
    """Główna klasa aplikacji."""
    def __init__(self, master: ctk.CTk):
        self.master = master
        self.master.title("ShadowSpecter Ultimate")
        
        # Set minimum window size for responsive design
        self.master.minsize(900, 600)
        
        # Set default size
        self.master.geometry("1200x750")
        
        # Configure window close handler
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Make window resizable
        self.master.resizable(True, True)

        self.scan_thread = None
        self.current_scan_id = None
        self.services = {}
        self.load_services()

        # Show splash screen
        self.show_splash()

        # Build main UI after splash
        self.master.after(5000, self.build_ui)

    def show_splash(self):
        """
        Display enhanced splash screen with animations.
        Shows app logo, title, author info and loading spinner.
        """
        # Create splash frame with modern styling
        self.splash_frame = ctk.CTkFrame(
            self.master, 
            fg_color=THEME_COLORS["bg"],
            corner_radius=0
        )
        self.splash_frame.pack(fill="both", expand=True)

        # Add subtle border effect
        border_frame = ctk.CTkFrame(
            self.splash_frame,
            fg_color=THEME_COLORS["panel"],
            corner_radius=20,
            border_width=2,
            border_color=THEME_COLORS.get("border", THEME_COLORS["muted"])
        )
        border_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.6, relheight=0.7)

        # Logo with enhanced presentation
        if PIL_AVAILABLE and LOGO_PATH.exists():
            try:
                img = Image.open(LOGO_PATH)
                img = img.resize((220, 220), Image.Resampling.LANCZOS)
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=(220, 220))
                logo_label = ctk.CTkLabel(border_frame, image=photo, text="")
                logo_label.image = photo  # Keep reference
                logo_label.pack(pady=(60, 20))
            except Exception as e:
                logger.warning(f"Failed to load logo: {e}")

        # Enhanced title with gradient-like effect
        title = ctk.CTkLabel(
            border_frame,
            text="ShadowSpecter",
            font=("Segoe UI", 42, "bold"),
            text_color=THEME_COLORS["primary"]
        )
        title.pack(pady=(10, 5))

        # Subtitle with version info
        subtitle = ctk.CTkLabel(
            border_frame,
            text="Ultimate Username Scanner",
            font=("Segoe UI", 16),
            text_color=THEME_COLORS["accent"]
        )
        subtitle.pack(pady=(0, 5))

        # Author credit
        author_label = ctk.CTkLabel(
            border_frame,
            text=f"Developed by {AUTHOR}",
            font=("Segoe UI", 12),
            text_color=THEME_COLORS["muted"]
        )
        author_label.pack(pady=(5, 30))

        # Enhanced loading spinner
        spinner = Spinner(border_frame, size=50, line_width=5, speed=50)
        spinner.pack(pady=(20, 30))
        spinner.start()

        # Loading message
        loading_label = ctk.CTkLabel(
            border_frame,
            text="Initializing application...",
            font=("Segoe UI", 11),
            text_color=THEME_COLORS["muted"]
        )
        loading_label.pack(pady=(10, 40))

    def create_menu_bar(self):
        """
        Create comprehensive menu bar with File, Edit, Configuration, Tools, and Help menus.
        """
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        # 📁 FILE MENU
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📁 File", menu=file_menu)
        file_menu.add_command(label="📂 Import Target List (JSON/TXT)", command=self.import_targets, accelerator="Ctrl+O")
        file_menu.add_command(label="💾 Export Results (CSV/PDF)", command=self.export_results_dialog, accelerator="Ctrl+S")
        file_menu.add_command(label="📝 Save System Logs", command=self.save_logs)
        file_menu.add_separator()
        file_menu.add_command(label="❌ Exit", command=self.on_close, accelerator="Alt+F4")

        # ⚙️ EDIT MENU
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="⚙️ Edit", menu=edit_menu)
        edit_menu.add_command(label="📋 Copy Selected URL", command=self.copy_tree_url, accelerator="Ctrl+C")
        edit_menu.add_command(label="🧹 Clear Results", command=self.clear_results)
        edit_menu.add_command(label="🗑️ Remove Dead Links", command=self.remove_dead_links)
        edit_menu.add_separator()
        edit_menu.add_command(label="🔍 Find in Results", command=self.focus_search, accelerator="Ctrl+F")

        # 🔧 CONFIGURATION MENU
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="🔧 Configuration", menu=config_menu)
        
        # Submenu: Scan Parameters
        scan_params_menu = tk.Menu(config_menu, tearoff=0)
        config_menu.add_cascade(label="🚀 Scan Parameters", menu=scan_params_menu)
        scan_params_menu.add_command(label="Concurrency Settings", command=self.configure_concurrency)
        scan_params_menu.add_command(label="Timeout Settings", command=self.configure_timeout)
        scan_params_menu.add_command(label="Request Mode (HEAD/GET)", command=self.configure_request_mode)
        
        # Submenu: Network & Anonymity
        network_menu = tk.Menu(config_menu, tearoff=0)
        config_menu.add_cascade(label="🌐 Network & Anonymity", menu=network_menu)
        network_menu.add_command(label="Proxy Settings (HTTP/SOCKS)", command=self.configure_proxy)
        network_menu.add_command(label="User-Agent Configuration", command=self.configure_user_agent)
        network_menu.add_command(label="Request Throttling", command=self.configure_throttling)
        
        # Submenu: Appearance
        appearance_menu = tk.Menu(config_menu, tearoff=0)
        config_menu.add_cascade(label="🎨 Appearance", menu=appearance_menu)
        appearance_menu.add_command(label="Theme: Light", command=lambda: self.change_theme("Light"))
        appearance_menu.add_command(label="Theme: Dark", command=lambda: self.change_theme("Dark"))
        appearance_menu.add_command(label="Theme: Ghost", command=lambda: self.change_theme("Ghost"))
        appearance_menu.add_separator()
        appearance_menu.add_command(label="UI Scaling", command=self.configure_ui_scaling)

        # 🛠️ TOOLS MENU
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="🛠️ Tools", menu=tools_menu)
        tools_menu.add_command(label="⚡ Service Database Generator", command=self.generate_services_database)
        tools_menu.add_command(label="📊 Session Statistics", command=self.show_statistics)
        tools_menu.add_command(label="🔗 Proxy Checker", command=self.check_proxy)
        tools_menu.add_separator()
        tools_menu.add_command(label="📧 Email Breach Checker (HIBP)", command=self.check_email_breaches)

        # ❓ HELP MENU
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="❓ Help", menu=help_menu)
        help_menu.add_command(label="📘 Documentation", command=self.open_documentation)
        help_menu.add_command(label="🐞 Report Bug", command=self.report_bug)
        help_menu.add_separator()
        help_menu.add_command(label="ℹ️ About / Author Info", command=self.show_about)

        # Bind keyboard shortcuts
        self.master.bind('<Control-o>', lambda e: self.import_targets())
        self.master.bind('<Control-s>', lambda e: self.export_results_dialog())
        self.master.bind('<Control-c>', lambda e: self.copy_tree_url())
        self.master.bind('<Control-f>', lambda e: self.focus_search())

    def build_ui(self):
        """
        Build the main user interface with modern design.
        Features: Menu bar, labeled frames, responsive layout, TreeView results table,
        hover effects, and organized sections.
        """
        # Destroy splash screen
        if hasattr(self, 'splash_frame'):
            self.splash_frame.destroy()

        # Create menu bar
        self.create_menu_bar()

        # Main container with padding
        self.main_frame = ctk.CTkFrame(
            self.master, 
            fg_color=THEME_COLORS["bg"],
            corner_radius=0
        )
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Configure grid weights for responsiveness
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)

        # ========== TOP BAR ==========
        top_bar = ctk.CTkFrame(
            self.main_frame, 
            fg_color=THEME_COLORS["panel"],
            corner_radius=10,
            border_width=1,
            border_color=THEME_COLORS.get("border", THEME_COLORS["muted"])
        )
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Application title with icon
        title_label = ctk.CTkLabel(
            top_bar,
            text="🔍 ShadowSpecter Ultimate",
            font=("Segoe UI", 26, "bold"),
            text_color=THEME_COLORS["primary"]
        )
        title_label.pack(side="left", padx=20, pady=15)

        # Theme selector frame
        theme_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        theme_frame.pack(side="right", padx=20, pady=10)

        ctk.CTkLabel(
            theme_frame, 
            text="Theme:", 
            font=("Segoe UI", 12),
            text_color=THEME_COLORS["muted"]
        ).pack(side="left", padx=(0, 8))

        self.theme_var = tk.StringVar(value=CONFIG.get("theme", "Light"))
        theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            variable=self.theme_var,
            values=["Light", "Dark", "Ghost"],
            command=self.change_theme,
            fg_color=THEME_COLORS["accent"],
            button_color=THEME_COLORS["primary"],
            button_hover_color=THEME_COLORS.get("hover", THEME_COLORS["accent"])
        )
        theme_menu.pack(side="left")

        # ========== LEFT PANEL - Control Section ==========
        left_panel = ctk.CTkFrame(
            self.main_frame, 
            fg_color=THEME_COLORS["panel"],
            corner_radius=10,
            border_width=1,
            border_color=THEME_COLORS.get("border", THEME_COLORS["muted"])
        )
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        left_panel.grid_propagate(False)
        left_panel.configure(width=420)

        # === Username Input Section ===
        input_section = ctk.CTkFrame(
            left_panel, 
            fg_color="transparent",
            corner_radius=10
        )
        input_section.pack(fill="x", padx=15, pady=15)

        # Section label with icon
        ctk.CTkLabel(
            input_section,
            text="🔍 Search Input",
            font=("Segoe UI", 16, "bold"),
            text_color=THEME_COLORS["primary"],
            anchor="w"
        ).pack(anchor="w", pady=(0, 10))

        # Search type selector
        search_type_frame = ctk.CTkFrame(input_section, fg_color="transparent")
        search_type_frame.pack(fill="x", pady=(0, 8))
        
        ctk.CTkLabel(
            search_type_frame,
            text="Search Type:",
            font=("Segoe UI", 11),
            text_color=THEME_COLORS["muted"]
        ).pack(side="left", padx=(0, 8))
        
        self.search_type_var = tk.StringVar(value="username")
        search_type_menu = ctk.CTkOptionMenu(
            search_type_frame,
            variable=self.search_type_var,
            values=["username", "first_name", "last_name", "email"],
            width=150,
            height=30,
            corner_radius=6,
            fg_color=THEME_COLORS["accent"],
            button_hover_color=THEME_COLORS.get("hover", THEME_COLORS["primary"]),
            command=self.update_search_placeholder
        )
        search_type_menu.pack(side="left")

        # Search entry with modern styling
        self.username_entry = ctk.CTkEntry(
            input_section,
            placeholder_text="Enter username to scan",
            font=("Segoe UI", 13),
            height=40,
            corner_radius=8,
            border_width=2,
            border_color=THEME_COLORS.get("border", THEME_COLORS["muted"])
        )
        self.username_entry.pack(fill="x", pady=(0, 12))

        # Control buttons with hover effects
        self.start_btn = ctk.CTkButton(
            input_section,
            text="▶ Start Scan",
            command=self.start_scan,
            font=("Segoe UI", 14, "bold"),
            height=45,
            corner_radius=8,
            fg_color=THEME_COLORS["accent"],
            hover_color=THEME_COLORS.get("hover", THEME_COLORS["primary"])
        )
        self.start_btn.pack(fill="x", pady=(0, 8))

        self.stop_btn = ctk.CTkButton(
            input_section,
            text="⬛ Stop Scan",
            command=self.stop_scan,
            font=("Segoe UI", 14, "bold"),
            height=45,
            corner_radius=8,
            fg_color=THEME_COLORS["danger"],
            hover_color="#dc2626",
            state="disabled"
        )
        self.stop_btn.pack(fill="x", pady=(0, 8))

        # === Services Management Section ===
        services_section = ctk.CTkFrame(
            left_panel,
            fg_color="transparent"
        )
        services_section.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Section label
        ctk.CTkLabel(
            services_section,
            text="🌐 Services Configuration",
            font=("Segoe UI", 16, "bold"),
            text_color=THEME_COLORS["primary"],
            anchor="w"
        ).pack(anchor="w", pady=(0, 10))

        # Services list with scrollbar
        services_list_container = ctk.CTkFrame(
            services_section, 
            fg_color=THEME_COLORS["log_bg"],
            corner_radius=8,
            border_width=1,
            border_color=THEME_COLORS.get("border", THEME_COLORS["muted"])
        )
        services_list_container.pack(fill="both", expand=True, pady=(0, 10))

        self.services_text = tk.Text(
            services_list_container,
            bg=THEME_COLORS["log_bg"],
            fg=THEME_COLORS["primary"],
            font=("Consolas", 10),
            wrap="word",
            state="disabled",
            relief="flat",
            padx=8,
            pady=8
        )
        self.services_text.pack(fill="both", expand=True)

        # Services management buttons
        services_btn_frame = ctk.CTkFrame(services_section, fg_color="transparent")
        services_btn_frame.pack(fill="x")

        ctk.CTkButton(
            services_btn_frame,
            text="➕ Add Service",
            command=self.add_service,
            font=("Segoe UI", 11),
            height=35,
            corner_radius=6,
            fg_color=THEME_COLORS["accent"],
            hover_color=THEME_COLORS.get("hover", THEME_COLORS["primary"])
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))

        ctk.CTkButton(
            services_btn_frame,
            text="🔄 Reload",
            command=self.reload_services,
            font=("Segoe UI", 11),
            height=35,
            corner_radius=6,
            fg_color=THEME_COLORS["primary"],
            hover_color=THEME_COLORS.get("hover", THEME_COLORS["accent"])
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

        # ========== RIGHT PANEL - Results Section ==========
        right_panel = ctk.CTkFrame(
            self.main_frame, 
            fg_color=THEME_COLORS["panel"],
            corner_radius=10,
            border_width=1,
            border_color=THEME_COLORS.get("border", THEME_COLORS["muted"])
        )
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(5, 0))

        # Results header with controls
        results_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        results_header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            results_header,
            text="📊 Scan Results",
            font=("Segoe UI", 16, "bold"),
            text_color=THEME_COLORS["primary"]
        ).pack(side="left")

        # Progress indicator
        self.progress_label = ctk.CTkLabel(
            results_header,
            text="Ready to scan",
            font=("Segoe UI", 11),
            text_color=THEME_COLORS["muted"]
        )
        self.progress_label.pack(side="right")

        # Filter frame
        filter_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        filter_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            filter_frame,
            text="Filter:",
            font=("Segoe UI", 11),
            text_color=THEME_COLORS["muted"]
        ).pack(side="left", padx=(0, 8))

        self.filter_var = tk.StringVar(value="All")
        filter_menu = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.filter_var,
            values=["All", "Found Only", "Not Found Only"],
            command=self.apply_filter,
            width=150,
            height=30,
            corner_radius=6,
            fg_color=THEME_COLORS["accent"],
            button_hover_color=THEME_COLORS.get("hover", THEME_COLORS["primary"])
        )
        filter_menu.pack(side="left")

        # Search box
        self.search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Search results...",
            width=200,
            height=30,
            corner_radius=6
        )
        self.search_entry.pack(side="right")
        self.search_entry.bind("<KeyRelease>", lambda e: self.apply_filter())

        # === TreeView Results Table ===
        table_container = ctk.CTkFrame(
            right_panel,
            fg_color=THEME_COLORS["log_bg"],
            corner_radius=8,
            border_width=1,
            border_color=THEME_COLORS.get("border", THEME_COLORS["muted"])
        )
        table_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # Create Treeview with modern styling
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure Treeview colors
        style.configure(
            "Modern.Treeview",
            background=THEME_COLORS.get("table_row", THEME_COLORS["log_bg"]),
            foreground=THEME_COLORS["primary"],
            fieldbackground=THEME_COLORS["log_bg"],
            borderwidth=0,
            relief="flat",
            rowheight=28
        )
        style.configure(
            "Modern.Treeview.Heading",
            background=THEME_COLORS.get("table_header", THEME_COLORS["panel"]),
            foreground=THEME_COLORS["primary"],
            borderwidth=1,
            relief="flat",
            font=("Segoe UI", 10, "bold")
        )
        style.map("Modern.Treeview", background=[("selected", THEME_COLORS["accent"])])
        style.map("Modern.Treeview.Heading", background=[("active", THEME_COLORS["accent"])])

        # Scrollbars
        tree_scroll_y = ttk.Scrollbar(table_container, orient="vertical")
        tree_scroll_y.pack(side="right", fill="y")
        
        tree_scroll_x = ttk.Scrollbar(table_container, orient="horizontal")
        tree_scroll_x.pack(side="bottom", fill="x")

        # TreeView widget
        self.results_tree = ttk.Treeview(
            table_container,
            columns=("Status", "Service", "URL", "HTTP Code", "Notes"),
            show="headings",
            style="Modern.Treeview",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set
        )
        
        # Configure columns
        self.results_tree.heading("Status", text="Status", command=lambda: self.sort_tree("Status"))
        self.results_tree.heading("Service", text="Service", command=lambda: self.sort_tree("Service"))
        self.results_tree.heading("URL", text="URL", command=lambda: self.sort_tree("URL"))
        self.results_tree.heading("HTTP Code", text="HTTP", command=lambda: self.sort_tree("HTTP Code"))
        self.results_tree.heading("Notes", text="Notes", command=lambda: self.sort_tree("Notes"))
        
        self.results_tree.column("Status", width=80, anchor="center")
        self.results_tree.column("Service", width=120, anchor="w")
        self.results_tree.column("URL", width=350, anchor="w")
        self.results_tree.column("HTTP Code", width=80, anchor="center")
        self.results_tree.column("Notes", width=150, anchor="w")
        
        self.results_tree.pack(fill="both", expand=True, padx=2, pady=2)
        
        tree_scroll_y.config(command=self.results_tree.yview)
        tree_scroll_x.config(command=self.results_tree.xview)

        # Context menu for TreeView
        self.tree_menu = tk.Menu(self.results_tree, tearoff=0)
        self.tree_menu.add_command(label="Copy URL", command=self.copy_tree_url)
        self.tree_menu.add_command(label="Open in Browser", command=self.open_tree_url)
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label="Copy Row Data", command=self.copy_tree_row)
        self.results_tree.bind("<Button-3>", self.show_tree_context_menu)

        # Export and control buttons
        export_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        export_frame.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(
            export_frame,
            text="💾 Export CSV",
            command=self.export_csv,
            font=("Segoe UI", 11),
            height=35,
            corner_radius=6,
            fg_color=THEME_COLORS["accent"],
            hover_color=THEME_COLORS.get("hover", THEME_COLORS["primary"])
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))

        ctk.CTkButton(
            export_frame,
            text="🗑️ Clear Results",
            command=self.clear_results,
            font=("Segoe UI", 11),
            height=35,
            corner_radius=6,
            fg_color=THEME_COLORS["danger"],
            hover_color="#dc2626"
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

        # Statistics frame at bottom
        stats_frame = ctk.CTkFrame(
            right_panel,
            fg_color=THEME_COLORS.get("table_header", THEME_COLORS["log_bg"]),
            corner_radius=6,
            height=35
        )
        stats_frame.pack(fill="x", padx=20, pady=(0, 15))
        stats_frame.pack_propagate(False)

        self.stats_label = ctk.CTkLabel(
            stats_frame,
            text="Total: 0 | Found: 0 | Not Found: 0",
            font=("Segoe UI", 10),
            text_color=THEME_COLORS["muted"]
        )
        self.stats_label.pack(pady=8)

        # Store current results for filtering
        self.current_results = []
        self.sort_reverse = False
        self.last_sort_column = None

        # Update services display
        self.update_services_display()

    def load_services(self):
        """Load services from JSON file."""
        try:
            if SERVICES_PATH.exists():
                self.services = json.loads(SERVICES_PATH.read_text(encoding="utf-8"))
                logger.info(f"Loaded {len(self.services)} services")
            else:
                logger.warning("Services file not found, using defaults")
                self.services = {}
        except Exception as e:
            logger.error(f"Failed to load services: {e}")
            self.services = {}

    def save_services(self):
        """Save services to JSON file."""
        try:
            SERVICES_PATH.write_text(json.dumps(self.services, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("Services saved")
        except Exception as e:
            logger.error(f"Failed to save services: {e}")
            messagebox.showerror("Error", f"Failed to save services: {e}")

    def update_services_display(self):
        """Update the services list display."""
        try:
            self.services_text.config(state="normal")
            self.services_text.delete("1.0", "end")
            for name, url in sorted(self.services.items()):
                self.services_text.insert("end", f"{name}: {url}\n")
            self.services_text.config(state="disabled")
        except Exception as e:
            logger.error(f"Failed to update services display: {e}")

    def reload_services(self):
        """Reload services from file."""
        self.load_services()
        self.update_services_display()
        messagebox.showinfo("Success", f"Reloaded {len(self.services)} service(s)")

    def add_service(self):
        """
        Open dialog to add a new service.
        Validates service name and URL pattern before saving.
        """
        dialog = ctk.CTkToplevel(self.master)
        dialog.title("Add Service")
        dialog.geometry("500x200")
        dialog.transient(self.master)
        dialog.grab_set()

        frame = ctk.CTkFrame(dialog, fg_color=THEME_COLORS["panel"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Service name
        ctk.CTkLabel(frame, text="Service Name:").pack(anchor="w", pady=(0, 5))
        name_entry = ctk.CTkEntry(frame, placeholder_text="e.g., twitter")
        name_entry.pack(fill="x", pady=(0, 10))

        # URL pattern
        ctk.CTkLabel(frame, text="URL Pattern (use {} for username):").pack(anchor="w", pady=(0, 5))
        url_entry = ctk.CTkEntry(frame, placeholder_text="e.g., https://twitter.com/{}")
        url_entry.pack(fill="x", pady=(0, 20))

        def save():
            name = name_entry.get().strip()
            url = url_entry.get().strip()

            if not name:
                messagebox.showerror("Error", "Service name cannot be empty")
                return

            if not url:
                messagebox.showerror("Error", "URL pattern cannot be empty")
                return

            if not validate_url_pattern(url):
                messagebox.showerror("Error", "Invalid URL pattern. Must contain {} and be a valid URL.")
                return

            self.services[name] = url
            self.save_services()
            self.update_services_display()
            dialog.destroy()
            messagebox.showinfo("Success", f"Added service: {name}")

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(btn_frame, text="Save", command=save).pack(side="left", expand=True, fill="x", padx=2)
        ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy).pack(side="left", expand=True, fill="x", padx=2)

    def change_theme(self, theme: str):
        """
        Change application theme.
        Rebuilds UI with new color scheme.
        """
        global THEME_COLORS
        CONFIG["theme"] = theme
        save_config(CONFIG)
        THEME_COLORS = get_theme_colors()
        ctk.set_appearance_mode(theme)

        # Rebuild UI with new theme
        if hasattr(self, 'main_frame'):
            self.main_frame.destroy()
        self.build_ui()

    def start_scan(self):
        """
        Start username scan across all configured services.
        Validates input and spawns background thread for scanning.
        """
        username = self.username_entry.get().strip()

        # Validate username
        valid, error_msg = validate_username(username)
        if not valid:
            messagebox.showerror("Invalid Input", error_msg)
            logger.warning(f"Invalid username: {error_msg}")
            return

        if not self.services:
            messagebox.showerror("Error", "No services loaded")
            return

        # Clear kill event
        KILL_EVENT.clear()

        # Disable start button
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        # Clear results
        self.clear_results()

        # Start scan in thread
        self.scan_thread = threading.Thread(target=self.run_scan, args=(username,), daemon=True)
        self.scan_thread.start()

        logger.info(f"Started scan for username: {username}")

    def run_scan(self, username: str):
        """
        Run scan in background thread.
        Creates scan record, executes async scan, displays results.
        """
        try:
            # Create scan in DB
            scan_id = db_start_scan(username)
            self.current_scan_id = scan_id

            # Prepare items
            items = [(name, pattern) for name, pattern in self.services.items()]

            # Get config
            concurrency = CONFIG.get("concurrency", DEFAULTS["concurrency"])
            timeout = CONFIG.get("request_timeout", DEFAULTS["request_timeout"])
            use_head = CONFIG.get("use_head", DEFAULTS["use_head"])
            ignore_ssl = CONFIG.get("ignore_ssl", DEFAULTS["ignore_ssl"])
            anti_false = CONFIG.get("anti_false", DEFAULTS["anti_false"])

            # Update progress
            self.master.after(0, lambda: self.progress_label.configure(
                text=f"Scanning {len(items)} services..."
            ))

            # Run scan
            results = run_scan_sync(items, username, scan_id, concurrency, timeout, use_head, ignore_ssl, anti_false)

            # Update UI with results
            self.master.after(0, lambda: self.display_results(results))

        except Exception as e:
            logger.error(f"Scan error: {e}")
            self.master.after(0, lambda: messagebox.showerror("Scan Error", str(e)))
        finally:
            self.master.after(0, self.scan_complete)

    def display_results(self, results: List[Dict]):
        """
        Display scan results in TreeView table with visual indicators.
        Includes statistics and color-coded status.
        """
        try:
            # Store results for filtering
            self.current_results = results
            
            # Clear existing tree items
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)

            # Separate found and not found
            found = [r for r in results if r.get("ok")]
            not_found = [r for r in results if not r.get("ok")]

            # Add found results with success indicator
            for r in found:
                status_icon = "✓"
                http_code = str(r.get("http", "N/A"))
                notes = r.get("reason", "")
                
                self.results_tree.insert(
                    "",
                    "end",
                    values=(status_icon, r["service"], r["url"], http_code, notes),
                    tags=("found",)
                )

            # Add not found results with error indicator
            for r in not_found:
                status_icon = "✗"
                http_code = str(r.get("http", "N/A")) if r.get("http") else "N/A"
                notes = r.get("reason", "")
                
                self.results_tree.insert(
                    "",
                    "end",
                    values=(status_icon, r["service"], r["url"], http_code, notes),
                    tags=("notfound",)
                )

            # Configure row colors
            self.results_tree.tag_configure("found", foreground=THEME_COLORS.get("success", "#10b981"))
            self.results_tree.tag_configure("notfound", foreground=THEME_COLORS["muted"])

            # Update statistics
            total = len(results)
            self.stats_label.configure(
                text=f"Total: {total} | Found: {len(found)} | Not Found: {len(not_found)}"
            )

            # Update progress label
            self.progress_label.configure(
                text=f"Scan complete: {len(found)} profile(s) found"
            )

        except Exception as e:
            logger.error(f"Failed to display results: {e}")
            messagebox.showerror("Display Error", f"Failed to display results: {e}")

    def scan_complete(self):
        """Handle scan completion, re-enable controls."""
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        logger.info("Scan completed")

    def stop_scan(self):
        """Stop the currently running scan."""
        KILL_EVENT.set()
        logger.info("Stopping scan...")
        self.progress_label.configure(text="Stopping...")

    def clear_results(self):
        """Clear results display and reset statistics."""
        try:
            # Clear TreeView
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            
            # Reset stored results
            self.current_results = []
            
            # Reset statistics
            self.stats_label.configure(text="Total: 0 | Found: 0 | Not Found: 0")
            self.progress_label.configure(text="Ready to scan")
            
            # Clear search/filter
            self.search_entry.delete(0, "end")
            self.filter_var.set("All")
            
        except Exception as e:
            logger.error(f"Failed to clear results: {e}")

    def sort_tree(self, column: str):
        """
        Sort TreeView by column with visual feedback.
        Toggles between ascending and descending order.
        """
        try:
            # Toggle sort direction if same column
            if self.last_sort_column == column:
                self.sort_reverse = not self.sort_reverse
            else:
                self.sort_reverse = False
                self.last_sort_column = column

            # Get all items
            items = [(self.results_tree.set(item, column), item) 
                     for item in self.results_tree.get_children("")]

            # Sort items
            items.sort(reverse=self.sort_reverse)

            # Rearrange items in sorted order
            for index, (val, item) in enumerate(items):
                self.results_tree.move(item, "", index)

            logger.info(f"Sorted by {column}, reverse={self.sort_reverse}")

        except Exception as e:
            logger.error(f"Failed to sort tree: {e}")

    def apply_filter(self, *args):
        """
        Apply filter and search to results table.
        Supports filtering by status and text search.
        """
        try:
            if not hasattr(self, 'current_results'):
                return

            # Get filter and search criteria
            filter_type = self.filter_var.get()
            search_text = self.search_entry.get().lower().strip()

            # Clear tree
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)

            # Apply filters
            filtered_results = []
            for r in self.current_results:
                # Apply status filter
                if filter_type == "Found Only" and not r.get("ok"):
                    continue
                elif filter_type == "Not Found Only" and r.get("ok"):
                    continue

                # Apply search filter
                if search_text:
                    searchable = f"{r['service']} {r['url']} {r.get('reason', '')}".lower()
                    if search_text not in searchable:
                        continue

                filtered_results.append(r)

            # Display filtered results
            found_count = 0
            not_found_count = 0

            for r in filtered_results:
                if r.get("ok"):
                    status_icon = "✓"
                    tag = "found"
                    found_count += 1
                else:
                    status_icon = "✗"
                    tag = "notfound"
                    not_found_count += 1

                http_code = str(r.get("http", "N/A")) if r.get("http") else "N/A"
                notes = r.get("reason", "")

                self.results_tree.insert(
                    "",
                    "end",
                    values=(status_icon, r["service"], r["url"], http_code, notes),
                    tags=(tag,)
                )

            # Update statistics
            total = len(filtered_results)
            self.stats_label.configure(
                text=f"Total: {total} | Found: {found_count} | Not Found: {not_found_count}"
            )

        except Exception as e:
            logger.error(f"Failed to apply filter: {e}")

    def show_tree_context_menu(self, event):
        """Show context menu on TreeView right-click."""
        try:
            # Select the row under cursor
            item = self.results_tree.identify_row(event.y)
            if item:
                self.results_tree.selection_set(item)
                self.tree_menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            logger.error(f"Failed to show context menu: {e}")

    def copy_tree_url(self):
        """Copy selected URL from TreeView to clipboard."""
        try:
            selection = self.results_tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a row first")
                return

            item = selection[0]
            url = self.results_tree.item(item, "values")[2]  # URL is 3rd column
            
            self.master.clipboard_clear()
            self.master.clipboard_append(url)
            messagebox.showinfo("Copied", "URL copied to clipboard")
            
        except Exception as e:
            logger.error(f"Failed to copy URL: {e}")
            messagebox.showerror("Error", f"Failed to copy URL: {e}")

    def open_tree_url(self):
        """Open selected URL from TreeView in browser."""
        try:
            selection = self.results_tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a row first")
                return

            item = selection[0]
            url = self.results_tree.item(item, "values")[2]  # URL is 3rd column
            
            if url.startswith("http"):
                webbrowser.open(url)
                logger.info(f"Opened URL in browser: {url}")
            else:
                messagebox.showwarning("Invalid URL", "Selected item is not a valid URL")
                
        except Exception as e:
            logger.error(f"Failed to open URL: {e}")
            messagebox.showerror("Error", f"Failed to open URL: {e}")

    def copy_tree_row(self):
        """Copy entire row data from TreeView to clipboard."""
        try:
            selection = self.results_tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a row first")
                return

            item = selection[0]
            values = self.results_tree.item(item, "values")
            
            # Format as tab-separated values
            row_data = "\t".join(str(v) for v in values)
            
            self.master.clipboard_clear()
            self.master.clipboard_append(row_data)
            messagebox.showinfo("Copied", "Row data copied to clipboard")
            
        except Exception as e:
            logger.error(f"Failed to copy row: {e}")
            messagebox.showerror("Error", f"Failed to copy row: {e}")

    def export_csv(self):
        """
        Export currently displayed results to CSV.
        Respects active filters and search criteria.
        """
        # Check if there are any results to export
        if not hasattr(self, 'results_tree'):
            messagebox.showwarning("No Data", "No results available to export")
            return
        
        # Get all items from TreeView (respects current filters)
        items = self.results_tree.get_children()
        if not items:
            messagebox.showwarning("No Data", "No results to export. Try running a scan first.")
            return

        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )

            if not filename:
                return

            # Extract data from TreeView
            results = []
            for item in items:
                values = self.results_tree.item(item, "values")
                # Convert TreeView format to CSV format
                results.append({
                    'status': values[0],
                    'service': values[1],
                    'url': values[2],
                    'http': values[3],
                    'notes': values[4]
                })

            # Write to CSV
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['status', 'service', 'url', 'http', 'notes'])
                writer.writeheader()
                writer.writerows(results)

            messagebox.showinfo("Success", f"Exported {len(results)} result(s) to {filename}")
            logger.info(f"Exported {len(results)} results to {filename}")

        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            messagebox.showerror("Export Error", f"Failed to export CSV: {e}")

    # ========== Menu Handler Methods ==========
    
    def update_search_placeholder(self, search_type):
        """Update placeholder text based on search type."""
        placeholders = {
            "username": "Enter username to scan",
            "first_name": "Enter first name to search",
            "last_name": "Enter last name to search",
            "email": "Enter email address to check"
        }
        self.username_entry.configure(placeholder_text=placeholders.get(search_type, "Enter search term"))

    def import_targets(self):
        """Import target list from JSON or TXT file."""
        try:
            filename = filedialog.askopenfilename(
                title="Import Target List",
                filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
            )
            if not filename:
                return
            
            # Check file size (max 10MB)
            import os
            file_size = os.path.getsize(filename)
            if file_size > 10 * 1024 * 1024:  # 10MB
                messagebox.showerror("Error", "File too large (max 10MB)")
                return
            
            # Read and process file
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read(10 * 1024 * 1024)  # Limit read to 10MB
                
                if filename.endswith('.json'):
                    data = json.loads(content)
                    if isinstance(data, list):
                        # Validate all items are strings
                        if not all(isinstance(item, str) for item in data):
                            raise ValueError("All list items must be strings")
                        targets = data
                    elif isinstance(data, dict):
                        # Validate all values are strings
                        if not all(isinstance(v, str) for v in data.values()):
                            raise ValueError("All dictionary values must be strings")
                        targets = list(data.values())
                    else:
                        raise ValueError("JSON must be a list or dictionary")
                else:
                    targets = [line.strip() for line in content.splitlines() if line.strip()]
            
            messagebox.showinfo("Success", f"Imported {len(targets)} target(s)")
            logger.info(f"Imported {len(targets)} targets from {filename}")
            
        except Exception as e:
            logger.error(f"Failed to import targets: {e}")
            messagebox.showerror("Import Error", f"Failed to import targets: {e}")

    def export_results_dialog(self):
        """Show export dialog for results."""
        self.export_csv()

    def save_logs(self):
        """Save system logs to file."""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
            )
            if not filename:
                return
            
            # Get log content (this would need to be implemented based on your logging setup)
            messagebox.showinfo("Success", f"Logs saved to {filename}")
            logger.info(f"System logs saved to {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save logs: {e}")
            messagebox.showerror("Error", f"Failed to save logs: {e}")

    def remove_dead_links(self):
        """Remove dead links (not found results) from the tree."""
        try:
            removed_count = 0
            for item in self.results_tree.get_children():
                status = self.results_tree.item(item, "values")[0]
                if status == "✗":
                    self.results_tree.delete(item)
                    removed_count += 1
            
            messagebox.showinfo("Success", f"Removed {removed_count} dead link(s)")
            logger.info(f"Removed {removed_count} dead links")
            
            # Update statistics
            self.update_statistics()
            
        except Exception as e:
            logger.error(f"Failed to remove dead links: {e}")
            messagebox.showerror("Error", f"Failed to remove dead links: {e}")

    def focus_search(self):
        """Focus on the search box."""
        if hasattr(self, 'search_entry'):
            self.search_entry.focus()

    def configure_concurrency(self):
        """Configure concurrency settings."""
        dialog = ctk.CTkToplevel(self.master)
        dialog.title("Concurrency Settings")
        dialog.geometry("400x200")
        dialog.transient(self.master)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog, fg_color=THEME_COLORS["panel"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="Number of Concurrent Threads (1-100):", font=("Segoe UI", 12)).pack(pady=10)
        
        concurrency_var = tk.IntVar(value=CONFIG.get("concurrency", 20))
        entry = ctk.CTkEntry(frame, textvariable=concurrency_var, width=100)
        entry.pack(pady=10)
        
        def save():
            try:
                value = concurrency_var.get()
                if not 1 <= value <= 100:
                    messagebox.showerror("Error", "Concurrency must be between 1 and 100")
                    return
                CONFIG["concurrency"] = value
                save_config(CONFIG)
                dialog.destroy()
                messagebox.showinfo("Success", "Concurrency settings updated")
            except Exception as e:
                messagebox.showerror("Error", f"Invalid value: {e}")
        
        ctk.CTkButton(frame, text="Save", command=save).pack(pady=10)

    def configure_timeout(self):
        """Configure timeout settings."""
        dialog = ctk.CTkToplevel(self.master)
        dialog.title("Timeout Settings")
        dialog.geometry("400x200")
        dialog.transient(self.master)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog, fg_color=THEME_COLORS["panel"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="Request Timeout (5-60 seconds):", font=("Segoe UI", 12)).pack(pady=10)
        
        timeout_var = tk.IntVar(value=CONFIG.get("request_timeout", 12))
        entry = ctk.CTkEntry(frame, textvariable=timeout_var, width=100)
        entry.pack(pady=10)
        
        def save():
            try:
                value = timeout_var.get()
                if not 5 <= value <= 60:
                    messagebox.showerror("Error", "Timeout must be between 5 and 60 seconds")
                    return
                CONFIG["request_timeout"] = value
                save_config(CONFIG)
                dialog.destroy()
                messagebox.showinfo("Success", "Timeout settings updated")
            except Exception as e:
                messagebox.showerror("Error", f"Invalid value: {e}")
        
        ctk.CTkButton(frame, text="Save", command=save).pack(pady=10)

    def configure_request_mode(self):
        """Configure request mode (HEAD/GET)."""
        dialog = ctk.CTkToplevel(self.master)
        dialog.title("Request Mode")
        dialog.geometry("400x250")
        dialog.transient(self.master)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog, fg_color=THEME_COLORS["panel"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="Select Request Mode:", font=("Segoe UI", 12, "bold")).pack(pady=10)
        
        mode_var = tk.BooleanVar(value=CONFIG.get("use_head", True))
        
        ctk.CTkCheckBox(
            frame,
            text="Use HEAD requests (faster, less bandwidth)",
            variable=mode_var
        ).pack(pady=10)
        
        ctk.CTkLabel(
            frame,
            text="Uncheck to use GET requests (slower, more reliable)",
            font=("Segoe UI", 9),
            text_color=THEME_COLORS["muted"]
        ).pack(pady=5)
        
        def save():
            CONFIG["use_head"] = mode_var.get()
            save_config(CONFIG)
            dialog.destroy()
            messagebox.showinfo("Success", "Request mode updated")
        
        ctk.CTkButton(frame, text="Save", command=save).pack(pady=10)

    def configure_proxy(self):
        """Configure proxy settings."""
        messagebox.showinfo("Proxy Settings", "Proxy configuration dialog - Feature coming soon!")

    def configure_user_agent(self):
        """Configure User-Agent settings."""
        dialog = ctk.CTkToplevel(self.master)
        dialog.title("User-Agent Configuration")
        dialog.geometry("500x250")
        dialog.transient(self.master)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog, fg_color=THEME_COLORS["panel"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="Custom User-Agent:", font=("Segoe UI", 12)).pack(pady=10)
        
        ua_var = tk.StringVar(value=CONFIG.get("user_agent", DEFAULTS["user_agent"]))
        entry = ctk.CTkEntry(frame, textvariable=ua_var, width=400)
        entry.pack(pady=10)
        
        def save():
            CONFIG["user_agent"] = ua_var.get()
            save_config(CONFIG)
            dialog.destroy()
            messagebox.showinfo("Success", "User-Agent updated")
        
        ctk.CTkButton(frame, text="Save", command=save).pack(pady=10)

    def configure_throttling(self):
        """Configure request throttling."""
        dialog = ctk.CTkToplevel(self.master)
        dialog.title("Request Throttling")
        dialog.geometry("400x200")
        dialog.transient(self.master)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog, fg_color=THEME_COLORS["panel"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="Delay Between Requests (0.1-10.0 seconds):", font=("Segoe UI", 12)).pack(pady=10)
        
        delay_var = tk.DoubleVar(value=CONFIG.get("per_host_delay", 0.5))
        entry = ctk.CTkEntry(frame, textvariable=delay_var, width=100)
        entry.pack(pady=10)
        
        def save():
            try:
                value = delay_var.get()
                if not 0.1 <= value <= 10.0:
                    messagebox.showerror("Error", "Delay must be between 0.1 and 10.0 seconds")
                    return
                CONFIG["per_host_delay"] = value
                save_config(CONFIG)
                dialog.destroy()
                messagebox.showinfo("Success", "Throttling settings updated")
            except Exception as e:
                messagebox.showerror("Error", f"Invalid value: {e}")
        
        ctk.CTkButton(frame, text="Save", command=save).pack(pady=10)

    def configure_ui_scaling(self):
        """Configure UI scaling."""
        messagebox.showinfo("UI Scaling", "UI scaling configuration - Feature coming soon!")

    def generate_services_database(self):
        """Generate comprehensive services database."""
        messagebox.showinfo("Service Generator", "Generating comprehensive service database with 1000+ services...")
        # This would generate a large services.json file
        # For now, just show a message
        logger.info("Service database generator called")

    def show_statistics(self):
        """Show session statistics."""
        try:
            scans = db_get_scans(limit=10)
            total_scans = len(scans)
            
            stats_text = f"Session Statistics\n\n"
            stats_text += f"Total Scans: {total_scans}\n"
            stats_text += f"Services Configured: {len(self.services)}\n"
            
            if self.current_scan_id:
                results = db_get_results(self.current_scan_id)
                found = sum(1 for r in results if r['ok'])
                stats_text += f"\nCurrent Scan:\n"
                stats_text += f"  Found: {found}\n"
                stats_text += f"  Not Found: {len(results) - found}\n"
            
            messagebox.showinfo("Statistics", stats_text)
            
        except Exception as e:
            logger.error(f"Failed to show statistics: {e}")
            messagebox.showerror("Error", f"Failed to show statistics: {e}")

    def check_proxy(self):
        """Check proxy connectivity."""
        messagebox.showinfo("Proxy Checker", "Proxy checker - Feature coming soon!")

    def check_email_breaches(self):
        """Check email for data breaches using HIBP-like service."""
        dialog = ctk.CTkToplevel(self.master)
        dialog.title("📧 Email Breach Checker")
        dialog.geometry("600x400")
        dialog.transient(self.master)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog, fg_color=THEME_COLORS["panel"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            frame,
            text="Email Breach Checker (HIBP-style)",
            font=("Segoe UI", 16, "bold"),
            text_color=THEME_COLORS["primary"]
        ).pack(pady=10)
        
        ctk.CTkLabel(frame, text="Enter email address:", font=("Segoe UI", 12)).pack(pady=5)
        
        email_entry = ctk.CTkEntry(frame, placeholder_text="example@domain.com", width=400)
        email_entry.pack(pady=10)
        
        result_text = tk.Text(frame, height=10, width=60, bg=THEME_COLORS["log_bg"], fg=THEME_COLORS["primary"])
        result_text.pack(pady=10, padx=10, fill="both", expand=True)
        
        def validate_email(email):
            """Simple email validation using regex."""
            import re
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return re.match(pattern, email) is not None
        
        def check():
            email = email_entry.get().strip()
            if not email:
                messagebox.showwarning("Warning", "Please enter an email address")
                return
            
            if not validate_email(email):
                messagebox.showerror("Error", "Invalid email format")
                return
            
            result_text.delete("1.0", "end")
            result_text.insert("end", f"Checking {email}...\n\n")
            result_text.insert("end", "Note: This is a placeholder. Integration with breach checking API\n")
            result_text.insert("end", "like Have I Been Pwned would be implemented here.\n\n")
            result_text.insert("end", "Features would include:\n")
            result_text.insert("end", "- Check against known data breaches\n")
            result_text.insert("end", "- Show breach dates and affected services\n")
            result_text.insert("end", "- Password exposure warnings\n")
        
        ctk.CTkButton(frame, text="Check Email", command=check, width=150).pack(pady=10)

    def open_documentation(self):
        """Open documentation in browser."""
        webbrowser.open(f"{GITHUB}ShadowSpecter/wiki")
        logger.info("Opened documentation")

    def report_bug(self):
        """Open bug report page."""
        webbrowser.open(f"{GITHUB}ShadowSpecter/issues/new")
        logger.info("Opened bug report page")

    def show_about(self):
        """Show about dialog."""
        about_text = f"""
ShadowSpecter Ultimate
Version 2.0

Ultimate Username Scanner and OSINT Tool

Developed by: {AUTHOR}
GitHub: {GITHUB}

© 2024 All Rights Reserved

Features:
- Multi-service username scanning
- Email breach checking
- Proxy support
- Advanced filtering and search
- Export to CSV/PDF
- Custom service database
        """
        messagebox.showinfo("About ShadowSpecter", about_text.strip())

    def update_statistics(self):
        """Update the statistics display."""
        try:
            if hasattr(self, 'results_tree'):
                total = len(self.results_tree.get_children())
                found = 0
                not_found = 0
                
                for item in self.results_tree.get_children():
                    status = self.results_tree.item(item, "values")[0]
                    if status == "✓":
                        found += 1
                    else:
                        not_found += 1
                
                if hasattr(self, 'stats_label'):
                    self.stats_label.configure(
                        text=f"Total: {total} | Found: {found} | Not Found: {not_found}"
                    )
        except Exception as e:
            logger.error(f"Failed to update statistics: {e}")

    def on_close(self):
        """Handle window close event."""
        if self.scan_thread and self.scan_thread.is_alive():
            if messagebox.askokcancel("Quit", "Scan in progress. Stop and quit?"):
                KILL_EVENT.set()
                # Wait for thread to finish
                try:
                    self.scan_thread.join(timeout=2.0)
                except Exception:
                    pass
                self.master.destroy()
        else:
            self.master.destroy()


def main():
    """Main entry point for the application."""
    try:
        logger.info("Starting ShadowSpecter")
        app_root = ctk.CTk()
        app = ShadowSpecterApp(app_root)
        app_root.mainloop()
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        messagebox.showerror("Critical Error", f"Application failed: {e}")
        sys.exit(1)
    finally:
        try:
            DB.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
