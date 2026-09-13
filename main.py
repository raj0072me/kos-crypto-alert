"""
main.py
-------
Entry point for Kanta's Crypto Alerts · कांता के क्रिप्टो अलर्ट्स.
Powered by Binance public API — no API key needed!

Startup flow:
  1. Check session.json for a saved token
  2. If valid → skip login, go straight to App or AdminPanel
  3. If expired / missing → show LoginScreen
"""

import os
import sys
import customtkinter as ctk


def _get_base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _ensure_assets(base_dir: str):
    assets_dir = os.path.join(base_dir, "assets")
    alert_sound = os.path.join(assets_dir, "allert.mp3")
    if not os.path.exists(assets_dir):
        try:
            os.makedirs(assets_dir)
        except OSError as e:
            print(f"[main] Could not create assets directory: {e}")
    if not os.path.exists(alert_sound):
        try:
            with open(alert_sound, "wb") as f:
                pass
        except Exception as e:
            print(f"[main] Could not create sound placeholder: {e}")


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    base_dir = _get_base_dir()
    _ensure_assets(base_dir)

    # ── 1. Initialize DB ──────────────────────────────────────────────
    try:
        import db_manager
        db_manager.init_db()
        db_manager.cleanup_expired_sessions()
        db_available = True
    except Exception as e:
        print(f"[main] DB init error (running offline): {e}")
        db_available = False

    # ── 2. Check saved session ────────────────────────────────────────
    if db_available:
        try:
            import auth_manager
            local = auth_manager.load_local_session()
            if local and local.get("token"):
                user = db_manager.validate_session(local["token"])
                if user:
                    print(f"[main] Auto-login as {user.get('display_name')} (id={user.get('id')})")
                    db_manager.update_user_last_login(user["id"])
                    # Launch directly without login screen
                    if user.get("is_admin"):
                        from admin_panel import AdminPanel
                        panel = AdminPanel(user)
                        panel.mainloop()
                    else:
                        from gui import App
                        app = App(current_user=user)
                        app.mainloop()
                    return  # Done
                else:
                    # Token expired
                    auth_manager.clear_local_session()
        except Exception as e:
            print(f"[main] Session check error: {e}")

    # ── 3. Show login screen ──────────────────────────────────────────
    if db_available:
        from login_screen import LoginScreen
        login = LoginScreen()
        login.mainloop()
    else:
        # DB unavailable — fall back to legacy no-login mode
        print("[main] Running in offline mode (no DB).")
        from gui import App
        app = App()
        app.mainloop()


if __name__ == "__main__":
    main()