"""
auth_manager.py
---------------
Manages local session persistence (remember-me).
Stores token in session.json next to the exe / main.py.
"""

import json
import os
import sys

if getattr(sys, "frozen", False):
    _BASE = os.path.dirname(sys.executable)
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))

SESSION_FILE = os.path.join(_BASE, "session.json")


def save_local_session(token: str, user_id: int, is_admin: bool, display_name: str):
    """Persist login token to disk so next launch auto-logs in."""
    data = {
        "token": token,
        "user_id": user_id,
        "is_admin": is_admin,
        "display_name": display_name,
    }
    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[Auth] Could not save session: {e}")


def load_local_session() -> dict | None:
    """Load session from disk. Returns dict with token, user_id, is_admin, display_name or None."""
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("token"):
            return data
    except Exception:
        pass
    return None


def clear_local_session():
    """Delete saved session (logout)."""
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except Exception as e:
        print(f"[Auth] Could not clear session: {e}")
