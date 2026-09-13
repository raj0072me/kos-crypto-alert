"""
db_manager.py
-------------
NeonDB PostgreSQL backend for Kanta's Crypto Alerts.
Handles: users, sessions, watched coins, alerts, alert history.
"""

import psycopg2
import psycopg2.extras
import os
import sys
import secrets
import hashlib
from datetime import datetime, timedelta

# ──────────────────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────────────────

DB_URL = (
    "postgresql://neondb_owner:npg_khqMJtF2bO8e@ep-summer-paper-b3369gg8-pooler"
    ".c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

ADMIN_PHONE = "9899654695"
SESSION_EXPIRY_DAYS = 30


def _connect():
    """Return a new psycopg2 connection."""
    return psycopg2.connect(DB_URL)


# ──────────────────────────────────────────────────────────────────────────────
# Schema initialisation (run once on startup)
# ──────────────────────────────────────────────────────────────────────────────

def init_db():
    """Create all tables and seed the admin user if missing."""
    conn = _connect()
    cur = conn.cursor()

    # users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          SERIAL PRIMARY KEY,
            phone       VARCHAR(20) UNIQUE NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            is_admin    BOOLEAN DEFAULT FALSE,
            profile_pic BYTEA,
            created_at  TIMESTAMP DEFAULT NOW(),
            last_login  TIMESTAMP
        )
    """)

    # sessions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
            token       VARCHAR(64) UNIQUE NOT NULL,
            device_name VARCHAR(100),
            created_at  TIMESTAMP DEFAULT NOW(),
            expires_at  TIMESTAMP NOT NULL
        )
    """)

    # watched coins per user
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_watched_coins (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
            symbol     VARCHAR(30) NOT NULL,
            display_symbol VARCHAR(20) NOT NULL,
            added_at   TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, symbol)
        )
    """)

    # alerts per coin per user
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_alerts (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
            symbol      VARCHAR(30) NOT NULL,
            alert_uuid  VARCHAR(40) UNIQUE NOT NULL,
            alert_type  VARCHAR(10) NOT NULL,
            price       NUMERIC(24,8),
            label       VARCHAR(200),
            is_active   BOOLEAN DEFAULT TRUE,
            loop_alarm  BOOLEAN DEFAULT FALSE,
            created_at  TIMESTAMP DEFAULT NOW()
        )
    """)

    # alert history (what fired and when)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alert_history (
            id            SERIAL PRIMARY KEY,
            user_id       INTEGER REFERENCES users(id) ON DELETE CASCADE,
            symbol        VARCHAR(30),
            alert_type    VARCHAR(10),
            trigger_price NUMERIC(24,8),
            threshold     NUMERIC(24,8),
            triggered_at  TIMESTAMP DEFAULT NOW()
        )
    """)

    # per-user app settings
    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            key     VARCHAR(80) NOT NULL,
            value   TEXT,
            PRIMARY KEY (user_id, key)
        )
    """)

    conn.commit()

    # Seed admin user if not present
    cur.execute("SELECT id FROM users WHERE phone = %s", (ADMIN_PHONE,))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (phone, display_name, is_admin) VALUES (%s, %s, TRUE)",
            (ADMIN_PHONE, "Admin")
        )
        conn.commit()
        print("[DB] Admin user seeded.")

    cur.close()
    conn.close()
    print("[DB] Schema ready.")


# ──────────────────────────────────────────────────────────────────────────────
# User management
# ──────────────────────────────────────────────────────────────────────────────

def get_user_by_phone(phone: str) -> dict | None:
    """Return user dict or None if not found."""
    conn = _connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE phone = %s", (phone.strip(),))
    row = cur.fetchone()
    cur.close(); conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    conn = _connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return dict(row) if row else None


def get_all_users() -> list[dict]:
    """Return all users (admin use)."""
    conn = _connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, phone, display_name, is_admin, created_at, last_login, (profile_pic IS NOT NULL) AS has_pic FROM users ORDER BY created_at")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def create_user(phone: str, display_name: str, is_admin: bool = False,
                profile_pic_bytes: bytes | None = None) -> int:
    """Create a new user, return new id."""
    conn = _connect()
    cur = conn.cursor()
    pic_val = psycopg2.Binary(profile_pic_bytes) if profile_pic_bytes is not None else None
    cur.execute(
        "INSERT INTO users (phone, display_name, is_admin, profile_pic) VALUES (%s, %s, %s, %s) RETURNING id",
        (phone.strip(), display_name.strip(), is_admin, pic_val)
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close(); conn.close()
    return new_id


def update_user_profile_pic(user_id: int, pic_bytes: bytes):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET profile_pic = %s WHERE id = %s", (psycopg2.Binary(pic_bytes), user_id))
    conn.commit()
    cur.close(); conn.close()


def update_user_last_login(user_id: int):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))
    conn.commit()
    cur.close(); conn.close()


def delete_user(user_id: int):
    """Delete user and all their data (CASCADE)."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = %s AND is_admin = FALSE", (user_id,))
    conn.commit()
    cur.close(); conn.close()


def update_user(user_id: int, display_name: str | None = None,
                phone: str | None = None,
                profile_pic_bytes: bytes | None = None,
                clear_pic: bool = False) -> bool:
    """
    Update user fields. Only updates fields that are provided (not None).
    clear_pic=True sets profile_pic to NULL.
    Returns True on success.
    """
    conn = _connect()
    cur = conn.cursor()
    try:
        if display_name is not None:
            cur.execute("UPDATE users SET display_name = %s WHERE id = %s",
                        (display_name.strip(), user_id))
        if phone is not None:
            # Check uniqueness first
            cur.execute("SELECT id FROM users WHERE phone = %s AND id != %s",
                        (phone.strip(), user_id))
            if cur.fetchone():
                cur.close(); conn.close()
                return False  # Phone already taken
            cur.execute("UPDATE users SET phone = %s WHERE id = %s",
                        (phone.strip(), user_id))
        if clear_pic:
            cur.execute("UPDATE users SET profile_pic = NULL WHERE id = %s", (user_id,))
        elif profile_pic_bytes is not None:
            cur.execute("UPDATE users SET profile_pic = %s WHERE id = %s",
                        (psycopg2.Binary(profile_pic_bytes), user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] update_user error: {e}")
        conn.rollback()
        return False
    finally:
        cur.close(); conn.close()



# ──────────────────────────────────────────────────────────────────────────────
# Sessions
# ──────────────────────────────────────────────────────────────────────────────

def create_session(user_id: int) -> str:
    """Create a 30-day session token and return it."""
    token = secrets.token_hex(32)
    expires = datetime.utcnow() + timedelta(days=SESSION_EXPIRY_DAYS)
    device = os.environ.get("COMPUTERNAME", "Unknown PC")
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sessions (user_id, token, device_name, expires_at) VALUES (%s, %s, %s, %s)",
        (user_id, token, device, expires)
    )
    conn.commit()
    cur.close(); conn.close()
    return token


def validate_session(token: str) -> dict | None:
    """Return user dict if token is valid and not expired, else None."""
    if not token:
        return None
    conn = _connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT u.* FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = %s AND s.expires_at > NOW()
    """, (token,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return dict(row) if row else None


def delete_session(token: str):
    """Invalidate a session (logout)."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE token = %s", (token,))
    conn.commit()
    cur.close(); conn.close()


def cleanup_expired_sessions():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE expires_at <= NOW()")
    conn.commit()
    cur.close(); conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Watched coins
# ──────────────────────────────────────────────────────────────────────────────

def save_watched_coins(user_id: int, coins: list[dict]):
    """
    Replace all watched coins for user_id.
    coins: list of {symbol, display_symbol, alerts:[...]}
    """
    conn = _connect()
    cur = conn.cursor()

    # Clear existing coins and alerts for this user
    cur.execute("DELETE FROM user_alerts WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM user_watched_coins WHERE user_id = %s", (user_id,))

    for coin in coins:
        sym = coin.get("symbol", "")
        disp = coin.get("display_symbol", sym.replace("USDT", ""))
        if not sym:
            continue
        cur.execute(
            "INSERT INTO user_watched_coins (user_id, symbol, display_symbol) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (user_id, sym, disp)
        )
        # Save alerts for this coin
        for alert in coin.get("alerts", []):
            cur.execute("""
                INSERT INTO user_alerts
                    (user_id, symbol, alert_uuid, alert_type, price, label, is_active, loop_alarm)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (alert_uuid) DO UPDATE SET
                    alert_type = EXCLUDED.alert_type,
                    price = EXCLUDED.price,
                    label = EXCLUDED.label,
                    is_active = EXCLUDED.is_active,
                    loop_alarm = EXCLUDED.loop_alarm
            """, (
                user_id, sym,
                alert.get("id", ""),
                alert.get("direction", "above"),
                alert.get("price"),
                alert.get("label", ""),
                alert.get("active", True),
                alert.get("loop", False),
            ))

    conn.commit()
    cur.close(); conn.close()


def load_watched_coins(user_id: int) -> list[dict]:
    """Load watched coins with their alerts as the config format expected by gui.py."""
    conn = _connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        "SELECT symbol, display_symbol FROM user_watched_coins WHERE user_id = %s ORDER BY added_at",
        (user_id,)
    )
    coins = [dict(r) for r in cur.fetchall()]

    result = []
    for coin in coins:
        sym = coin["symbol"]
        disp = coin["display_symbol"]
        cur.execute(
            "SELECT * FROM user_alerts WHERE user_id = %s AND symbol = %s ORDER BY id",
            (user_id, sym)
        )
        alert_rows = cur.fetchall()
        alerts = [
            {
                "id": r["alert_uuid"],
                "price": float(r["price"]) if r["price"] is not None else None,
                "direction": r["alert_type"],
                "loop": r["loop_alarm"],
                "label": r["label"] or "",
                "active": r["is_active"],
            }
            for r in alert_rows
        ]
        result.append({
            "symbol": sym,
            "display_symbol": disp,
            "alerts": alerts,
        })

    cur.close(); conn.close()
    return result


# ──────────────────────────────────────────────────────────────────────────────
# App settings (refresh interval, sound enabled, custom sound path)
# ──────────────────────────────────────────────────────────────────────────────

def save_setting(user_id: int, key: str, value: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO app_settings (user_id, key, value) VALUES (%s, %s, %s)
        ON CONFLICT (user_id, key) DO UPDATE SET value = EXCLUDED.value
    """, (user_id, key, value))
    conn.commit()
    cur.close(); conn.close()


def load_settings(user_id: int) -> dict:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM app_settings WHERE user_id = %s", (user_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return {k: v for k, v in rows}


# ──────────────────────────────────────────────────────────────────────────────
# Alert history
# ──────────────────────────────────────────────────────────────────────────────

def log_alert_history(user_id: int, symbol: str, alert_type: str,
                      trigger_price: float, threshold: float):
    """Write a fired alert to history."""
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO alert_history (user_id, symbol, alert_type, trigger_price, threshold)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, symbol, alert_type, trigger_price, threshold))
        conn.commit()
        cur.close(); conn.close()
    except Exception as e:
        print(f"[DB] log_alert_history error: {e}")


def get_alert_history(user_id: int | None = None) -> list[dict]:
    """
    Fetch alert history.
    If user_id is None → return ALL history (admin use).
    If user_id given → return only that user's history.
    """
    conn = _connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if user_id is None:
        cur.execute("""
            SELECT h.*, u.display_name FROM alert_history h
            JOIN users u ON u.id = h.user_id
            ORDER BY h.triggered_at DESC LIMIT 500
        """)
    else:
        cur.execute("""
            SELECT h.*, u.display_name FROM alert_history h
            JOIN users u ON u.id = h.user_id
            WHERE h.user_id = %s
            ORDER BY h.triggered_at DESC LIMIT 200
        """, (user_id,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# Test
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[DB] Connecting and initialising schema...")
    init_db()
    admin = get_user_by_phone(ADMIN_PHONE)
    print(f"[DB] Admin user: {admin}")
    print("[DB] All good!")
