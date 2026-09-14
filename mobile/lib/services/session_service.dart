// lib/services/session_service.dart
// ─────────────────────────────────────────────────────────────────────────────
// Persists login session securely on the device using flutter_secure_storage
// ─────────────────────────────────────────────────────────────────────────────

import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/models.dart';

class SessionService {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );
  static const _key = 'kos_session';

  static Future<void> saveSession(UserSession session) async {
    await _storage.write(key: _key, value: jsonEncode(session.toJson()));
  }

  static Future<UserSession?> loadSession() async {
    try {
      final raw = await _storage.read(key: _key);
      if (raw == null) return null;
      return UserSession.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  static Future<void> clearSession() async {
    await _storage.delete(key: _key);
  }
}
