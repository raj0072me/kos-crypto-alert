"""
config_manager.py
-----------------
Manages loading/saving app configuration.
New format uses Binance symbols and per-coin alerts list.
Automatically migrates old CoinMarketCap-based config on first load.
"""

import json
import os
import sys
import uuid

CONFIG_FILE_NAME = "config.json"
if getattr(sys, "frozen", False):
    CONFIG_DIR = os.path.dirname(sys.executable)
else:
    CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

BUNDLE_DIR = getattr(sys, "_MEIPASS", CONFIG_DIR)
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)

# Default configuration — no API key needed!
DEFAULT_CONFIG = {
    "watched_coins": [],
    "refresh_interval_seconds": 10,
    "sound_enabled": True,
    "alert_sound_path": "",  # Custom sound path; empty string = assets/allert.mp3
}

DEFAULT_SOUND_FILE = os.path.join(CONFIG_DIR, "assets", "allert.mp3")


def get_alert_sound_file(config: dict) -> str:
    """Return configured custom sound path if valid, else default assets/allert.mp3."""
    custom = config.get("alert_sound_path", "")
    if custom and os.path.isfile(custom):
        return custom
    if os.path.isfile(DEFAULT_SOUND_FILE):
        return DEFAULT_SOUND_FILE
    bundled = os.path.join(BUNDLE_DIR, "assets", "allert.mp3")
    if os.path.isfile(bundled):
        return bundled
    return DEFAULT_SOUND_FILE


def load_config() -> dict:
    """Load config from file, migrating old formats automatically."""
    if not os.path.exists(CONFIG_FILE_PATH):
        print(f"[Config] File not found — creating with defaults.")
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Migrate from old CMC-based format if needed
        config = _migrate_config(config)

        # Ensure all top-level keys exist
        updated = False
        for key, default_val in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = default_val
                updated = True

        if updated:
            print("[Config] Added missing keys from defaults.")
            save_config(config)

        return config

    except json.JSONDecodeError:
        print("[Config] JSON decode error — using defaults.")
        return DEFAULT_CONFIG.copy()
    except Exception as e:
        print(f"[Config] Unexpected load error: {e} — using defaults.")
        return DEFAULT_CONFIG.copy()


def save_config(config_data: dict) -> None:
    """Save config dict to file."""
    try:
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        print(f"[Config] Error saving: {e}")


def _migrate_config(config: dict) -> dict:
    """
    Migrate old CoinMarketCap-based config format to the new Binance format.
    Converts single alert_above/alert_below fields to the alerts list.
    """
    # Remove legacy CMC api_key
    config.pop("api_key", None)

    if "watched_coins" not in config:
        config["watched_coins"] = []
        return config

    new_coins = []
    for coin in config.get("watched_coins", []):
        if not isinstance(coin, dict):
            continue

        symbol = coin.get("symbol", "")

        # Already new format: has Binance-style USDT symbol
        if symbol.endswith("USDT") and "alerts" in coin:
            new_coins.append(coin)
            continue

        # Old CMC format: symbol like "BTC", has numeric "id", no "alerts"
        if symbol and not symbol.endswith("USDT"):
            new_symbol = f"{symbol}USDT"
            alerts = []

            # Convert old single alert_above
            alert_above = coin.get("alert_above")
            was_active = coin.get("alert_active", False)
            if alert_above is not None:
                alerts.append({
                    "id": str(uuid.uuid4()),
                    "price": float(alert_above),
                    "direction": "above",
                    "loop": False,
                    "label": f"{symbol} above target",
                    "active": was_active,
                })

            # Convert old single alert_below
            alert_below = coin.get("alert_below")
            if alert_below is not None:
                alerts.append({
                    "id": str(uuid.uuid4()),
                    "price": float(alert_below),
                    "direction": "below",
                    "loop": False,
                    "label": f"{symbol} below target",
                    "active": was_active,
                })

            new_coin = {
                "symbol": new_symbol,
                "display_symbol": symbol,
                "alerts": alerts,
            }
            new_coins.append(new_coin)
            print(f"[Config] Migrated '{symbol}' (CMC) → '{new_symbol}' (Binance)")
            continue

        # Partially new format: has USDT symbol but missing alerts key
        if symbol.endswith("USDT"):
            coin.setdefault("alerts", [])
            coin.setdefault("display_symbol", symbol[:-4])
            new_coins.append(coin)

    config["watched_coins"] = new_coins
    return config