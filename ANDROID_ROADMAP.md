# 📱 Android Cross-Device Architecture & Implementation Guide
### *Syncing Crypto Alerts between PC (Windows) and Android Phone via NeonDB*

---

## 🎯 Executive Summary: Can This App Be Turned into an Android App?

**Yes, 100% — and your existing setup makes it significantly easier!**

Because you already migrated this application to **NeonDB (Cloud PostgreSQL)**:
- All users, watchlists, target thresholds, and alert history are **already stored in the cloud**.
- A coin added or an alert set on your **PC** is instantly written to NeonDB.
- An **Android app** reading the same NeonDB database will immediately see those exact alerts and watchlists, and vice versa!

```
+-----------------------------------------------------------------------------------------+
|                                    NEONDB CLOUD (PostgreSQL)                            |
|                                                                                         |
|   • users (Admin, Mehboob Khan, ...)      • user_watched_coins (BTC, SOL, DOGE)         |
|   • user_alerts (Above/Below thresholds)  • alert_history (Audit log of all triggers)   |
+-----------------------------------------------------------------------------------------+
                         ▲                                         ▲
                         │                                         │
                 Read / Write                              Read / Write
                         │                                         │
                         ▼                                         ▼
            +-------------------------+               +--------------------------+
            |      PC APPLICATION     |               |    ANDROID APPLICATION   |
            | (Kantas_Crypto_Alerts)  |               | (Phone / Tablet / APK)   |
            |                         |               |                          |
            | • Desktop GUI           |               | • Mobile Touch UI        |
            | • Windows Toasts        |               | • Full-Screen Audio Alarm|
            | • Pygame Audio          |               | • Lock-Screen Banner     |
            +-------------------------+               +--------------------------+
```

---

## ⚠️ The Mobile Challenge: How Alarms Work on Android

On desktop (Windows), an application can run silently in the system tray.  
However, modern Android (Android 12, 13, 14, 15) has aggressive **battery optimization (Doze mode)**:
> If an app is closed or the screen is locked for a few minutes, Android puts CPU threads to sleep.

To ensure your crypto alarm **rings reliably 24/7 on Android even when the phone is locked or screen is off**, there are two proven architectures:

---

### Architecture Option 1: Foreground Service (Self-Contained in APK) ⭐ *Simplest to Build*

The Android app runs an **Android Foreground Service** with a persistent status notification (e.g., *"Monitoring crypto prices: BTC $68,420"*).

* **How it works:**
  1. The app runs a background timer thread every 10–15 seconds.
  2. It fetches prices directly from Binance Public API.
  3. It reads your active alerts from NeonDB.
  4. If a target triggers, it uses Android's `MediaPlayer` and `RingtoneManager` to play a loud alarm sound and displays a full-screen alert banner over the lock screen.
* **Pros:** 100% client-side, zero extra servers, no recurring costs.
* **Cons:** Uses slightly more phone battery (~3–5% per day).

---

### Architecture Option 2: Cloud Push Notifications (FCM / Firebase) 🏆 *Enterprise Standard*

A lightweight cloud bot checks prices and sends a push notification to your phone.

* **How it works:**
  1. A free worker (running on Render, Railway, or AWS Lambda) checks Binance prices every 10 seconds.
  2. When an alert crosses, it sends a high-priority **Firebase Cloud Messaging (FCM)** message to your phone.
  3. Your phone wakes up instantly, vibrates, and rings the alarm sound even if the app was completely swiped away.
* **Pros:** Zero battery drain on your phone; 100% reliable even on strict phone brands (Xiaomi, Samsung, OnePlus).
* **Cons:** Requires setting up a free Firebase project and a background runner script.

---

## 🛠️ Technology Options for the Android App

| Framework | Difficulty | UI Quality | Performance | Recommended For |
|-----------|------------|------------|-------------|-----------------|
| **Flutter (Dart)** | 🟢 Moderate | 🌟 Top Tier (Native feel) | ⚡ Very Fast | **#1 Choice**: Best cross-platform UI, easy NeonDB / REST integration, excellent background audio plugins. |
| **React Native (JS/TS)** | 🟢 Moderate | ⭐ Great | ⚡ Fast | Great if you already know JavaScript/Web development. |
| **Kotlin (Native Android)**| 🟡 Advanced | 🌟 Official Native | ⚡ Maximum | Deepest integration with Android AlarmManager and Doze mode bypass. |
| **Kivy / BeeWare (Python)**| 🔴 Hard to debug | ⚪ Basic | 🐢 Moderate | Keeps Python, but building reliable background services and audio alarms on Android is painful. |

> **Recommendation:** **Flutter** is currently the gold standard for building modern, high-performance crypto alert apps with beautiful dark-mode charts and loud lockscreen alarms.

---

## 🗄️ How the Shared NeonDB Database Works

Because your database is already deployed on NeonDB, both PC and Android will read and write to the **exact same tables**:

```sql
-- 1. Users table (Shared authentication)
SELECT id, phone, display_name, profile_pic FROM users WHERE phone = :phone;

-- 2. Watchlist (Syncs coins between PC and phone)
SELECT symbol, display_name FROM user_watched_coins WHERE user_id = :user_id;

-- 3. Alerts (Target levels set on PC appear on phone, and vice-versa)
SELECT id, symbol, alert_type, threshold, is_loop, is_active 
FROM user_alerts 
WHERE user_id = :user_id AND is_active = TRUE;

-- 4. Alert History (Logged whenever either device fires an alarm)
INSERT INTO alert_history (user_id, symbol, alert_type, threshold, trigger_price)
VALUES (:user_id, :symbol, :type, :threshold, :price);
```

### The User Flow:
1. **At your Desk (PC):** You log in as **Mehboob Khan** (`9818011930`), add `SOLUSDT`, and set an alert: *"Alert when SOL > 200 USDT"*.
2. **On the Move (Android Phone):** You open your mobile app and log in with `9818011930`.
3. **Instant Sync:** The app fetches from NeonDB. `SOLUSDT` with target `200` is already visible on the phone!
4. **Alarm Fired:** When SOL reaches $200.05, both your PC and your phone play the alert sound!

---

## 🗺️ Step-by-Step Implementation Blueprint

If you decide to build the Android version in the future, follow this 5-stage roadmap:

### Stage 1: Build a Lightweight API Bridge (Recommended)
While an Android app can connect directly to PostgreSQL, direct DB connections from mobile devices can be fragile on spotty mobile 4G/5G connections.
- Create a small REST API in Python using **FastAPI** (running on free hosting like Render or Railway):
  - `POST /api/login` (phone number authentication)
  - `GET /api/coins` (get watchlist)
  - `POST /api/alerts` (create or update alert)
  - `GET /api/history` (view trigger history)

### Stage 2: Create the Flutter Mobile App
- Set up a Flutter project (`flutter create crypto_alert_app`).
- Implement the 3 primary screens matching the desktop theme:
  1. **Login Screen**: Minimalist dark-mode screen with User / Admin buttons and phone entry.
  2. **Watchlist Dashboard**: Live price ticker from Binance WebSocket/REST with green/red flash indicators and coin logos.
  3. **Alert Modal**: Bottom sheet slider to set Above/Below target and toggle Loop mode.

### Stage 3: Implement the Android Background Alarm Service
- Use the **`flutter_local_notifications`** and **`android_alarm_manager_plus`** packages.
- Configure an Android Notification Channel with:
  - `Importance: Max` (High-priority heads-up banner)
  - `Sound: Custom alert.mp3` stored in `android/app/src/main/res/raw/allert.mp3`
  - `AudioAttributes: USAGE_ALARM` (bypasses silent/vibrate switches if configured as an emergency alarm).

### Stage 4: Admin Panel on Mobile
- If logged in with admin credentials (`9899654695`), the mobile app displays an **Admin Drawer**:
  - List of all users with circular profile pictures.
  - Ability to create users, edit names/passwords, or delete accounts right from your phone.
  - Real-time global alert trigger feed.

### Stage 5: Exporting & Installing the APK
- You don't need Google Play Store to use it on your phone!
- Run:
  ```bash
  flutter build apk --release
  ```
- This generates a standalone file: `build/app/outputs/flutter-apk/app-release.apk`.
- Send this `.apk` to your phone via WhatsApp, Google Drive, or USB cable, tap **Install**, and it is ready to run!

---

## 💻 Sample Code: How Android Queries Your NeonDB

Here is an example in Dart (Flutter) showing how the Android app connects directly to your NeonDB instance using the `postgres` package:

```dart
import 'package:postgres/postgres.dart';

class DatabaseService {
  static final PostgreSQLConnection connection = PostgreSQLConnection(
    'ep-summer-paper-b3369gg8-pooler.c-4.ap-southeast-1.aws.neon.tech',
    5432,
    'neondb',
    username: 'neondb_owner',
    password: 'npg_khqMJtF2bO8e',
    useSSL: true,
  );

  /// Fetch active alerts for logged-in user
  static Future<List<Map<String, dynamic>>> fetchUserAlerts(int userId) async {
    if (!connection.isClosed) await connection.open();
    
    final results = await connection.query(
      'SELECT symbol, alert_type, threshold, is_loop FROM user_alerts WHERE user_id = @id AND is_active = TRUE',
      substitutionValues: {'id': userId},
    );

    return results.map((row) => {
      'symbol': row[0],
      'alert_type': row[1],
      'threshold': row[2],
      'is_loop': row[3],
    }).toList();
  }
}
```

---

## 📋 Checklist for When You Are Ready to Build the Android App

- [ ] Choose approach: **Flutter** (recommended) or **React Native**.
- [ ] Install **Flutter SDK** and **Android Studio** on your PC.
- [ ] Add the PostgreSQL connection string or build the FastAPI bridge.
- [ ] Bundle `allert.mp3` into Android raw audio resources (`res/raw/`).
- [ ] Request `POST_NOTIFICATIONS` and `SCHEDULE_EXACT_ALARM` permissions in `AndroidManifest.xml`.
- [ ] Build release APK and install on test phone.
- [ ] Test cross-device sync: Add coin on PC -> Watch it appear on phone -> Trigger alert!
