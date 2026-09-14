"""
gui.py
------
Kanta's Crypto Alerts · कान्ता क्रिप्टो अलर्ट्स
Complete bilingual (English + Hindi Devanagari) dark-mode GUI.
- Powered by Binance Public API (no API key required)
- Custom application logo from SVG
- Live coin icons from CoinCap CDN with local caching & fallback letter badges
- Multiple price alerts per coin (Above / Below, Loop mode, Active toggle)
- Custom audio alert selector (any system .mp3/.wav/.ogg file, defaults to assets/allert.mp3)
- Instant stop when clicking Dismiss Alert
- Background Windows toast notifications via plyer + topmost flashing popup window
- Interactive candlestick charts with volume bars, timeframe selector, and click-to-inspect price
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import time
import os
import uuid
from PIL import Image, ImageTk

from config_manager import load_config, save_config, get_alert_sound_file, DEFAULT_SOUND_FILE
from binance_client import BinanceClient
from alert_manager import AlertManager
from icon_manager import get_coin_icon, get_app_logo_image, APP_ICON_ICO, APP_ICON_PNG, ROOT_ICON_PNG

try:
    import db_manager
    import auth_manager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

try:
    import mplfinance as mpf
    import pandas as pd
    MPF_AVAILABLE = True
except ImportError:
    MPF_AVAILABLE = False
    print("[GUI] mplfinance/pandas not available — charts will be line-only.")

# ─────────────────────────────────────────────
# THEME CONSTANTS
# ─────────────────────────────────────────────
BG_MAIN        = "#0d1117"
BG_PANEL       = "#161b22"
BG_ROW         = "#0d1117"
BG_ROW_ALT     = "#111720"
BG_HOVER       = "#1c2128"
BORDER_COLOR   = "#21262d"
TEXT_PRIMARY   = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
ACCENT_GREEN   = "#3fb950"
ACCENT_RED     = "#f85149"
ACCENT_BLUE    = "#58a6ff"
ACCENT_YELLOW  = "#d29922"
FLASH_GREEN    = "#0d3321"
FLASH_RED      = "#3d0f14"
BTN_DEFAULT    = "#21262d"

# ─────────────────────────────────────────────
# CHART TIMEFRAMES
# ─────────────────────────────────────────────
CHART_TIMEFRAMES = [
    ("15m", "15m", 96),
    ("1H",  "1h",  168),
    ("4H",  "4h",  90),
    ("1D",  "1d",  90),
    ("1W",  "1w",  52),
]


def apply_window_icon(window):
    """Set window icon to custom Kanta's Crypto Alerts icon."""
    try:
        if os.path.exists(APP_ICON_ICO):
            window.iconbitmap(APP_ICON_ICO)
    except Exception:
        pass
    try:
        icon_path = ROOT_ICON_PNG if os.path.exists(ROOT_ICON_PNG) else APP_ICON_PNG
        if os.path.exists(icon_path):
            im = Image.open(icon_path)
            photo = ImageTk.PhotoImage(im)
            window.iconphoto(False, photo)
            window._icon_photo_ref = photo
    except Exception:
        pass


def fmt_price(price: float) -> str:
    if price is None:
        return "—"
    if price >= 1000:
        return f"{price:,.2f}"
    elif price >= 1:
        return f"{price:.4f}"
    elif price >= 0.01:
        return f"{price:.6f}"
    else:
        return f"{price:.8f}"


def fmt_volume(vol: float) -> str:
    if vol is None:
        return "—"
    if vol >= 1_000_000_000:
        return f"${vol/1_000_000_000:.1f}B"
    elif vol >= 1_000_000:
        return f"${vol/1_000_000:.1f}M"
    elif vol >= 1_000:
        return f"${vol/1_000:.1f}K"
    return f"${vol:.0f}"


# ═══════════════════════════════════════════════════════════════════════
# AlertPopupWindow — flashing alert notification window
# ═══════════════════════════════════════════════════════════════════════
class AlertPopupWindow(ctk.CTkToplevel):
    def __init__(self, parent, display_symbol, message, direction, loop=False,
                 sound_callback=None, sound_stop_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.display_symbol = display_symbol
        self.message = message
        self.direction = direction
        self.loop = loop
        self.sound_callback = sound_callback
        self.sound_stop_callback = sound_stop_callback
        self._flash_state = False
        self._loop_running = loop

        apply_window_icon(self)
        self.title(f"🚨 ALERT — {display_symbol} · कान्ता क्रिप्टो अलर्ट्स")
        self.geometry("560x340")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()

        color = ACCENT_GREEN if direction == "above" else ACCENT_RED
        self.configure(fg_color=BG_MAIN)

        # Header bar with app logo
        hdr_frame = ctk.CTkFrame(self, fg_color="transparent")
        hdr_frame.pack(pady=(14, 2))
        app_logo = get_app_logo_image((26, 26))
        if app_logo:
            ctk.CTkLabel(hdr_frame, image=app_logo, text="").pack(side="left", padx=6)
        ctk.CTkLabel(hdr_frame, text="Kanta's Crypto Alerts · कान्ता क्रिप्टो अलर्ट्स",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=TEXT_SECONDARY).pack(side="left")

        # Direction indicator (bilingual)
        icon = "📈" if direction == "above" else "📉"
        verb_en = "PRICE ABOVE TARGET" if direction == "above" else "PRICE BELOW TARGET"
        verb_hi = "मूल्य लक्ष्य से ऊपर निकल गया!" if direction == "above" else "मूल्य लक्ष्य से नीचे गिर गया!"
        ctk.CTkLabel(self, text=f"{icon}  {verb_en}  ·  {verb_hi}",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=color).pack(pady=(4, 4))

        # Symbol + Coin Icon
        sym_frame = ctk.CTkFrame(self, fg_color="transparent")
        sym_frame.pack(pady=(0, 4))
        coin_icon = get_coin_icon(display_symbol, size=(34, 34))
        if coin_icon:
            ctk.CTkLabel(sym_frame, image=coin_icon, text="").pack(side="left", padx=(0, 8))
        ctk.CTkLabel(sym_frame, text=f"{display_symbol}/USDT",
                     font=ctk.CTkFont("Segoe UI", 36, "bold"),
                     text_color=color).pack(side="left")

        # Message
        clean_msg = message.replace("📈", "").replace("📉", "").strip()
        ctk.CTkLabel(self, text=clean_msg,
                     font=ctk.CTkFont("Segoe UI", 12),
                     text_color=TEXT_SECONDARY,
                     wraplength=510,
                     justify="center").pack(pady=(0, 10))

        # Dismiss button (bilingual) - stops sound immediately!
        ctk.CTkButton(self, text="Dismiss Alert  ·  अलर्ट बंद करें ✕",
                      font=ctk.CTkFont("Segoe UI", 12, "bold"),
                      fg_color=color, hover_color=color,
                      text_color=BG_MAIN,
                      width=260, height=40,
                      corner_radius=8,
                      command=self._dismiss).pack(pady=4)

        if loop:
            ctk.CTkLabel(self, text="⚠ Loop mode: sound repeats until dismissed (अलर्ट बंद करने तक ध्वनि बजती रहेगी)",
                         font=ctk.CTkFont("Segoe UI", 9),
                         text_color=ACCENT_YELLOW).pack(pady=(4, 0))

        self.protocol("WM_DELETE_WINDOW", self._dismiss)
        self.bind("<Escape>", lambda e: self._dismiss())
        self.after(0, self._start_flash)
        if loop:
            self.after(500, self._loop_sound)

    def _start_flash(self):
        if not self.winfo_exists():
            return
        self._flash_state = not self._flash_state
        try:
            bg = BG_PANEL if self._flash_state else BG_MAIN
            self.configure(fg_color=bg)
        except Exception:
            return
        self.after(700, self._start_flash)

    def _loop_sound(self):
        if not self._loop_running or not self.winfo_exists():
            return
        if self.sound_callback:
            self.sound_callback()
        self.after(3000, self._loop_sound)

    def _dismiss(self):
        """Immediately stop any ongoing sound playback and close the popup window."""
        self._loop_running = False
        if self.sound_stop_callback:
            try:
                self.sound_stop_callback()
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════
# AlertRow — single row inside AlertDialog
# ═══════════════════════════════════════════════════════════════════════
class AlertRow(ctk.CTkFrame):
    def __init__(self, master, alert_data: dict, on_delete, on_change):
        super().__init__(master, fg_color=BG_PANEL, corner_radius=8)
        self.alert_data = alert_data
        self.on_delete = on_delete
        self.on_change = on_change
        self._build()

    def _build(self):
        self.columnconfigure(2, weight=1)
        pad = {"padx": 5, "pady": 6}

        # Direction toggle (Above / Below with Hindi subtext)
        self._dir_var = ctk.StringVar(value=self.alert_data.get("direction", "above"))
        dir_frame = ctk.CTkFrame(self, fg_color="transparent")
        dir_frame.grid(row=0, column=0, **pad)
        ctk.CTkRadioButton(dir_frame, text="Above (ऊपर ▲)", variable=self._dir_var, value="above",
                           text_color=ACCENT_GREEN, font=ctk.CTkFont("Segoe UI", 11),
                           command=self._save).pack(side="left", padx=(0, 8))
        ctk.CTkRadioButton(dir_frame, text="Below (नीचे ▼)", variable=self._dir_var, value="below",
                           text_color=ACCENT_RED, font=ctk.CTkFont("Segoe UI", 11),
                           command=self._save).pack(side="left")

        # Price entry
        self._price_var = ctk.StringVar(value=str(self.alert_data.get("price", "")))
        price_entry = ctk.CTkEntry(self, textvariable=self._price_var, width=120,
                                   placeholder_text="Price / मूल्य (USDT)",
                                   fg_color=BG_MAIN, border_color=BORDER_COLOR,
                                   text_color=TEXT_PRIMARY)
        price_entry.grid(row=0, column=1, **pad)
        price_entry.bind("<FocusOut>", lambda e: self._save())
        price_entry.bind("<Return>", lambda e: self._save())

        # Label entry
        self._label_var = ctk.StringVar(value=self.alert_data.get("label", ""))
        label_entry = ctk.CTkEntry(self, textvariable=self._label_var, width=160,
                                   placeholder_text="Label / विवरण (optional)",
                                   fg_color=BG_MAIN, border_color=BORDER_COLOR,
                                   text_color=TEXT_PRIMARY)
        label_entry.grid(row=0, column=2, **pad, sticky="ew")
        label_entry.bind("<FocusOut>", lambda e: self._save())
        label_entry.bind("<Return>", lambda e: self._save())

        # Loop checkbox
        self._loop_var = ctk.BooleanVar(value=self.alert_data.get("loop", False))
        ctk.CTkCheckBox(self, text="Loop (दोहराएं)", variable=self._loop_var,
                        text_color=ACCENT_YELLOW, font=ctk.CTkFont("Segoe UI", 10),
                        command=self._save, width=105).grid(row=0, column=3, **pad)

        # Active checkbox
        self._active_var = ctk.BooleanVar(value=self.alert_data.get("active", True))
        ctk.CTkCheckBox(self, text="Active (सक्रिय)", variable=self._active_var,
                        text_color=TEXT_SECONDARY, font=ctk.CTkFont("Segoe UI", 10),
                        command=self._save, width=95).grid(row=0, column=4, **pad)

        # Delete button
        ctk.CTkButton(self, text="✕", width=30, height=28,
                      fg_color=BG_MAIN, hover_color=FLASH_RED,
                      text_color=ACCENT_RED,
                      command=self._delete).grid(row=0, column=5, padx=(4, 6), pady=6)

    def _save(self):
        try:
            raw = self._price_var.get().strip().replace(",", "")
            price = float(raw) if raw else None
        except ValueError:
            price = None

        self.alert_data["direction"] = self._dir_var.get()
        self.alert_data["price"]     = price
        self.alert_data["label"]     = self._label_var.get().strip()
        self.alert_data["loop"]      = self._loop_var.get()
        self.alert_data["active"]    = self._active_var.get()
        if self.on_change:
            self.on_change()

    def _delete(self):
        if self.on_delete:
            self.on_delete(self.alert_data.get("id"))


# ═══════════════════════════════════════════════════════════════════════
# AlertDialog — manage multiple alerts for a single coin
# ═══════════════════════════════════════════════════════════════════════
class AlertDialog(ctk.CTkToplevel):
    def __init__(self, parent, coin_config: dict, on_save):
        super().__init__(parent)
        self.coin_config = coin_config
        self.on_save = on_save
        sym = coin_config.get("display_symbol", coin_config.get("symbol", ""))

        apply_window_icon(self)
        self.title(f"Price Alerts (मूल्य अलर्ट्स) — {sym}")
        self.geometry("700x500")
        self.resizable(True, True)
        self.configure(fg_color=BG_MAIN)
        self.transient(parent)
        self.grab_set()
        self.lift()
        self.focus_force()

        self._alert_rows: list[AlertRow] = []
        self._build_ui()
        self._render_alerts()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0)
        header.pack(fill="x")
        sym = self.coin_config.get("display_symbol", "")

        coin_icon = get_coin_icon(sym, size=(26, 26))
        if coin_icon:
            ctk.CTkLabel(header, image=coin_icon, text="").pack(side="left", padx=(14, 4), pady=10)

        ctk.CTkLabel(header, text=f"⚡ Manage Alerts for {sym}/USDT  ·  अलर्ट प्रबंधित करें",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=6, pady=12)

        # Column headers (bilingual)
        col_hdr = ctk.CTkFrame(self, fg_color="transparent")
        col_hdr.pack(fill="x", padx=12, pady=(10, 2))
        for text, w in [
            ("Direction\nदिशा", 185),
            ("Price (USDT)\nलक्ष्य मूल्य", 125),
            ("Label\nविवरण (नोट)", 165),
            ("Loop\nदोहराएं", 105),
            ("Active\nसक्रिय", 95),
            ("", 34)
        ]:
            ctk.CTkLabel(col_hdr, text=text, width=w,
                         font=ctk.CTkFont("Segoe UI", 9, "bold"),
                         text_color=TEXT_SECONDARY, justify="left", anchor="w").pack(side="left", padx=5)

        # Scrollable alert list
        self._scroll_frame = ctk.CTkScrollableFrame(self, fg_color=BG_MAIN)
        self._scroll_frame.pack(fill="both", expand=True, padx=12, pady=4)

        # Bottom bar
        bottom = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0)
        bottom.pack(fill="x", side="bottom")
        ctk.CTkButton(bottom, text="+ Add Alert / + अलर्ट जोड़ें",
                      font=ctk.CTkFont("Segoe UI", 12, "bold"),
                      fg_color=ACCENT_BLUE, hover_color="#3a8fd9",
                      text_color=BG_MAIN, width=170, height=36,
                      command=self._add_alert).pack(side="left", padx=14, pady=10)
        ctk.CTkButton(bottom, text="Save & Close / सहेजें और बंद करें",
                      font=ctk.CTkFont("Segoe UI", 12, "bold"),
                      fg_color=ACCENT_GREEN, hover_color="#2d8f42",
                      text_color=BG_MAIN, width=190, height=36,
                      command=self._save_and_close).pack(side="right", padx=14, pady=10)

    def _render_alerts(self):
        for w in self._alert_rows:
            w.destroy()
        self._alert_rows.clear()

        alerts = self.coin_config.get("alerts", [])
        for alert in alerts:
            row = AlertRow(
                self._scroll_frame, alert,
                on_delete=self._delete_alert,
                on_change=self._autosave,
            )
            row.pack(fill="x", pady=4, padx=4)
            self._alert_rows.append(row)

    def _add_alert(self):
        new_alert = {
            "id": str(uuid.uuid4()),
            "price": None,
            "direction": "above",
            "loop": False,
            "label": "",
            "active": True,
        }
        self.coin_config.setdefault("alerts", []).append(new_alert)
        self._render_alerts()
        self._autosave()

    def _delete_alert(self, alert_id: str):
        self.coin_config["alerts"] = [
            a for a in self.coin_config.get("alerts", []) if a.get("id") != alert_id
        ]
        self._render_alerts()
        self._autosave()

    def _autosave(self):
        if self.on_save:
            self.on_save()

    def _save_and_close(self):
        self._autosave()
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════
# CoinRow — single coin entry in the watchlist table
# ═══════════════════════════════════════════════════════════════════════
class CoinRow(ctk.CTkFrame):
    COL_WIDTHS = [120, 135, 95, 105, 105, 115, 115, 45]

    def __init__(self, master, coin_config: dict, callbacks: dict, row_index: int = 0):
        bg = BG_ROW_ALT if row_index % 2 else BG_ROW
        super().__init__(master, fg_color=bg, corner_radius=0)
        self.coin_config = coin_config
        self.callbacks = callbacks
        self._prev_price = None
        self._normal_price_color = TEXT_PRIMARY
        self._bg = bg
        self._build()

    def _build(self):
        for i, w in enumerate(self.COL_WIDTHS):
            self.columnconfigure(i, minsize=w)

        sym = self.coin_config.get("display_symbol", self.coin_config.get("symbol", "?"))
        pad = {"padx": 6, "pady": 8}

        # Coin Icon + Symbol + USDT badge
        sym_frame = ctk.CTkFrame(self, fg_color="transparent")
        sym_frame.grid(row=0, column=0, **pad, sticky="w")

        self.icon_label = ctk.CTkLabel(sym_frame, text="", width=24, height=24)
        coin_icon = get_coin_icon(sym, on_loaded_callback=self._on_icon_loaded, size=(24, 24))
        self.icon_label.configure(image=coin_icon)
        self.icon_label.pack(side="left", padx=(0, 6))

        ctk.CTkLabel(sym_frame, text=sym,
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(sym_frame, text="/USDT",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=TEXT_SECONDARY).pack(side="left", padx=(2, 0), pady=(3, 0))

        # Price
        self.price_label = ctk.CTkLabel(self, text="Loading…",
                                         font=ctk.CTkFont("Segoe UI", 14, "bold"),
                                         text_color=TEXT_PRIMARY,
                                         width=self.COL_WIDTHS[1], anchor="w")
        self.price_label.grid(row=0, column=1, **pad, sticky="w")

        # 24h Change %
        self.change_label = ctk.CTkLabel(self, text="—",
                                          font=ctk.CTkFont("Segoe UI", 12),
                                          text_color=TEXT_SECONDARY,
                                          width=self.COL_WIDTHS[2], anchor="w")
        self.change_label.grid(row=0, column=2, **pad, sticky="w")

        # 24h High
        self.high_label = ctk.CTkLabel(self, text="—",
                                        font=ctk.CTkFont("Segoe UI", 11),
                                        text_color=TEXT_SECONDARY,
                                        width=self.COL_WIDTHS[3], anchor="w")
        self.high_label.grid(row=0, column=3, **pad, sticky="w")

        # 24h Low
        self.low_label = ctk.CTkLabel(self, text="—",
                                       font=ctk.CTkFont("Segoe UI", 11),
                                       text_color=TEXT_SECONDARY,
                                       width=self.COL_WIDTHS[4], anchor="w")
        self.low_label.grid(row=0, column=4, **pad, sticky="w")

        # 24h Volume
        self.vol_label = ctk.CTkLabel(self, text="—",
                                       font=ctk.CTkFont("Segoe UI", 11),
                                       text_color=TEXT_SECONDARY,
                                       width=self.COL_WIDTHS[5], anchor="w")
        self.vol_label.grid(row=0, column=5, **pad, sticky="w")

        # Alerts button
        alert_count = len(self.coin_config.get("alerts", []))
        self.alerts_btn = ctk.CTkButton(
            self, text=f"⚡ Alerts ({alert_count})",
            font=ctk.CTkFont("Segoe UI", 11),
            width=self.COL_WIDTHS[6], height=30,
            fg_color=BTN_DEFAULT, hover_color=BG_HOVER,
            text_color=ACCENT_YELLOW, corner_radius=6,
            command=self._open_alerts
        )
        self.alerts_btn.grid(row=0, column=6, padx=4, pady=6)

        # Chart button
        ctk.CTkButton(
            self, text="📈",
            font=ctk.CTkFont("Segoe UI", 14),
            width=40, height=30,
            fg_color=BTN_DEFAULT, hover_color=BG_HOVER,
            text_color=ACCENT_BLUE, corner_radius=6,
            command=self._show_chart
        ).grid(row=0, column=7, padx=(2, 4), pady=6)

        # Remove button
        ctk.CTkButton(
            self, text="✕",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            width=30, height=30,
            fg_color=BTN_DEFAULT, hover_color=FLASH_RED,
            text_color=ACCENT_RED, corner_radius=6,
            command=self._remove
        ).grid(row=0, column=8, padx=(0, 8), pady=6)

    def _on_icon_loaded(self, ctk_img):
        try:
            self.after(0, lambda: self.icon_label.configure(image=ctk_img))
        except Exception:
            pass

    # ── Data Update ──────────────────────────────────────────────────

    def update_data(self, ticker: dict | None):
        if ticker is None:
            self.price_label.configure(text="Error", text_color=ACCENT_RED)
            return

        price = ticker.get("price")
        change_pct = ticker.get("change_pct", 0.0)
        high = ticker.get("high")
        low = ticker.get("low")
        vol = ticker.get("quote_volume", ticker.get("volume"))

        # Flash price on change
        if self._prev_price is not None and price is not None:
            if price > self._prev_price:
                self._flash_price(ACCENT_GREEN)
            elif price < self._prev_price:
                self._flash_price(ACCENT_RED)
        self._prev_price = price

        self.price_label.configure(text=f"{fmt_price(price)} USDT", text_color=TEXT_PRIMARY)

        # Change %
        sign = "+" if change_pct > 0 else ""
        c_color = ACCENT_GREEN if change_pct >= 0 else ACCENT_RED
        self.change_label.configure(text=f"{sign}{change_pct:.2f}%", text_color=c_color)

        self.high_label.configure(text=fmt_price(high))
        self.low_label.configure(text=fmt_price(low))
        self.vol_label.configure(text=fmt_volume(vol))

    def _flash_price(self, color: str):
        self.price_label.configure(text_color=color)
        self.after(600, lambda: self.price_label.configure(text_color=TEXT_PRIMARY))

    def flash_row_alert(self, direction: str):
        flash_bg = FLASH_GREEN if direction == "above" else FLASH_RED
        self.configure(fg_color=flash_bg)
        self.after(500, lambda: self.configure(fg_color=self._bg))
        self.after(1000, lambda: self.configure(fg_color=flash_bg))
        self.after(1500, lambda: self.configure(fg_color=self._bg))

    def update_alert_count(self):
        alert_count = len(self.coin_config.get("alerts", []))
        self.alerts_btn.configure(text=f"⚡ Alerts ({alert_count})")

    # ── Callbacks ────────────────────────────────────────────────────

    def _open_alerts(self):
        if self.callbacks.get("on_alerts"):
            self.callbacks["on_alerts"](self.coin_config)

    def _show_chart(self):
        if self.callbacks.get("on_chart"):
            self.callbacks["on_chart"](self.coin_config, self._prev_price)

    def _remove(self):
        if self.callbacks.get("on_remove"):
            self.callbacks["on_remove"](self.coin_config.get("symbol"))


# ═══════════════════════════════════════════════════════════════════════
# ChartWindow — interactive candlestick charts (mplfinance)
# ═══════════════════════════════════════════════════════════════════════
class ChartWindow(ctk.CTkToplevel):
    def __init__(self, parent, binance_client: BinanceClient,
                 coin_config: dict, current_price=None):
        super().__init__(parent)
        self.binance_client = binance_client
        self.coin_config = coin_config
        self.symbol = coin_config.get("symbol", "")
        self.display_symbol = coin_config.get("display_symbol", self.symbol)
        self.current_price = current_price
        self._tf_idx = 3   # Default: 1D
        self._canvas = None
        self._fig = None
        self._axes = None
        self._df = None
        self._click_line = None
        self._click_text = None
        self._live_line = None
        self._loading = False

        apply_window_icon(self)
        self.title(f"{self.display_symbol}/USDT — Interactive Chart · चार्ट")
        self.geometry("1080x700")
        self.configure(fg_color=BG_MAIN)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()
        self.after(100, self._load_chart)

    def _build_ui(self):
        # Header bar
        header = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0)
        header.pack(fill="x")

        coin_icon = get_coin_icon(self.display_symbol, size=(28, 28))
        if coin_icon:
            ctk.CTkLabel(header, image=coin_icon, text="").pack(side="left", padx=(14, 4), pady=10)

        ctk.CTkLabel(header, text=f"{self.display_symbol}",
                     font=ctk.CTkFont("Segoe UI", 22, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=(4, 2), pady=12)
        ctk.CTkLabel(header, text="/USDT",
                     font=ctk.CTkFont("Segoe UI", 14),
                     text_color=TEXT_SECONDARY).pack(side="left", pady=(14, 0))

        if self.current_price is not None:
            self.live_price_badge = ctk.CTkLabel(
                header, text=f"  {fmt_price(self.current_price)} USDT",
                font=ctk.CTkFont("Segoe UI", 16, "bold"),
                text_color=ACCENT_GREEN
            )
            self.live_price_badge.pack(side="left", padx=10, pady=12)

        # Button to toggle/mark live price line on chart (bilingual)
        ctk.CTkButton(
            header, text="📍 Show Live Price / लाइव मूल्य",
            width=175, height=30,
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            fg_color="#1f2937", hover_color="#374151",
            text_color=ACCENT_GREEN,
            border_width=1, border_color=ACCENT_GREEN,
            corner_radius=6,
            command=self._toggle_live_price_line
        ).pack(side="left", padx=10, pady=10)

        # Timeframe buttons
        self._tf_buttons = []
        tf_frame = ctk.CTkFrame(header, fg_color="transparent")
        tf_frame.pack(side="right", padx=10, pady=8)
        for i, (label, _, _) in enumerate(CHART_TIMEFRAMES):
            is_active = (i == self._tf_idx)
            btn = ctk.CTkButton(
                tf_frame, text=label,
                width=48, height=32,
                font=ctk.CTkFont("Segoe UI", 11, "bold" if is_active else "normal"),
                fg_color=ACCENT_BLUE if is_active else BTN_DEFAULT,
                hover_color="#3a8fd9",
                text_color=BG_MAIN if is_active else TEXT_SECONDARY,
                corner_radius=6,
                command=lambda idx=i: self._switch_tf(idx)
            )
            btn.pack(side="left", padx=3)
            self._tf_buttons.append(btn)

        # Interactive inspection bar (bilingual)
        self.inspect_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=30)
        self.inspect_frame.pack(fill="x", padx=0, pady=(1, 0))
        self.inspect_bar = ctk.CTkLabel(
            self.inspect_frame,
            text="💡 Click anywhere on chart to inspect price / मूल्य व कैंडल जांचने के लिए चार्ट पर क्लिक करें",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=ACCENT_BLUE,
            anchor="w"
        )
        self.inspect_bar.pack(side="left", padx=16, pady=4)

        # Status / loading label
        self.status_label = ctk.CTkLabel(self, text="Loading chart data… (डेटा लोड हो रहा है)",
                                          font=ctk.CTkFont("Segoe UI", 11),
                                          text_color=TEXT_SECONDARY)
        self.status_label.pack(pady=4)

        # Chart container
        self.chart_frame = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        self.chart_frame.pack(fill="both", expand=True, padx=0, pady=0)

    def _switch_tf(self, idx: int):
        if self._loading:
            return
        self._tf_idx = idx
        for i, btn in enumerate(self._tf_buttons):
            is_active = (i == idx)
            btn.configure(
                fg_color=ACCENT_BLUE if is_active else BTN_DEFAULT,
                text_color=BG_MAIN if is_active else TEXT_SECONDARY,
                font=ctk.CTkFont("Segoe UI", 11, "bold" if is_active else "normal"),
            )
        self._load_chart()

    def _load_chart(self):
        self._loading = True
        self.status_label.configure(text="Fetching candle data… (कैंडल डेटा प्राप्त कर रहे हैं)", text_color=ACCENT_YELLOW)
        label, interval, limit = CHART_TIMEFRAMES[self._tf_idx]
        t = threading.Thread(target=self._fetch_and_render, args=(interval, limit, label), daemon=True)
        t.start()

    def _fetch_and_render(self, interval: str, limit: int, label: str):
        candles = self.binance_client.get_klines(self.symbol, interval, limit)
        self.after(0, lambda: self._render(candles, interval, label))

    def _render(self, candles, interval: str, label: str):
        self._loading = False

        if not candles or len(candles) < 5:
            self.status_label.configure(
                text=f"Could not load {label} chart data. (डेटा प्राप्त नहीं हो सका)", text_color=ACCENT_RED)
            return

        for child in self.chart_frame.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass

        if self._fig:
            try:
                plt.close(self._fig)
            except Exception:
                pass

        self._click_line = None
        self._click_text = None
        self._live_line = None

        if not MPF_AVAILABLE:
            self._render_line_fallback(candles, label)
            return

        self.status_label.configure(text="", text_color=TEXT_SECONDARY)

        try:
            import pandas as pd
            import mplfinance as mpf

            df = pd.DataFrame(candles)
            df["Date"] = pd.to_datetime(df["time"], unit="s")
            df = df.set_index("Date")
            df = df.rename(columns={
                "open": "Open", "high": "High",
                "low": "Low", "close": "Close", "volume": "Volume"
            })
            self._df = df

            # Custom dark style
            mc = mpf.make_marketcolors(
                up=ACCENT_GREEN, down=ACCENT_RED,
                edge="inherit", wick="inherit",
                volume={"up": "#1a3a25", "down": "#3a1a1a"},
            )
            style = mpf.make_mpf_style(
                base_mpf_style="nightclouds",
                marketcolors=mc,
                facecolor=BG_MAIN,
                edgecolor=BORDER_COLOR,
                figcolor=BG_MAIN,
                gridcolor=BORDER_COLOR,
                gridstyle="-",
                gridaxis="both",
                y_on_right=True,
                rc={
                    "axes.labelcolor": TEXT_SECONDARY,
                    "xtick.color": TEXT_SECONDARY,
                    "ytick.color": TEXT_SECONDARY,
                    "axes.edgecolor": BORDER_COLOR,
                    "figure.facecolor": BG_MAIN,
                    "axes.facecolor": BG_MAIN,
                }
            )

            self._fig, axes = mpf.plot(
                df, type="candle", volume=True,
                style=style, returnfig=True,
                figsize=(13, 7.5),
                title=f"\n{self.display_symbol}/USDT  [{label}]",
            )
            self._axes = axes
            if self._fig.texts:
                self._fig.texts[0].set_color(TEXT_SECONDARY)
                self._fig.texts[0].set_fontsize(12)

            self._canvas = FigureCanvasTkAgg(self._fig, master=self.chart_frame)
            self._canvas.draw()
            widget = self._canvas.get_tk_widget()
            widget.pack(fill="both", expand=True)

            self._canvas.mpl_connect("button_press_event", self._on_chart_clicked)

            # Toolbar for zoom/pan
            toolbar_frame = tk.Frame(self.chart_frame, bg=BG_PANEL)
            toolbar_frame.pack(fill="x")
            toolbar = NavigationToolbar2Tk(self._canvas, toolbar_frame)
            toolbar.config(background=BG_PANEL)
            toolbar._message_label.config(background=BG_PANEL, foreground=TEXT_SECONDARY)
            for btn in toolbar.winfo_children():
                try:
                    btn.config(background=BG_PANEL)
                except Exception:
                    pass
            toolbar.update()

        except Exception as e:
            print(f"[Chart] Render error: {e}")
            self.status_label.configure(
                text=f"Chart render error: {e}", text_color=ACCENT_RED)

    def _render_line_fallback(self, candles, label: str):
        """Fallback: simple line chart if mplfinance is unavailable."""
        import matplotlib.dates as mdates
        import datetime

        timestamps = [datetime.datetime.fromtimestamp(c["time"]) for c in candles]
        prices = [c["close"] for c in candles]

        self._fig, ax = plt.subplots(figsize=(12, 6), facecolor=BG_MAIN)
        self._axes = [ax]
        ax.set_facecolor(BG_MAIN)
        ax.plot(timestamps, prices, color=ACCENT_GREEN, linewidth=1.5)
        ax.fill_between(timestamps, prices, alpha=0.08, color=ACCENT_GREEN)
        ax.tick_params(colors=TEXT_SECONDARY, labelsize=9)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax.spines[:].set_color(BORDER_COLOR)
        ax.set_title(f"{self.display_symbol}/USDT [{label}]", color=TEXT_SECONDARY)
        plt.tight_layout()

        self._canvas = FigureCanvasTkAgg(self._fig, master=self.chart_frame)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill="both", expand=True)
        self._canvas.mpl_connect("button_press_event", self._on_chart_clicked)

    def _on_chart_clicked(self, event):
        """Show clicked price and candle information upon clicking the chart."""
        if not event.inaxes or event.ydata is None:
            return

        price_ax = self._axes[0] if self._axes else None
        if not price_ax:
            return

        clicked_price = float(event.ydata)

        if self._click_line and self._click_line in price_ax.lines:
            self._click_line.remove()
        if self._click_text and self._click_text in price_ax.texts:
            self._click_text.remove()

        self._click_line = price_ax.axhline(
            clicked_price, color=ACCENT_YELLOW, linestyle="--", linewidth=1.2, alpha=0.85
        )
        xlim = price_ax.get_xlim()
        self._click_text = price_ax.text(
            xlim[1], clicked_price, f" {fmt_price(clicked_price)} ",
            color=BG_MAIN, backgroundcolor=ACCENT_YELLOW,
            fontsize=9, fontweight="bold", va="center"
        )

        candle_info = ""
        if self._df is not None and event.xdata is not None:
            idx = int(round(event.xdata))
            if 0 <= idx < len(self._df):
                c_row = self._df.iloc[idx]
                dt = self._df.index[idx].strftime("%Y-%m-%d %H:%M")
                candle_info = (
                    f"  │  Candle [{dt}]: O: {fmt_price(c_row['Open'])} · "
                    f"H: {fmt_price(c_row['High'])} · L: {fmt_price(c_row['Low'])} · "
                    f"C: {fmt_price(c_row['Close'])} · Vol: {fmt_volume(c_row['Volume'])}"
                )

        diff_str = ""
        if self.current_price is not None and self.current_price > 0:
            diff_pct = ((clicked_price - self.current_price) / self.current_price) * 100
            diff_sign = "+" if diff_pct > 0 else ""
            diff_str = f"  (vs Live: {diff_sign}{diff_pct:.2f}%)"

        self.inspect_bar.configure(
            text=f"📍 Price / मूल्य: {fmt_price(clicked_price)} USDT{diff_str}{candle_info}",
            text_color="#ffffff"
        )
        if self._canvas:
            self._canvas.draw_idle()

    def _toggle_live_price_line(self):
        if self.current_price is None or not self._axes:
            return

        price_ax = self._axes[0]
        if self._live_line and self._live_line in price_ax.lines:
            self._live_line.remove()
            self._live_line = None
            self.inspect_bar.configure(
                text="Removed Live Price marker line. (लाइव मूल्य रेखा हटाई गई)", text_color=TEXT_SECONDARY
            )
        else:
            self._live_line = price_ax.axhline(
                self.current_price, color=ACCENT_GREEN, linestyle=":", linewidth=1.5, alpha=0.9
            )
            self.inspect_bar.configure(
                text=f"🟢 Live Price / लाइव मूल्य: {fmt_price(self.current_price)} USDT",
                text_color=ACCENT_GREEN
            )
        if self._canvas:
            self._canvas.draw_idle()

    def _on_close(self):
        if self._fig:
            try:
                plt.close(self._fig)
            except Exception:
                pass
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════
# SuggestionDropdown — autocomplete popup below the search entry
# ═══════════════════════════════════════════════════════════════════════
class SuggestionDropdown:
    def __init__(self, entry_widget, on_select):
        self.entry_widget = entry_widget
        self.on_select = on_select
        self._win = None
        self._listbox = None
        self._suggestions = []

    def show(self, suggestions: list):
        self._suggestions = suggestions
        self.hide()
        if not suggestions:
            return

        entry = self.entry_widget
        x = entry.winfo_rootx()
        y = entry.winfo_rooty() + entry.winfo_height() + 2
        w = max(entry.winfo_width(), 280)
        h = min(len(suggestions) * 28 + 4, 220)

        self._win = tk.Toplevel()
        self._win.overrideredirect(True)
        self._win.geometry(f"{w}x{h}+{x}+{y}")
        self._win.configure(bg=BG_PANEL)
        self._win.attributes("-topmost", True)

        self._listbox = tk.Listbox(
            self._win,
            bg=BG_PANEL, fg=TEXT_PRIMARY,
            selectbackground=ACCENT_BLUE, selectforeground=BG_MAIN,
            activestyle="none",
            font=("Segoe UI", 11),
            border=0, relief="flat",
            highlightthickness=0,
        )
        self._listbox.pack(fill="both", expand=True, padx=2, pady=2)

        for base, full_sym in suggestions:
            self._listbox.insert(tk.END, f"  ●  {base}  —  {full_sym}")

        self._listbox.bind("<ButtonRelease-1>", self._pick)
        self._listbox.bind("<Return>", self._pick)

    def _pick(self, event=None):
        sel = self._listbox.curselection()
        if sel and self._suggestions:
            idx = sel[0]
            base, full_sym = self._suggestions[idx]
            self.on_select(base, full_sym)
        self.hide()

    def hide(self):
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None
            self._listbox = None

    def is_visible(self):
        return self._win is not None


# ═══════════════════════════════════════════════════════════════════════
# App — Main Application Window
# ═══════════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self, current_user: dict | None = None, on_close_callback=None):
        super().__init__()
        apply_window_icon(self)
        self.title("Kanta's Crypto Alerts  ·  कान्ता क्रिप्टो अलर्ट्स")
        self.geometry("1180x720")
        self.minsize(980, 560)
        self.configure(fg_color=BG_MAIN)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Current logged-in user (from login_screen or None for legacy)
        self.current_user = current_user or {}
        self._user_id: int | None = current_user.get("id") if current_user else None
        self._on_close_callback = on_close_callback

        self.config = load_config()
        self.binance_client = BinanceClient()
        self.alert_manager = AlertManager(
            gui_callback_visual_alert=self._on_visual_alert,
            gui_callback_popup_alert=self._on_popup_alert,
            sound_enabled_check_callback=lambda: self.config.get("sound_enabled", True),
            get_sound_file_callback=lambda: get_alert_sound_file(self.config),
            user_id=self._user_id,
        )

        self.coin_rows: dict[str, CoinRow] = {}   # binance_symbol -> CoinRow
        self._search_thread = None
        self._fetch_thread = None
        self._stop_event = threading.Event()
        self._db_sync_lock = threading.Lock()
        self._last_local_edit_time = 0.0
        self._suggestion_dropdown: SuggestionDropdown | None = None
        self._current_prices: dict = {}  # cache for chart windows

        self._build_ui()
        self._load_coins_to_gui()
        self._start_fetching()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ──────────────────────────────────────────────────────────────────
    # UI Construction
    # ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0)
        hdr.pack(fill="x")

        # Custom App Logo
        app_logo = get_app_logo_image((36, 36))
        if app_logo:
            ctk.CTkLabel(hdr, image=app_logo, text="").pack(side="left", padx=(16, 8), pady=8)

        title_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        title_frame.pack(side="left", pady=8)

        ctk.CTkLabel(title_frame, text="Kanta's Crypto Alerts",
                     font=ctk.CTkFont("Segoe UI", 17, "bold"),
                     text_color=ACCENT_GREEN).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="कान्ता क्रिप्टो अलर्ट्स",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=TEXT_SECONDARY).pack(anchor="w")

        self.live_dot = ctk.CTkLabel(hdr, text="● LIVE · लाइव",
                                      font=ctk.CTkFont("Segoe UI", 10, "bold"),
                                      text_color=ACCENT_GREEN)
        self.live_dot.pack(side="left", padx=16, pady=12)

        ctk.CTkLabel(hdr, text="Binance Public API · No Key Required (बिना किसी API कुंजी के)",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=TEXT_SECONDARY).pack(side="left", pady=12)

        # ── Logged-in user + logout (right side of header) ────────────
        user_name = self.current_user.get("display_name", "")
        if user_name:
            user_frame = ctk.CTkFrame(hdr, fg_color="transparent")
            user_frame.pack(side="right", padx=10, pady=6)

            # Profile picture (if available)
            user_avatar = None
            try:
                pic_bytes = self.current_user.get("profile_pic")
                if not pic_bytes and self._user_id and DB_AVAILABLE:
                    full_u = db_manager.get_user_by_id(self._user_id)
                    if full_u and full_u.get("profile_pic"):
                        pic_bytes = full_u["profile_pic"]
                        self.current_user["profile_pic"] = pic_bytes
                if pic_bytes:
                    import io
                    import PIL.ImageDraw as ImageDraw
                    im = Image.open(io.BytesIO(bytes(pic_bytes))).convert("RGBA").resize((30, 30), Image.LANCZOS)
                    mask = Image.new("L", (30, 30), 0)
                    ImageDraw.Draw(mask).ellipse((0, 0, 30, 30), fill=255)
                    im.putalpha(mask)
                    user_avatar = ctk.CTkImage(im, size=(30, 30))
            except Exception:
                pass

            if user_avatar:
                ctk.CTkLabel(user_frame, image=user_avatar, text="").pack(side="left", padx=(0, 6))

            ctk.CTkLabel(user_frame,
                         text=f"{'👤 ' if not user_avatar else ''}{user_name}",
                         font=ctk.CTkFont("Segoe UI", 11, "bold"),
                         text_color=ACCENT_BLUE).pack(side="left", padx=(0, 8))
            ctk.CTkButton(user_frame, text="🚪 Logout",
                          width=75, height=28,
                          font=ctk.CTkFont("Segoe UI", 10),
                          fg_color=BTN_DEFAULT, hover_color="#3d0f14",
                          text_color=ACCENT_RED,
                          corner_radius=6,
                          command=self._logout).pack(side="left")

        # ── Search / Add Coin (Bilingual) ──────────────────────────────
        search_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=8)
        search_frame.pack(fill="x", padx=12, pady=(10, 4))

        search_lbl_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_lbl_frame.pack(side="left", padx=(12, 6), pady=8)
        ctk.CTkLabel(search_lbl_frame, text="Add Coin / कॉइन जोड़ें:",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(search_lbl_frame, text="कॉइन खोजें व जोड़ें",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=TEXT_SECONDARY).pack(anchor="w")

        self.search_entry = ctk.CTkEntry(
            search_frame,
            width=220, height=34,
            placeholder_text="e.g. BTC, ETH, SOL... (खोजें)",
            fg_color=BG_MAIN, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont("Segoe UI", 12)
        )
        self.search_entry.pack(side="left", padx=4, pady=10)
        self.search_entry.bind("<KeyRelease>", self._on_search_key)
        self.search_entry.bind("<Escape>", lambda e: self._hide_suggestions())
        self.search_entry.bind("<Down>", self._focus_suggestions)
        self.search_entry.bind("<Return>", lambda e: self._add_coin_action())

        self._suggestion_dropdown = SuggestionDropdown(
            self.search_entry, on_select=self._on_suggestion_select
        )

        ctk.CTkButton(
            search_frame, text="+ Add / जोड़ें",
            width=105, height=34,
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=ACCENT_BLUE, hover_color="#3a8fd9",
            text_color=BG_MAIN,
            command=self._add_coin_action
        ).pack(side="left", padx=(6, 8), pady=10)

        # ── Table Header (Bilingual) ──────────────────────────────────
        hdr_row = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0)
        hdr_row.pack(fill="x", padx=12, pady=(6, 0))
        col_labels = [
            ("Coin\nकॉइन", 120),
            ("Price (USDT)\nमूल्य", 135),
            ("24h Change\n24घं बदलाव", 95),
            ("24h High\nउच्चतम", 105),
            ("24h Low\nन्यूनतम", 105),
            ("Volume\nवॉल्यूम", 115),
            ("Alerts\nअलर्ट्स", 115),
            ("Chart\nचार्ट", 45),
            ("Del\nहटाएं", 36),
        ]
        for text, w in col_labels:
            ctk.CTkLabel(hdr_row, text=text, width=w,
                         font=ctk.CTkFont("Segoe UI", 9, "bold"),
                         text_color=TEXT_SECONDARY, justify="left", anchor="w").pack(side="left", padx=6, pady=4)

        # ── Coin List (scrollable) ────────────────────────────────────
        self.coins_frame = ctk.CTkScrollableFrame(
            self, fg_color=BG_MAIN, corner_radius=0,
        )
        self.coins_frame.pack(fill="both", expand=True, padx=12, pady=(2, 4))

        # ── Bottom Bar (Bilingual with Custom Sound Selector) ─────────
        bottom = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0)
        bottom.pack(fill="x", side="bottom")

        # Refresh rate
        ref_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        ref_frame.pack(side="left", padx=(12, 6), pady=6)
        ctk.CTkLabel(ref_frame, text="Refresh / रिफ्रेश (s):",
                     font=ctk.CTkFont("Segoe UI", 10, "bold"),
                     text_color=TEXT_SECONDARY).pack(side="left", padx=(0, 4))
        self._interval_entry = ctk.CTkEntry(
            ref_frame, width=46, height=28,
            fg_color=BG_MAIN, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, font=ctk.CTkFont("Segoe UI", 11)
        )
        self._interval_entry.insert(0, str(self.config.get("refresh_interval_seconds", 10)))
        self._interval_entry.pack(side="left")
        self._interval_entry.bind("<Return>", self._update_interval)
        self._interval_entry.bind("<FocusOut>", self._update_interval)

        # Sound toggle
        self._sound_var = ctk.BooleanVar(value=self.config.get("sound_enabled", True))
        ctk.CTkCheckBox(bottom, text="Sound / ध्वनि",
                        variable=self._sound_var,
                        text_color=TEXT_SECONDARY,
                        font=ctk.CTkFont("Segoe UI", 10, "bold"),
                        command=self._toggle_sound).pack(side="left", padx=8, pady=6)

        # Custom alert sound selector
        sound_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        sound_frame.pack(side="left", padx=8, pady=6)
        ctk.CTkLabel(sound_frame, text="Alert Sound / अलर्ट ध्वनि:",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=TEXT_SECONDARY).pack(side="left", padx=(0, 4))

        self.sound_name_label = ctk.CTkLabel(
            sound_frame, text=self._get_sound_display_name(),
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color=ACCENT_YELLOW
        )
        self.sound_name_label.pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            sound_frame, text="📁 Choose / चुनें",
            width=85, height=26,
            font=ctk.CTkFont("Segoe UI", 10),
            fg_color=BTN_DEFAULT, hover_color=BG_HOVER,
            text_color=TEXT_PRIMARY, corner_radius=5,
            command=self._choose_sound_file
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            sound_frame, text="▶ Test / चलाएं",
            width=80, height=26,
            font=ctk.CTkFont("Segoe UI", 10),
            fg_color=BTN_DEFAULT, hover_color=BG_HOVER,
            text_color=ACCENT_GREEN, corner_radius=5,
            command=self._test_sound
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            sound_frame, text="↺ Reset / रीसेट",
            width=75, height=26,
            font=ctk.CTkFont("Segoe UI", 10),
            fg_color=BTN_DEFAULT, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, corner_radius=5,
            command=self._reset_sound_file
        ).pack(side="left", padx=2)

        # Status
        self.status_label = ctk.CTkLabel(
            bottom, text="Connecting to Binance... (बायनेन्स से जुड़ रहे हैं...)",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=TEXT_SECONDARY, anchor="e"
        )
        self.status_label.pack(side="right", padx=12, pady=6, fill="x", expand=True)

        self.bind("<Button-1>", self._on_root_click)

    # ── Sound Picker Methods ──────────────────────────────────────────

    def _get_sound_display_name(self) -> str:
        p = self.config.get("alert_sound_path", "")
        if p and os.path.isfile(p):
            return os.path.basename(p)
        return "allert.mp3 (Default)"

    def _choose_sound_file(self):
        chosen = filedialog.askopenfilename(
            title="Select Alert Sound / अलर्ट ध्वनि चुनें",
            filetypes=[
                ("Audio Files (*.mp3, *.wav, *.ogg)", "*.mp3 *.wav *.ogg"),
                ("All Files (*.*)", "*.*"),
            ]
        )
        if chosen and os.path.isfile(chosen):
            self.config["alert_sound_path"] = chosen
            save_config(self.config)
            self.sound_name_label.configure(text=self._get_sound_display_name())
            self.status_label.configure(
                text=f"Alert sound: {os.path.basename(chosen)} (अलर्ट ध्वनि सेट की गई)",
                text_color=ACCENT_GREEN
            )

    def _test_sound(self):
        self.alert_manager.play_sound_once()

    def _reset_sound_file(self):
        self.config["alert_sound_path"] = ""
        save_config(self.config)
        self.sound_name_label.configure(text=self._get_sound_display_name())
        self.status_label.configure(
            text="Reset alert sound to default (allert.mp3) / डिफ़ॉल्ट ध्वनि रीसेट",
            text_color=TEXT_SECONDARY
        )

    # ──────────────────────────────────────────────────────────────────
    # Coin Search / Add
    # ──────────────────────────────────────────────────────────────────

    def _on_search_key(self, event=None):
        query = self.search_entry.get().strip()
        if len(query) < 1:
            self._hide_suggestions()
            return
        if self._search_thread and self._search_thread.is_alive():
            return
        self._search_thread = threading.Thread(
            target=self._do_search, args=(query,), daemon=True
        )
        self._search_thread.start()

    def _do_search(self, query: str):
        results = self.binance_client.search_coins(query)
        self.after(0, lambda: self._show_suggestions(results))

    def _show_suggestions(self, suggestions: list):
        if suggestions:
            self._suggestion_dropdown.show(suggestions)
        else:
            self._hide_suggestions()

    def _hide_suggestions(self):
        if self._suggestion_dropdown:
            self._suggestion_dropdown.hide()

    def _focus_suggestions(self, event=None):
        if self._suggestion_dropdown and self._suggestion_dropdown._listbox:
            self._suggestion_dropdown._listbox.focus_set()

    def _on_suggestion_select(self, base: str, full_sym: str):
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, base)
        self._hide_suggestions()
        self._add_coin_with_symbol(base, full_sym)

    def _on_root_click(self, event=None):
        if self._suggestion_dropdown:
            self._suggestion_dropdown.hide()

    def _add_coin_action(self, event=None):
        query = self.search_entry.get().strip().upper()
        if not query:
            return
        self._hide_suggestions()
        full_sym = f"{query}USDT"
        self._add_coin_with_symbol(query, full_sym)

    def _add_coin_with_symbol(self, display_symbol: str, binance_symbol: str):
        if binance_symbol in self.coin_rows:
            self.status_label.configure(text=f"{display_symbol}/USDT already tracked. (पहले से ट्रैक किया गया है)")
            self.search_entry.delete(0, tk.END)
            return

        self.status_label.configure(text=f"Validating {binance_symbol}… (जांच हो रही है)", text_color=ACCENT_YELLOW)

        def _validate():
            ok = self.binance_client.validate_symbol(binance_symbol)
            self.after(0, lambda: self._finish_add(display_symbol, binance_symbol, ok))

        t = threading.Thread(target=_validate, daemon=True)
        t.start()

    def _finish_add(self, display_symbol: str, binance_symbol: str, valid: bool):
        if not valid:
            self.status_label.configure(
                text=f"Symbol {binance_symbol} not found on Binance. (कॉइन नहीं मिला)",
                text_color=ACCENT_RED
            )
            return

        new_coin = {
            "symbol": binance_symbol,
            "display_symbol": display_symbol,
            "alerts": [],
        }
        self.config["watched_coins"].append(new_coin)
        save_config(self.config)
        self._sync_coins_to_db()

        self._add_coin_row(new_coin, row_index=len(self.coin_rows))
        self.search_entry.delete(0, tk.END)
        self.status_label.configure(
            text=f"Added {display_symbol}/USDT ({display_symbol} जोड़ा गया)", text_color=ACCENT_GREEN
        )

        t = threading.Thread(target=self._fetch_single_now, args=(binance_symbol,), daemon=True)
        t.start()

    # ──────────────────────────────────────────────────────────────────
    # Watchlist Management
    # ──────────────────────────────────────────────────────────────────

    def _load_coins_to_gui(self):
        """Load coins from DB if logged in, else fall back to local config."""
        for widget in self.coins_frame.winfo_children():
            widget.destroy()
        self.coin_rows.clear()

        if self._user_id and DB_AVAILABLE:
            try:
                db_coins = db_manager.load_watched_coins(self._user_id)
                if db_coins:
                    self.config["watched_coins"] = db_coins
                    print(f"[App] Loaded {len(db_coins)} coins from DB for user {self._user_id}")
            except Exception as e:
                print(f"[App] DB load error, using local config: {e}")

        for i, coin in enumerate(self.config.get("watched_coins", [])):
            self._add_coin_row(coin, row_index=i)

    def _add_coin_row(self, coin_config: dict, row_index: int = 0):
        sym = coin_config.get("symbol")
        if not sym:
            return

        row = CoinRow(
            self.coins_frame,
            coin_config=coin_config,
            callbacks={
                "on_alerts": self._open_alerts_dialog,
                "on_chart":  self._open_chart_window,
                "on_remove": self._remove_coin,
            },
            row_index=row_index,
        )
        row.pack(fill="x", pady=2)
        self.coin_rows[sym] = row

    def _remove_coin(self, binance_symbol: str):
        if not binance_symbol:
            return
        disp = self.binance_client.get_display_symbol(binance_symbol)
        msg = f"Remove {disp}/USDT from watchlist?\n(क्या आप {disp} को सूची से हटाना चाहते हैं?)"
        if not messagebox.askyesno("Remove Coin (कॉइन हटाएं)", msg, parent=self):
            return

        # 1. Update UI and local config INSTANTLY (0ms lag, no freeze)
        if binance_symbol in self.coin_rows:
            self.coin_rows[binance_symbol].destroy()
            del self.coin_rows[binance_symbol]

        self.config["watched_coins"] = [
            c for c in self.config.get("watched_coins", [])
            if c.get("symbol") != binance_symbol
        ]
        save_config(self.config)
        self.alert_manager.reset_alerts_for_coin(binance_symbol)
        self.status_label.configure(
            text=f"Removed {disp}/USDT ({disp} हटाया गया)", text_color=TEXT_SECONDARY
        )

        # 2. Push to NeonDB in background thread without blocking Tkinter UI
        self._sync_coins_to_db(blocking=False)

    # ──────────────────────────────────────────────────────────────────
    # Dialogs & Windows
    # ──────────────────────────────────────────────────────────────────

    def _open_alerts_dialog(self, coin_config: dict):
        def _on_save():
            save_config(self.config)
            self._sync_coins_to_db()
            sym = coin_config.get("symbol")
            if sym and sym in self.coin_rows:
                self.coin_rows[sym].update_alert_count()

        AlertDialog(self, coin_config, on_save=_on_save)

    def _open_chart_window(self, coin_config: dict, current_price=None):
        sym = coin_config.get("symbol")
        price = current_price or self._current_prices.get(sym)
        ChartWindow(self, self.binance_client, coin_config, current_price=price)

    # ──────────────────────────────────────────────────────────────────
    # Alert Callbacks
    # ──────────────────────────────────────────────────────────────────

    def _on_visual_alert(self, binance_symbol: str, message: str, direction: str):
        def _flash():
            if binance_symbol in self.coin_rows:
                self.coin_rows[binance_symbol].flash_row_alert(direction)
        self.after(0, _flash)

    def _on_popup_alert(self, display_symbol: str, message: str, direction: str, loop: bool):
        def _show():
            AlertPopupWindow(
                self, display_symbol, message, direction, loop=loop,
                sound_callback=self.alert_manager.play_sound_once,
                sound_stop_callback=self.alert_manager.stop_sound,
            )
        self.after(0, _show)

    # ──────────────────────────────────────────────────────────────────
    # Data Fetch Loop (Background Thread)
    # ──────────────────────────────────────────────────────────────────

    def _start_fetching(self):
        self._stop_event.clear()
        self._fetch_thread = threading.Thread(target=self._fetch_loop, daemon=True)
        self._fetch_thread.start()

    def _fetch_loop(self):
        last_db_sync = 0.0
        while not self._stop_event.is_set():
            now = time.time()
            if self._user_id and DB_AVAILABLE and (now - last_db_sync >= 5.0):
                self._sync_from_db_worker()
                last_db_sync = now

            self._fetch_all_coins()

            # Wait in 1-second chunks so stop_event is responsive
            # and check DB every 5s even if price interval is longer
            interval = max(3, self.config.get("refresh_interval_seconds", 5))
            for _ in range(int(interval)):
                if self._stop_event.is_set():
                    break
                self._stop_event.wait(1.0)
                now_check = time.time()
                if self._user_id and DB_AVAILABLE and (now_check - last_db_sync >= 5.0):
                    self._sync_from_db_worker()
                    last_db_sync = now_check

    @staticmethod
    def _coins_data_equal(c1: list[dict], c2: list[dict]) -> bool:
        if len(c1) != len(c2):
            return False

        def _norm_alerts(alerts):
            norm = []
            for a in alerts:
                price = a.get("price")
                p_val = round(float(price), 8) if price is not None else 0.0
                norm.append((
                    str(a.get("id", "")),
                    p_val,
                    str(a.get("direction", "above")).lower(),
                    bool(a.get("active", True)),
                    bool(a.get("loop", False)),
                    str(a.get("label", "")).strip(),
                ))
            return sorted(norm, key=lambda x: str(x[0]))

        d1 = {c.get("symbol", ""): _norm_alerts(c.get("alerts", [])) for c in c1 if c.get("symbol")}
        d2 = {c.get("symbol", ""): _norm_alerts(c.get("alerts", [])) for c in c2 if c.get("symbol")}
        return d1 == d2

    def _sync_from_db_worker(self):
        """Fetch latest watchlist and alerts from NeonDB in background thread."""
        if not self._user_id or not DB_AVAILABLE:
            return
        if time.time() - self._last_local_edit_time < 3.0:
            return
        if not self._db_sync_lock.acquire(blocking=False):
            return
        try:
            db_coins = db_manager.load_watched_coins(self._user_id)
            current_coins = self.config.get("watched_coins", [])
            if not self._coins_data_equal(current_coins, db_coins):
                self.after(0, lambda: self._apply_db_sync(db_coins))
        except Exception as e:
            print(f"[App] DB sync check error: {e}")
        finally:
            self._db_sync_lock.release()

    def _apply_db_sync(self, db_coins: list[dict]):
        """Apply coins and alerts from NeonDB to GUI smoothly without flicker."""
        current_coins = self.config.get("watched_coins", [])
        if self._coins_data_equal(current_coins, db_coins):
            return

        old_syms = {c.get("symbol") for c in current_coins if c.get("symbol")}
        new_syms = {c.get("symbol") for c in db_coins if c.get("symbol")}

        # Update local config so alert_manager and local cache have latest data
        self.config["watched_coins"] = db_coins
        save_config(self.config)

        # Removed coins: destroy their rows
        for sym in (old_syms - new_syms):
            if sym in self.coin_rows:
                self.coin_rows[sym].destroy()
                del self.coin_rows[sym]
                self.alert_manager.reset_alerts_for_coin(sym)

        # Added coins: create rows and fetch their price immediately
        for coin in db_coins:
            sym = coin.get("symbol")
            if sym in (new_syms - old_syms):
                self._add_coin_row(coin, row_index=len(self.coin_rows))
                t = threading.Thread(target=self._fetch_single_now, args=(sym,), daemon=True)
                t.start()

        # Existing coins: update coin_config in-place and refresh alert count button
        for coin in db_coins:
            sym = coin.get("symbol")
            if sym in self.coin_rows:
                row = self.coin_rows[sym]
                row.coin_config = coin
                row.update_alert_count()

        if not db_coins:
            self.status_label.configure(
                text="No coins tracked. Use 'Add Coin' above. (कॉइन जोड़ें)",
                text_color=TEXT_SECONDARY
            )
        else:
            now_str = time.strftime("%H:%M:%S")
            self.status_label.configure(
                text=f"Auto-synced with mobile at {now_str} (मोबाइल से सिंक हुआ)",
                text_color=ACCENT_GREEN
            )

    def _fetch_all_coins(self):
        watched = self.config.get("watched_coins", [])
        if not watched:
            self.after(0, lambda: self.status_label.configure(
                text="No coins tracked. Use 'Add Coin' above. (कॉइन जोड़ें)",
                text_color=TEXT_SECONDARY
            ))
            return

        symbols = [c["symbol"] for c in watched if "symbol" in c]
        tickers = self.binance_client.get_all_tickers_24hr(symbols)

        for coin in watched:
            sym = coin.get("symbol")
            t_data = tickers.get(sym)
            if t_data and "price" in t_data:
                self._current_prices[sym] = t_data["price"]
                disp = coin.get("display_symbol", sym)
                self.alert_manager.check_and_trigger_alerts(
                    display_symbol=disp,
                    binance_symbol=sym,
                    current_price=t_data["price"],
                    coin_config=coin,
                )

        self.after(0, lambda: self._apply_tickers(tickers))

    def _apply_tickers(self, tickers: dict):
        for sym, row in list(self.coin_rows.items()):
            row.update_data(tickers.get(sym))

        now_str = time.strftime("%H:%M:%S")
        self.status_label.configure(
            text=f"Updated {now_str} (अपडेट हुआ)", text_color=TEXT_SECONDARY
        )

    def _fetch_single_now(self, binance_symbol: str):
        data = self.binance_client._get_single_ticker(binance_symbol)
        if data:
            self._current_prices[binance_symbol] = data.get("price")
            self.after(0, lambda: self._apply_single(binance_symbol, data))

    def _apply_single(self, sym: str, ticker: dict):
        if sym in self.coin_rows:
            self.coin_rows[sym].update_data(ticker)

    # ──────────────────────────────────────────────────────────────────
    # Settings Controls
    # ──────────────────────────────────────────────────────────────────

    def _update_interval(self, event=None):
        try:
            val = int(self._interval_entry.get().strip())
            val = max(5, min(val, 3600))
            self.config["refresh_interval_seconds"] = val
            save_config(self.config)
            self.status_label.configure(
                text=f"Refresh interval: {val}s (ताज़ा दर सेट)", text_color=TEXT_SECONDARY
            )
        except ValueError:
            self._interval_entry.delete(0, tk.END)
            self._interval_entry.insert(0, str(self.config.get("refresh_interval_seconds", 10)))

    def _toggle_sound(self):
        enabled = self._sound_var.get()
        self.config["sound_enabled"] = enabled
        save_config(self.config)
        state_txt = "enabled (चालू)" if enabled else "muted (बंद)"
        self.status_label.configure(text=f"Sound {state_txt}", text_color=TEXT_SECONDARY)

    # ──────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────

    def _logout(self):
        """Logout current user, clear local session, go back to login screen."""
        self._on_close(skip_callback=True)
        if DB_AVAILABLE:
            auth_manager.clear_local_session()
        from login_screen import LoginScreen
        ls = LoginScreen()
        ls.mainloop()

    def _sync_coins_to_db(self, blocking: bool = False):
        """Push current watchlist and alerts to NeonDB without freezing UI."""
        if not self._user_id or not DB_AVAILABLE:
            return
        self._last_local_edit_time = time.time()
        import copy
        coins_snapshot = copy.deepcopy(self.config.get("watched_coins", []))
        user_id = self._user_id

        def _worker():
            with self._db_sync_lock:
                try:
                    db_manager.save_watched_coins(user_id, coins_snapshot)
                except Exception as e:
                    print(f"[App] DB sync error: {e}")

        if blocking:
            _worker()
        else:
            threading.Thread(target=_worker, daemon=True).start()

    def _on_close(self, skip_callback: bool = False):
        self._stop_event.set()
        self.alert_manager.stop_sound()
        save_config(self.config)
        self._sync_coins_to_db(blocking=True)
        self.destroy()
        if not skip_callback and self._on_close_callback:
            try:
                self._on_close_callback()
            except Exception:
                pass