# 🔔 Kanta's Crypto Alerts · कान्ता क्रिप्टो अलर्ट्स

> A modern, bilingual (English + Hindi) cryptocurrency price alert desktop app with cloud sync across devices — **no Binance API key required!**
> Powered by the free **Binance Public API** and **NeonDB PostgreSQL**.

---

## ✨ Features

- 🔴 **Real-time Price Tracking** — Live USDT pair prices directly from Binance public API (no account or API key needed).
- 🔍 **Search Autocomplete** — Instant suggestions for all Binance pairs as you type.
- 🪙 **Live Coin Logos** — Official cryptocurrency logos dynamically cached with circular badges.
- 🔔 **Multiple Alerts per Coin** — Configure independent Above / Below thresholds, loop mode, and active toggles.
- 🔁 **Continuous Alarm & Instant Dismiss** — Loop alert sound until dismissed; audio instantly cuts off when closed.
- 🎵 **Custom Alert Audio** — Choose any `.mp3`, `.wav`, or `.ogg` sound file from your computer.
- 📈 **Interactive Candlestick Charts** — Deep OHLC candlestick charts with volume bars, timeframe selectors (15m, 1h, 4h, 1d, 1w), and interactive price inspection.
- ☁️ **Cloud Multi-Device Sync (NeonDB)** — Watchlists, active alerts, and trigger history automatically sync across devices via cloud PostgreSQL.
- 🔐 **Authentication & Remember Me** — Secure phone-number based credentials with automatic 30-day session tokens (never prompts for login on reopen).
- 👑 **Comprehensive Admin Panel**:
  - View all registered users with avatar badges.
  - Create new users with custom display names, phone/password, and profile pictures.
  - ✏️ **Edit Users**: Edit names, passwords/phone numbers, or update/remove avatar photos.
  - 🗑 Delete users and their associated alert data (admin accounts protected).
  - 🔔 View centralized real-time trigger history for all users.
- 🇮🇳 **Bilingual English + Hindi UI** — Clear Devanagari labels and subtext across all views.
- 🖥️ **Portable Standalone EXE** — Runs directly on any Windows PC without installing Python.

---

## 🚀 Quickstart (No Python Needed)

Run the standalone executable directly:
```
dist/Kantas_Crypto_Alerts.exe
```
Or use the zip release:
```
dist/Kantas_Crypto_Alerts_v2.0_Portable.zip
```
No installation, no Python, no dependencies required.

---

## 🔑 Default Login Credentials

- **Admin Login**:
  - Select **🔐 Admin Login**
  - Password / Phone: `9899654695`
  - Access the full Admin Panel to manage users and monitor global alert history.
- **User Login**:
  - Select **👤 User Login**
  - Password / Phone: `9818011930` (Mehboob Khan)
  - Opens personal crypto watchlist & alert manager synced to cloud.

---

## 🐍 Run From Source (Developers)

### 1. Clone the repository
```bash
git clone https://github.com/raj0072me/kos-crypto-alert.git
cd kos-crypto-alert
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the application
```bash
python main.py
```

---

## 🗂️ Project Structure

```
kos-crypto-alert/
├── main.py                          # Startup controller & session validator
├── gui.py                           # Main crypto alerts UI (watchlist, charts, sounds)
├── login_screen.py                  # User and Admin authentication interface
├── admin_panel.py                   # Admin dashboard (user CRUD, edit dialog, global history)
├── db_manager.py                    # NeonDB PostgreSQL backend (users, sessions, watchlists, history)
├── auth_manager.py                  # Local session management (session.json)
├── alert_manager.py                 # Multi-threshold detection & background alert dispatcher
├── binance_client.py                # Public Binance REST API client
├── config_manager.py                # Local configuration & sound resolution
├── icon_manager.py                  # Icon fetching, caching, and letter-badge generation
├── assets/
│   ├── allert.mp3                   # Default alert audio
│   ├── allert.wav                   # Uncompressed WAV fallback
│   ├── app_icon.png                 # App icon (PNG)
│   ├── app_icon.ico                 # Multi-size Windows ICO
│   └── coin_icons/                  # Cached cryptocurrency logos
├── kos-crypto-alert-icon.png        # App branding asset
├── Kantas_Crypto_Alerts.spec        # PyInstaller specification file
├── requirements.txt                 # Python dependencies
├── HOW_TO_RUN.md                    # Setup and usage manual
└── README.md
```

---

## 🛠️ Tech Stack

| Area | Technologies |
|------|--------------|
| **GUI Framework** | `customtkinter`, `tkinter` |
| **Cloud Database** | `psycopg2-binary` (NeonDB Serverless PostgreSQL) |
| **Market Data** | Binance Public REST API |
| **Interactive Charts** | `mplfinance`, `matplotlib`, `pandas` |
| **Audio Engine** | `pygame.mixer` |
| **System Notifications**| `plyer` (Windows Action Center toasts) |
| **Packaging** | `PyInstaller` (One-file standalone portable binary) |

---

## 📦 Building the Portable EXE

To rebuild the single-file portable Windows executable:

```bash
pyinstaller --clean Kantas_Crypto_Alerts.spec
```

The output executable will be created at `dist/Kantas_Crypto_Alerts.exe` (~71 MB).

---

## 📚 Documentation

- [**`HOW_TO_RUN.md`**](HOW_TO_RUN.md) — Comprehensive run, setup, and troubleshooting manual.
- [**`GITHUB_GUIDE.md`**](GITHUB_GUIDE.md) — Step-by-step Git & GitHub guide on pushing, pulling, remotes, and conflict resolution.
- [**`ANDROID_ROADMAP.md`**](ANDROID_ROADMAP.md) — Architectural guide on building the cross-device Android app synced with NeonDB.

---

## 🙋 Author

Made with ❤️ by **Kanta**

---

## 📄 License

MIT — Free to use, modify, and distribute.
