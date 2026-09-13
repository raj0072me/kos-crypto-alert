# 🔔 Kanta's Crypto Alerts · कांता के क्रिप्टो अलर्ट्स

> A beautiful, bilingual (English + Hindi) desktop cryptocurrency price alert app — **no API key required!**
> Powered by the free **Binance public API**.

---

## ✨ Features

- 🔴 **Real-time Price Tracking** — Live USDT pair prices from Binance public API (zero sign-up needed)
- 🔍 **Search Autocomplete** — Type a coin symbol and get live suggestions from all Binance pairs
- 🪙 **Coin Icons** — Cryptocurrency logos fetched and cached locally alongside letter-badge fallbacks
- 🔔 **Multiple Alerts Per Coin** — Set multiple Above/Below thresholds per coin, each independently active/inactive
- 🔁 **Loop Alarm** — Optional looping audio alarm until dismissed
- 🛑 **Instant Dismiss** — Alert sound stops immediately when you click Dismiss
- 🎵 **Custom Alert Sound** — Pick any `.mp3`, `.wav`, or `.ogg` file from your system; defaults to `assets/allert.mp3`
- 📈 **Interactive Candlestick Charts** — Click any coin to see historical OHLC candle data via mplfinance
- 🌙 **Dark Mode UI** — Sleek dark theme with glassmorphism-style panels
- 🇮🇳 **Hindi Devanagari UI** — All labels in Hindi with English subtext
- 🔕 **Silent Startup** — Does NOT trigger alerts on launch for conditions already met; only fires when price actively crosses your threshold while the app is running
- 💾 **Persistent Settings** — `config.json` is saved next to the `.exe` / script and survives restarts
- 🖥️ **Portable Standalone EXE** — A single `.exe` that runs on any Windows PC — no Python needed

---

## 🚀 Quickstart (No Python needed)

Just double-click:
```
dist/Kantas_Crypto_Alerts.exe
```
That's it. No installation, no API key, no setup.

---

## 🐍 Run From Source (Developers)

### 1. Clone the repo
```bash
git clone https://github.com/raj0072me/kos-crypto-alert.git
cd kos-crypto-alert
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run
```bash
python main.py
```

---

## 🗂️ Project Structure

```
kos-crypto-alert/
├── main.py                    # Entry point
├── gui.py                     # Full UI (CustomTkinter, dark theme, Hindi labels)
├── alert_manager.py           # Alert logic, sound playback, silent startup baseline
├── binance_client.py          # Binance public API — no key needed
├── config_manager.py          # Loads/saves config.json (frozen + source mode)
├── icon_manager.py            # Fetches & caches coin icons, badge fallback
├── assets/
│   ├── allert.mp3             # Default alert sound (re-encoded LAME 192k, VLC safe)
│   ├── allert.wav             # Uncompressed WAV backup
│   ├── app_icon.png           # App logo (PNG)
│   ├── app_icon.ico           # App logo (multi-res ICO for taskbar / EXE)
│   └── coin_icons/            # Cached coin logos (auto-downloaded)
├── kos-crypto-alert-icon.png  # Original high-res brand icon
├── Kantas_Crypto_Alerts.spec  # PyInstaller build spec
├── requirements.txt
├── HOW_TO_RUN.md              # Detailed dev/build guide
└── README.md
```

---

## 🛠️ Technologies

| Area | Library |
|------|---------|
| GUI | `customtkinter` |
| Charts | `mplfinance`, `matplotlib` |
| Audio | `pygame.mixer` |
| Prices | Binance Public REST API |
| Notifications | `plyer` (Windows toast) |
| Packaging | `PyInstaller` |
| Config | JSON |

---

## 📦 Building the Portable EXE

```bash
pyinstaller Kantas_Crypto_Alerts.spec --noconfirm
```

Output: `dist/Kantas_Crypto_Alerts.exe` (~65 MB, fully self-contained)

---

## 🧩 How Alerts Work

1. Add a coin from the search bar (e.g. `BTC`, `ETH`, `SOL`)
2. Click **+ अलर्ट जोड़ें** (Add Alert) on any coin row
3. Set a price threshold (Above or Below), optionally enable Loop
4. Toggle Active on/off per alert at any time
5. When price crosses the threshold → flashing popup + audio alarm
6. Click **Dismiss** to instantly stop the alarm

> **Silent Startup**: Conditions already true when you open the app are silently skipped. Alerts only fire when prices *cross* your threshold while the app is running.

---

## 🔊 Custom Alert Sound

- Click the sound picker in the settings area
- Choose any `.mp3`, `.wav`, or `.ogg` file
- Default: `assets/allert.mp3` (24-second alert, VLC & WMP compatible)

---

## 🙋 Author

Made with ❤️ for **Kanta** · कांता के लिए

---

## 📄 License

MIT — free to use, fork, and modify.
