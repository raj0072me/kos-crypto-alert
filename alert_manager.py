"""
alert_manager.py
----------------
Manages price alert logic with:
- Multiple alerts per coin (list-based, not just one above/one below)
- System tray notifications via plyer (works when app is minimized)
- Audio alerts via pygame
- Looping alert popup windows (created on the main thread via callback)
"""

import pygame
import os
import threading

try:
    from plyer import notification as _plyer_notif
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    print("[AlertManager] plyer not found — system notifications disabled.")

# Default assets
import sys

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BUNDLE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)

DEFAULT_SOUND_FILE = os.path.join(BASE_DIR, "assets", "allert.mp3")
if not os.path.isfile(DEFAULT_SOUND_FILE):
    bundled_sound = os.path.join(BUNDLE_DIR, "assets", "allert.mp3")
    if os.path.isfile(bundled_sound):
        DEFAULT_SOUND_FILE = bundled_sound

APP_ICON_ICO = os.path.join(BASE_DIR, "assets", "app_icon.ico")
if not os.path.isfile(APP_ICON_ICO):
    bundled_ico = os.path.join(BUNDLE_DIR, "assets", "app_icon.ico")
    if os.path.isfile(bundled_ico):
        APP_ICON_ICO = bundled_ico


class AlertManager:
    """
    Checks price conditions against a coin's alerts list and triggers
    audio, visual, system, and popup notifications as appropriate.
    """

    def __init__(
        self,
        gui_callback_visual_alert=None,
        gui_callback_popup_alert=None,
        sound_enabled_check_callback=None,
        get_sound_file_callback=None,
        user_id: int | None = None,
    ):
        """
        Args:
            gui_callback_visual_alert: fn(binance_symbol, message, direction)
            gui_callback_popup_alert: fn(display_symbol, message, direction, loop)
            sound_enabled_check_callback: fn() -> bool
            get_sound_file_callback: fn() -> str
            user_id: logged-in user's DB id for alert history logging (optional)
        """
        self._triggered: dict = {}
        self._initialized_symbols: set = set()
        self.gui_callback_visual_alert = gui_callback_visual_alert
        self.gui_callback_popup_alert = gui_callback_popup_alert
        self.sound_enabled_check_callback = sound_enabled_check_callback
        self.get_sound_file_callback = get_sound_file_callback
        self._user_id = user_id
        self._mixer_ok = False

        try:
            pygame.mixer.init()
            self._mixer_ok = True
            print("[AlertManager] Pygame mixer initialized.")
        except pygame.error as e:
            print(f"[AlertManager] Pygame mixer init failed: {e}")

    # ------------------------------------------------------------------
    # Sound
    # ------------------------------------------------------------------

    def play_sound_once(self):
        """Play the configured alert sound once in a daemon thread."""
        if not self._mixer_ok:
            return
        if self.sound_enabled_check_callback and not self.sound_enabled_check_callback():
            return

        sound_file = None
        if self.get_sound_file_callback:
            try:
                sound_file = self.get_sound_file_callback()
            except Exception:
                sound_file = None

        if not sound_file or not os.path.isfile(sound_file):
            sound_file = DEFAULT_SOUND_FILE

        if not os.path.isfile(sound_file):
            print(f"[AlertManager] Sound file not found: {sound_file}")
            return

        t = threading.Thread(target=self._do_play, args=(sound_file,), daemon=True)
        t.start()

    def _do_play(self, sound_file: str):
        try:
            sound = pygame.mixer.Sound(sound_file)
            sound.play()
        except Exception as e:
            print(f"[AlertManager] Sound playback error ({sound_file}): {e}")

    def stop_sound(self):
        """Immediately stop all currently playing audio across all mixer channels."""
        if self._mixer_ok:
            try:
                pygame.mixer.stop()
            except Exception as e:
                print(f"[AlertManager] Stop sound error: {e}")

    # ------------------------------------------------------------------
    # System notification
    # ------------------------------------------------------------------

    def _send_system_notification(self, title: str, message: str):
        """Send a Windows toast / desktop notification (works when minimized)."""
        if not PLYER_AVAILABLE:
            return

        def _notify():
            try:
                kwargs = {
                    "title": title,
                    "message": message,
                    "app_name": "Kanta's Crypto Alerts",
                    "timeout": 8,
                }
                if os.path.exists(APP_ICON_ICO):
                    kwargs["app_icon"] = APP_ICON_ICO
                _plyer_notif.notify(**kwargs)
            except Exception as e:
                print(f"[AlertManager] Notification error: {e}")

        t = threading.Thread(target=_notify, daemon=True)
        t.start()

    # ------------------------------------------------------------------
    # Core: Check and trigger alerts
    # ------------------------------------------------------------------

    def check_and_trigger_alerts(
        self,
        display_symbol: str,
        binance_symbol: str,
        current_price: float,
        coin_config: dict,
    ):
        """
        Evaluate every alert in coin_config['alerts'] against current_price.
        Triggers only once per threshold crossing; resets when price moves back.

        Args:
            display_symbol:  e.g. "BTC"
            binance_symbol:  e.g. "BTCUSDT"
            current_price:   current market price (USDT)
            coin_config:     coin dict from config, must contain 'alerts' list
        """
        if current_price is None:
            return

        is_first_check = binance_symbol not in self._initialized_symbols
        if is_first_check:
            self._initialized_symbols.add(binance_symbol)

        alerts = coin_config.get("alerts", [])
        for alert in alerts:
            if not alert.get("active", True):
                continue

            alert_id = alert.get("id", f"{binance_symbol}_{alert.get('price')}_{alert.get('direction')}")
            price = alert.get("price")
            direction = alert.get("direction", "above")
            loop = alert.get("loop", False)
            label = alert.get("label", "")

            if price is None:
                continue

            # Check condition
            condition_met = (
                (direction == "above" and current_price > price) or
                (direction == "below" and current_price < price)
            )

            # Option 1: Startup baseline calibration
            # If this is the first price check since app launch and the condition is ALREADY met,
            # silently mark it as triggered so opening the app never blasts existing alerts.
            # It will trigger once the price moves back and crosses again while the app is open.
            if is_first_check:
                if condition_met:
                    self._triggered[alert_id] = True
                    print(
                        f"[AlertManager] Startup baseline: {display_symbol} is already {direction} "
                        f"{price} USDT (current: {current_price} USDT). Silently calibrated — will alert on next active crossing."
                    )
                continue

            if condition_met and not self._triggered.get(alert_id):
                # Mark as triggered
                self._triggered[alert_id] = True

                # Build message
                arrow = "📈" if direction == "above" else "📉"
                verb = "exceeded" if direction == "above" else "dropped below"
                price_str = self._fmt(current_price)
                target_str = self._fmt(price)
                message = (
                    f"{arrow} {display_symbol} {verb} {target_str} USDT\n"
                    f"Current price: {price_str} USDT"
                )
                if label:
                    message = f"[{label}] {message}"

                try:
                    print(f"[ALERT] {message.replace(chr(10), ' ')}")
                except UnicodeEncodeError:
                    print(f"[ALERT] {display_symbol} {verb} {target_str} USDT (Current: {price_str} USDT)")

                # 1. Play sound
                self.play_sound_once()

                # 2. System notification (works when minimized/in background)
                self._send_system_notification(
                    f"Crypto Alert: {display_symbol}",
                    message.replace("\n", " ")
                )

                # 3. Flash the coin row in the GUI
                if self.gui_callback_visual_alert:
                    self.gui_callback_visual_alert(binance_symbol, message, direction)

                # 4. Show flashing popup window (main thread)
                if self.gui_callback_popup_alert:
                    self.gui_callback_popup_alert(display_symbol, message, direction, loop)

                # 5. Log to NeonDB alert history
                if self._user_id:
                    import threading as _t
                    _t.Thread(
                        target=self._log_to_db,
                        args=(binance_symbol, direction, current_price, price),
                        daemon=True
                    ).start()

            elif not condition_met:
                # Reset so it can fire again when price re-crosses the threshold
                self._triggered.pop(alert_id, None)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt(price: float) -> str:
        if price >= 1:
            return f"{price:,.2f}"
        elif price >= 0.01:
            return f"{price:.4f}"
        else:
            return f"{price:.8f}"

    def _log_to_db(self, symbol: str, alert_type: str, trigger_price: float, threshold: float):
        """Background thread: log fired alert to NeonDB."""
        try:
            import db_manager
            db_manager.log_alert_history(self._user_id, symbol, alert_type, trigger_price, threshold)
        except Exception as e:
            print(f"[AlertManager] DB log error: {e}")

    def reset_alerts_for_coin(self, binance_symbol: str):
        """Clear all triggered states and recalibrate baseline for a coin."""
        keys = [k for k in self._triggered if binance_symbol in k]
        for k in keys:
            del self._triggered[k]
        self._initialized_symbols.discard(binance_symbol)

    def reset_specific_alert(self, alert_id: str):
        """Clear triggered state for a specific alert."""
        self._triggered.pop(alert_id, None)