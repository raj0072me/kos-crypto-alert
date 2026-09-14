// lib/services/alarm_service.dart
// ─────────────────────────────────────────────────────────────────────────────
// Handles the Android alarm notification channel and audio playback.
// Uses USAGE_ALARM audio stream so it rings even in Do Not Disturb / Silent.
// ─────────────────────────────────────────────────────────────────────────────

import 'dart:ui';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:vibration/vibration.dart';
import 'price_service.dart';

class AlarmService {
  static final FlutterLocalNotificationsPlugin _notifs =
      FlutterLocalNotificationsPlugin();

  static AudioPlayer? _player;
  static bool _ringing = false;

  // ── Notification channel config ────────────────────────────────────────────
  static const String _channelId   = 'kos_crypto_alarm';
  static const String _channelName = 'Crypto Alarms';
  static const String _monitorId   = 'kos_monitor';
  static const String _monitorName = 'Price Monitor';

  static Future<void> initialize() async {
    const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
    const initSettings = InitializationSettings(android: androidInit);

    await _notifs.initialize(
      initSettings,
      onDidReceiveNotificationResponse: (details) async {
        // User tapped notification → stop alarm
        await stopAlarm();
      },
    );

    // Create the high-priority ALARM channel
    const alarmChannel = AndroidNotificationChannel(
      _channelId,
      _channelName,
      description: 'Crypto price alert alarms',
      importance: Importance.max,
      playSound: true,
      enableVibration: true,
      enableLights: true,
      ledColor: Color(0xFF00D4AA),
    );

    // Create the silent monitor channel (persistent notification)
    const monitorChannel = AndroidNotificationChannel(
      _monitorId,
      _monitorName,
      description: 'Background price monitoring service',
      importance: Importance.low,
      playSound: false,
      enableVibration: false,
    );

    final androidPlugin = _notifs
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();

    await androidPlugin?.createNotificationChannel(alarmChannel);
    await androidPlugin?.createNotificationChannel(monitorChannel);
    await androidPlugin?.requestNotificationsPermission();
    await androidPlugin?.requestExactAlarmsPermission();
  }

  // ── FIRE ALARM: called when a price target is crossed ─────────────────────

  static Future<void> fireAlarm({
    required String symbol,
    required String alertType,  // 'above' | 'below'
    required double triggerPrice,
    required double threshold,
    bool loop = false,
  }) async {
    if (_ringing && !loop) return;
    _ringing = true;

    // Vibrate pattern: long-short-long
    if (await Vibration.hasVibrator() ?? false) {
      Vibration.vibrate(pattern: [0, 500, 200, 500, 200, 1000], repeat: loop ? 0 : -1);
    }

    final direction = alertType == 'above' ? '▲ ABOVE' : '▼ BELOW';
    final title = '🚨 $symbol $direction \$${PriceService.formatPrice(threshold)}';
    final body  = 'Current: \$${PriceService.formatPrice(triggerPrice)}  •  Tap to dismiss';

    // Show full-screen intent (lock-screen banner like a phone call)
    final androidDetails = AndroidNotificationDetails(
      _channelId,
      _channelName,
      importance: Importance.max,
      priority: Priority.max,
      fullScreenIntent: true,            // Pops over lock screen
      category: AndroidNotificationCategory.alarm,
      ticker: '$symbol alert triggered',
      ongoing: loop,                     // Loop alerts cannot be swiped away
      autoCancel: !loop,
      color: const Color(0xFF00D4AA),
      ledColor: const Color(0xFF00D4AA),
      ledOnMs: 200,
      ledOffMs: 800,
    );

    await _notifs.show(
      symbol.hashCode,
      title,
      body,
      NotificationDetails(android: androidDetails),
    );

    // Play alarm sound
    _player = AudioPlayer();
    await _player!.setReleaseMode(loop ? ReleaseMode.loop : ReleaseMode.stop);
    await _player!.play(AssetSource('sounds/alert.mp3'));
  }

  // ── STOP ALARM ────────────────────────────────────────────────────────────

  static Future<void> stopAlarm() async {
    _ringing = false;
    await _player?.stop();
    _player?.dispose();
    _player = null;
    Vibration.cancel();
    await _notifs.cancelAll();
  }

  // ── MONITOR NOTIFICATION (persistent status bar icon) ────────────────────

  static Future<void> showMonitorNotification(String statusText) async {
    const androidDetails = AndroidNotificationDetails(
      _monitorId,
      _monitorName,
      importance: Importance.low,
      priority: Priority.low,
      ongoing: true,
      autoCancel: false,
      showWhen: false,
      icon: '@mipmap/ic_launcher',
    );

    await _notifs.show(
      1,
      '📊 KoS Crypto Alerts',
      statusText,
      const NotificationDetails(android: androidDetails),
    );
  }

  static Future<void> hideMonitorNotification() async {
    await _notifs.cancel(1);
  }

  static bool get isRinging => _ringing;
}
