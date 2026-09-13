"""
main.py
-------
Entry point for Kanta's Crypto Alerts · कांता के क्रिप्टो अलर्ट्स.
Powered by Binance public API — no API key needed!
"""

import os
import customtkinter as ctk
from gui import App


def main():
    # Force dark mode
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    import sys
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    # Ensure assets directory and sound file exist
    assets_dir = os.path.join(base_dir, "assets")
    alert_sound = os.path.join(assets_dir, "allert.mp3")

    if not os.path.exists(assets_dir):
        try:
            os.makedirs(assets_dir)
            print(f"[main] Created assets directory: {assets_dir}")
        except OSError as e:
            print(f"[main] Could not create assets directory: {e}")

    if not os.path.exists(alert_sound):
        try:
            with open(alert_sound, "wb") as f:
                pass
            print(f"[main] Created default sound placeholder: {alert_sound}")
        except Exception as e:
            print(f"[main] Could not create sound placeholder: {e}")

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()