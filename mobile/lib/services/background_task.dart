// lib/services/background_task.dart
// ─────────────────────────────────────────────────────────────────────────────
// WorkManager background task — runs even when app is swiped away.
// Checks prices against active alerts and fires alarms when triggered.
// ─────────────────────────────────────────────────────────────────────────────

import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/models.dart';
import 'db_service.dart';
import 'price_service.dart';
import 'alarm_service.dart';

class BackgroundTask {
  static const String taskName = 'kos_price_check';

  static Future<bool> run(String task, Map<String, dynamic>? inputData) async {
    if (task != taskName) return true;

    try {
      // Load session from secure storage
      const storage = FlutterSecureStorage(
          aOptions: AndroidOptions(encryptedSharedPreferences: true));
      final sessionRaw = await storage.read(key: 'kos_session');
      if (sessionRaw == null) return true;

      final session = UserSession.fromJson(
          jsonDecode(sessionRaw) as Map<String, dynamic>);

      // Fetch active alerts from NeonDB
      final alerts = await DbService.getActiveAlerts(session.userId);
      if (alerts.isEmpty) return true;

      // Get unique symbols
      final symbols = alerts.map((a) => a.symbol).toSet().toList();

      // Fetch current prices from Binance
      final prices = await PriceService.getPrices(symbols);

      // Check each alert
      final prefs = await SharedPreferences.getInstance();

      for (final alert in alerts) {
        final currentPrice = prices[alert.symbol];
        if (currentPrice == null) continue;

        bool triggered = false;
        if (alert.alertType == 'above' && currentPrice >= alert.price) {
          triggered = true;
        } else if (alert.alertType == 'below' && currentPrice <= alert.price) {
          triggered = true;
        }

        if (triggered) {
          // Debounce: don't fire the same alert more than once per 60 seconds
          final debounceKey = 'alerted_${alert.alertUuid}';
          final lastFired = prefs.getInt(debounceKey) ?? 0;
          final now = DateTime.now().millisecondsSinceEpoch;
          if (now - lastFired < 60000) continue;
          await prefs.setInt(debounceKey, now);

          // Fire the alarm notification
          await AlarmService.fireAlarm(
            symbol: alert.displaySymbol ?? alert.symbol,
            alertType: alert.alertType,
            triggerPrice: currentPrice,
            threshold: alert.price,
            loop: alert.loopAlarm,
          );

          // Log to history
          await DbService.logAlertHistory(
            userId: session.userId,
            symbol: alert.symbol,
            alertType: alert.alertType,
            triggerPrice: currentPrice,
            threshold: alert.price,
          );

          // Deactivate non-loop alerts
          if (!alert.loopAlarm) {
            await DbService.deactivateAlert(alert.alertUuid);
          }
        }
      }

      // Update the persistent notification with current BTC price
      final btcPrice = prices['BTCUSDT'];
      final statusText = btcPrice != null
          ? 'BTC: \$${PriceService.formatPrice(btcPrice)}  •  ${alerts.length} alert(s) active'
          : '${alerts.length} alert(s) being monitored';
      await AlarmService.showMonitorNotification(statusText);

    } catch (e) {
      // Never crash — WorkManager will retry
    }
    return true;
  }
}

// Dart extension to access displaySymbol from CoinAlert
extension _CoinAlertExt on CoinAlert {
  String? get displaySymbol => symbol.replaceAll('USDT', '');
}
