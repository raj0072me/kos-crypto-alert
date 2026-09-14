# How to Run Kanta's Crypto Alerts · कांता के क्रिप्टो अलर्ट्स

This guide provides step-by-step instructions on setting up, configuring, and running **Kanta's Crypto Alerts (कांता के क्रिप्टो अलर्ट्स)** on Windows, macOS, and Linux.

---

## 🌟 Key Features & What's New

* **Rebranded as Kanta's Crypto Alerts (कांता के क्रिप्टो अलर्ट्स)**:
  - Custom crypto bell logo (`kos-crypto-alert-icon.svg`) applied to the titlebar, taskbar, header, and Windows notifications.
* **Bilingual English + Hindi Devanagari UI**:
  - Clear English labels paired with intuitive Hindi Devanagari subtext across every window, button, table header, and alert popup.
* **Live Cryptocurrency Icons**:
  - Automatically fetches and displays crisp official coin logos (BTC, ETH, SOL, DOGE, BNB, etc.) directly in the watchlist table with local disk caching and offline letter-badge fallbacks.
* **Custom Alert Sound Chooser**:
  - Choose any `.mp3`, `.wav`, or `.ogg` audio file from your system via the built-in file picker.
  - Includes **▶ Test** and **↺ Reset** buttons. Defaults to `assets/allert.mp3`.
* **Instant Alert Sound Dismissal**:
  - Clicking **Dismiss Alert (अलर्ट बंद करें)** or closing the alert window immediately cuts off all audio playback in real time.
* **Zero API Key Needed**:
  - Free Binance Public API integration — no account, signup, or API key needed.
* **Interactive Candlestick & Volume Charts**:
  - Dark-mode TradingView-style charts with timeframe selector (15m, 1H, 4H, 1D, 1W), clickable price inspection, and live price guidelines.
* **Multiple Alerts per Coin & Loop Mode**:
  - Set multiple Above / Below target levels per coin with custom labels and loop alarm mode.

---

## 📋 Table of Contents
1. [Prerequisites](#-prerequisites)
2. [Quick Start (Windows)](#-quick-start-windows)
3. [Step-by-Step Installation](#-step-by-step-installation)
4. [Running the Application](#-running-the-application)
5. [How to Use the Application](#-how-to-use-the-application)
6. [Alerts & Notifications Guide](#-alerts--notifications-guide)
7. [Choosing a Custom Alert Sound](#-choosing-a-custom-alert-sound)
8. [Interactive Candlestick Charts](#-interactive-candlestick-charts)
9. [Configuration Reference](#-configuration-reference)
10. [Troubleshooting & FAQs](#-troubleshooting--faqs)

---

## 📌 Prerequisites

Before running the application, make sure you have:
* **Python 3.8 or newer** installed on your system.
  * To check your Python version, open a terminal and run:
    ```bash
    python --version
    ```
* **Internet Connection** (to fetch real-time Binance prices, candlestick data, and coin logos).
* **No API Key is required!**

---

## 🚀 Standalone Portable Executable (.exe) — No Python Needed!

You can run the app directly on **any Windows computer** without installing Python, Git, or any dependencies:

```
dist/Kantas_Crypto_Alerts.exe
```

* **Fully Portable**: Simply copy `Kantas_Crypto_Alerts.exe` to your Desktop, Documents folder, or a USB drive and double-click to run.
* **Persistent Preferences**: Saves your watched coins and alert settings to a `config.json` file in the same folder as the executable.
* **No Console Window**: Runs as a sleek, native desktop application.

---

## ⚡ Quick Start (Running from Python Source)

If you prefer to run from Python source code:

```powershell
# 1. Navigate to the project directory
cd c:\Users\raj00\OneDrive\Desktop\temp_apps\crypto_checker

# 2. Install dependencies
pip install -r requirements-desktop.txt

# 3. Start the application
python main.py
```

---

## 🛠 Step-by-Step Installation

### Step 1: Open Terminal / Command Prompt
Open **PowerShell**, **Command Prompt**, or your terminal and navigate to the project directory:

```bash
cd c:\Users\raj00\OneDrive\Desktop\temp_apps\crypto_checker
```

### Step 2: Create a Virtual Environment (Recommended)
```powershell
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements-desktop.txt
```

This installs:
- **`customtkinter`**: Modern dark-mode user interface.
- **`requests`**: Fast API requests to Binance public endpoints and coin logos.
- **`pygame`**: Instant audio alert playback and stopping.
- **`matplotlib` & `mplfinance`**: Candlestick and volume charts.
- **`pandas`**: Time-series candlestick dataframe handling.
- **`pillow` (PIL)**: High-resolution icon rendering and caching.
- **`plyer`**: Native Windows toast / desktop notifications.

---

## 🚀 Running the Application

```bash
python main.py
```

---

## 🖥 How to Use the Application

| Action | How to do it |
| :--- | :--- |
| **Search & Add Coin (सिक्का जोड़ें)** | Type a coin ticker or name into the **Add Coin** box (e.g. `BTC`, `ETH`, `SOL`, `DOGE`, `PEPE`). Click any suggestion from the autocomplete dropdown or press <kbd>Enter</kbd>. |
| **View Coin Icons (सिक्के का लोगो)** | The official icon for each coin is loaded automatically next to the symbol in the watchlist. |
| **Manage Multiple Alerts (अलर्ट्स)** | Click **⚡ Alerts (N)** on any coin row to open the Price Alert Dialog. Click **+ Add Alert**, choose Direction (**Above (ऊपर)** or **Below (नीचे)**), enter Target Price in USDT, optional label, and toggle **Loop (दोहराएं)**. |
| **Dismiss Alert (अलर्ट बंद करें)** | Click **Dismiss Alert · अलर्ट बंद करें ✕** on the flashing alert window. The sound stops immediately. |
| **View Candlestick Chart (चार्ट)** | Click the **📈** (Chart) button next to any coin to open the interactive chart. |
| **Inspect Price on Chart** | Click anywhere on the candlestick chart to see the exact price level in USDT, percentage difference from live price, and candle OHLCV data. |
| **Change Alert Sound (ध्वनि बदलें)** | In the bottom bar, click **📁 Choose / चुनें** to pick any audio file (`.mp3`, `.wav`, `.ogg`). Click **▶ Test / चलाएं** to test it, or **↺ Reset / रीसेट** to revert to default. |
| **Adjust Refresh Rate (ताज़ा दर)** | In the bottom bar, change **Refresh / ताज़ा (s)** (default is 10s). |
| **Toggle Sound (ध्वनि चालू/बंद)** | Check or uncheck **Sound / ध्वनि** in the bottom bar. |
| **Remove a Coin (सिक्का हटाएं)** | Click the red **✕** button on the right side of the coin's row. |

---

## 🔔 Alerts & Notifications Guide

1. **System Toast Notifications**:
   - Fires Windows toast notifications even when the app is **minimized** or in the background.
   - Shows the custom app logo.

2. **Flashing Alert Popup Window**:
   - Pops up in front of all windows with a green (above) or red (below) flashing border.
   - Displays the coin icon, current price, target price, and custom label in both English and Hindi.

3. **Looping Mode & Instant Stop**:
   - If **Loop (दोहराएं)** is enabled, the alarm repeats until you manually dismiss it.
   - Clicking **Dismiss Alert (अलर्ट बंद करें)** or pressing <kbd>Esc</kbd> stops the sound the exact millisecond you click it!

---

## 🎵 Choosing a Custom Alert Sound

1. In the bottom bar of the app, locate the **Alert Sound / अलर्ट ध्वनि** section.
2. Click **📁 Choose / चुनें**.
3. Select any audio file (`.mp3`, `.wav`, or `.ogg`) from your computer.
4. Click **▶ Test / चलाएं** to preview the audio.
5. If you ever want to return to the built-in sound, click **↺ Reset / रीसेट** (resets to `assets/allert.mp3`).

---

## 📁 File Structure Reference

```
crypto_checker/
├── main.py                 # Application launcher (Kanta's Crypto Alerts)
├── gui.py                  # Bilingual GUI (CustomTkinter + mplfinance)
├── binance_client.py       # Free Binance public API client
├── config_manager.py       # Preferences, multi-alerts, and custom sound loader
├── alert_manager.py        # Multi-alert checker, sound player & desktop toasts
├── icon_manager.py         # Coin logo downloader, disk cache & SVG logo loader
├── requirements.txt        # Python dependency list
├── kos-crypto-alert-icon.svg # Original SVG app logo
├── assets/                 # Application assets
│   ├── app_icon.ico        # Generated multi-size application icon
│   ├── app_icon.png        # Transparent 256x256 app logo
│   ├── allert.mp3          # Default alert audio
│   └── coin_icons/         # Cached coin logos (BTC, ETH, SOL, etc.)
├── config.json             # Saved user preferences & watched coins
└── HOW_TO_RUN.md           # This execution guide
```
