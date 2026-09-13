"""
icon_manager.py
----------------
Manages cryptocurrency icons and application logo:
- Fetches and caches coin icons (PNG) locally in assets/coin_icons/
- Generates fallback letter badges if offline or coin icon is unavailable
- Loads the application custom logo (Kanta's Crypto Alerts)
"""

import os
import sys
import threading
import requests
from PIL import Image, ImageDraw, ImageFont
import customtkinter as ctk

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BUNDLE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
COIN_ICONS_DIR = os.path.join(ASSETS_DIR, "coin_icons")
APP_ICON_PNG = os.path.join(ASSETS_DIR, "app_icon.png")
ROOT_ICON_PNG = os.path.join(BASE_DIR, "kos-crypto-alert-icon.png")
APP_ICON_ICO = os.path.join(ASSETS_DIR, "app_icon.ico")

os.makedirs(COIN_ICONS_DIR, exist_ok=True)

# Cache in memory: symbol -> ctk.CTkImage
_icon_cache: dict[str, ctk.CTkImage] = {}
_callbacks: dict[str, list] = {}
_lock = threading.Lock()


def get_app_logo_image(size: tuple[int, int] = (36, 36)) -> ctk.CTkImage | None:
    """Return the main app custom icon as a CTkImage."""
    candidates = [
        ROOT_ICON_PNG,
        APP_ICON_PNG,
        os.path.join(BUNDLE_DIR, "kos-crypto-alert-icon.png"),
        os.path.join(BUNDLE_DIR, "assets", "app_icon.png"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            try:
                im = Image.open(p).convert("RGBA")
                return ctk.CTkImage(light_image=im, dark_image=im, size=size)
            except Exception:
                continue
    return None


def _generate_fallback_badge(symbol: str, size: int = 48) -> Image.Image:
    """Generate a stylish circular badge with the coin's first letter."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    # Color based on symbol hash
    palette = [
        ("#f7931a", "#ffffff"),  # Orange (BTC style)
        ("#627eea", "#ffffff"),  # Blue (ETH style)
        ("#14f195", "#000000"),  # Green (SOL style)
        ("#f3ba2f", "#000000"),  # Yellow (BNB style)
        ("#2775ca", "#ffffff"),  # Deep Blue
        ("#e84142", "#ffffff"),  # Red (AVAX style)
        ("#a052ff", "#ffffff"),  # Purple (MATIC/Polygon style)
        ("#00b8d9", "#ffffff"),  # Cyan
    ]
    idx = sum(ord(c) for c in symbol) % len(palette)
    bg_col, text_col = palette[idx]

    draw.ellipse([(1, 1), (size - 2, size - 2)], fill=bg_col)

    # First 1-2 characters
    txt = symbol[:2].upper() if len(symbol) <= 2 else symbol[0].upper()
    try:
        font = ImageFont.truetype("segoeui.ttf", int(size * 0.45))
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), txt, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) / 2
    y = (size - th) / 2 - 1
    draw.text((x, y), txt, fill=text_col, font=font)
    return im


def get_coin_icon(display_symbol: str, on_loaded_callback=None, size: tuple[int, int] = (24, 24)) -> ctk.CTkImage:
    """
    Get CTkImage for a coin. If cached, returns it immediately.
    If not cached on disk, returns a fallback badge and queues a background download.
    Calls on_loaded_callback(ctk_image) on completion.
    """
    sym = display_symbol.upper().strip()
    with _lock:
        if sym in _icon_cache:
            return _icon_cache[sym]

    local_path = os.path.join(COIN_ICONS_DIR, f"{sym.lower()}.png")

    if os.path.exists(local_path):
        try:
            im = Image.open(local_path).convert("RGBA")
            ctk_img = ctk.CTkImage(light_image=im, dark_image=im, size=size)
            with _lock:
                _icon_cache[sym] = ctk_img
            return ctk_img
        except Exception:
            pass

    # Generate placeholder badge
    fallback_im = _generate_fallback_badge(sym, size=size[0] * 2)
    fallback_ctk = ctk.CTkImage(light_image=fallback_im, dark_image=fallback_im, size=size)

    # Queue download
    if on_loaded_callback:
        with _lock:
            _callbacks.setdefault(sym, []).append(on_loaded_callback)

    threading.Thread(target=_fetch_icon_worker, args=(sym, size), daemon=True).start()
    return fallback_ctk


def _fetch_icon_worker(sym: str, size: tuple[int, int]):
    """Download coin icon from CoinCap CDN or fallback sources."""
    local_path = os.path.join(COIN_ICONS_DIR, f"{sym.lower()}.png")
    urls = [
        f"https://assets.coincap.io/assets/icons/{sym.lower()}@2x.png",
        f"https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/{sym.lower()}.png",
        f"https://cdn.jsdelivr.net/gh/atomiclabs/cryptocurrency-icons@1a63539be1e374f02232f27bb2142044370e57b2/32/color/{sym.lower()}.png",
    ]

    for url in urls:
        try:
            resp = requests.get(url, timeout=6)
            if resp.status_code == 200 and len(resp.content) > 200:
                with open(local_path, "wb") as f:
                    f.write(resp.content)

                im = Image.open(local_path).convert("RGBA")
                ctk_img = ctk.CTkImage(light_image=im, dark_image=im, size=size)
                with _lock:
                    _icon_cache[sym] = ctk_img
                    cbs = _callbacks.pop(sym, [])
                for cb in cbs:
                    try:
                        cb(ctk_img)
                    except Exception:
                        pass
                return
        except Exception:
            continue

    # If all URLs fail, save the fallback badge to disk so we don't keep retrying
    fallback_im = _generate_fallback_badge(sym)
    try:
        fallback_im.save(local_path, format="PNG")
    except Exception:
        pass
