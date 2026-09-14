// lib/services/db_service.dart
// ─────────────────────────────────────────────────────────────────────────────
// NeonDB access via HTTP REST (no native PostgreSQL driver needed).
// We use Neon's built-in HTTP endpoint so we don't need the postgres package
// and there are zero native library issues on Android.
//
// Neon HTTP API:  POST https://<host>/sql
//   Headers: { "Authorization": "Bearer <password>", "Neon-Connection-String": "<url>", "Content-Type": "application/json" }
//   Body:    { "query": "SELECT ...", "params": [...] }
// ─────────────────────────────────────────────────────────────────────────────

import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/models.dart';

class DbService {
  // ── Connection config (matches db_manager.py) ─────────────────────────────
  static const String _host =
      'ep-summer-paper-b3369gg8-pooler.c-4.ap-southeast-1.aws.neon.tech';
  static const String _database = 'neondb';
  static const String _user     = 'neondb_owner';
  static const String _password = 'npg_khqMJtF2bO8e';
  static const String _adminPhone = '9899654695';

  static String get _connectionString =>
      'postgresql://$_user:$_password@$_host/$_database?sslmode=require';

  static final Uri _sqlEndpoint = Uri.parse('https://$_host/sql/v1');

  static Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer $_password',
    'Neon-Connection-String': _connectionString,
  };

  // ── Generic query helper ──────────────────────────────────────────────────
  static Future<List<Map<String, dynamic>>> _query(
      String sql, List<dynamic> params) async {
    final body = jsonEncode({'query': sql, 'params': params});
    final response = await http
        .post(_sqlEndpoint, headers: _headers, body: body)
        .timeout(const Duration(seconds: 15));

    if (response.statusCode != 200) {
      throw Exception('DB error ${response.statusCode}: ${response.body}');
    }
    final decoded = jsonDecode(response.body);
    // Neon HTTP response: { "rows": [...], "fields": [...] }
    final rows = decoded['rows'] as List<dynamic>? ?? [];
    return rows.cast<Map<String, dynamic>>();
  }

  static Future<void> _execute(String sql, List<dynamic> params) async {
    await _query(sql, params);
  }

  // ── Auth ──────────────────────────────────────────────────────────────────

  /// Get user by phone number (no password — app uses phone-based login like PC)
  static Future<AppUser?> getUserByPhone(String phone) async {
    final rows = await _query(
      'SELECT id, phone, display_name, is_admin FROM users WHERE phone = \$1',
      [phone.trim()],
    );
    if (rows.isEmpty) return null;
    return AppUser.fromJson(rows.first);
  }

  /// Get ALL users (admin only)
  static Future<List<AppUser>> getAllUsers() async {
    final rows = await _query(
      'SELECT id, phone, display_name, is_admin FROM users ORDER BY created_at',
      [],
    );
    return rows.map(AppUser.fromJson).toList();
  }

  /// Create a new user (admin only)
  static Future<int> createUser(String phone, String displayName,
      {bool isAdmin = false}) async {
    final rows = await _query(
      'INSERT INTO users (phone, display_name, is_admin) VALUES (\$1, \$2, \$3) RETURNING id',
      [phone.trim(), displayName.trim(), isAdmin],
    );
    return rows.first['id'] as int;
  }

  /// Update last login timestamp
  static Future<void> updateLastLogin(int userId) async {
    await _execute(
        'UPDATE users SET last_login = NOW() WHERE id = \$1', [userId]);
  }

  // ── Watched Coins ─────────────────────────────────────────────────────────

  static Future<List<WatchedCoin>> getWatchedCoins(int userId) async {
    final rows = await _query(
      'SELECT id, user_id, symbol, display_symbol FROM user_watched_coins WHERE user_id = \$1 ORDER BY added_at',
      [userId],
    );
    return rows.map(WatchedCoin.fromJson).toList();
  }

  static Future<void> addWatchedCoin(
      int userId, String symbol, String displaySymbol) async {
    await _execute(
      'INSERT INTO user_watched_coins (user_id, symbol, display_symbol) VALUES (\$1, \$2, \$3) ON CONFLICT DO NOTHING',
      [userId, symbol.toUpperCase(), displaySymbol.toUpperCase()],
    );
  }

  static Future<void> removeWatchedCoin(int userId, String symbol) async {
    await _execute(
      'DELETE FROM user_watched_coins WHERE user_id = \$1 AND symbol = \$2',
      [userId, symbol],
    );
  }

  // ── Alerts ────────────────────────────────────────────────────────────────

  static Future<List<CoinAlert>> getActiveAlerts(int userId) async {
    final rows = await _query(
      '''SELECT id, user_id, symbol, alert_uuid, alert_type, price, label, is_active, loop_alarm
         FROM user_alerts
         WHERE user_id = \$1 AND is_active = TRUE
         ORDER BY created_at''',
      [userId],
    );
    return rows.map(CoinAlert.fromJson).toList();
  }

  static Future<void> createAlert({
    required int userId,
    required String symbol,
    required String alertUuid,
    required String alertType,  // 'above' | 'below'
    required double price,
    String? label,
    bool loopAlarm = false,
  }) async {
    await _execute(
      '''INSERT INTO user_alerts (user_id, symbol, alert_uuid, alert_type, price, label, loop_alarm)
         VALUES (\$1, \$2, \$3, \$4, \$5, \$6, \$7)''',
      [userId, symbol, alertUuid, alertType, price, label ?? '', loopAlarm],
    );
  }

  static Future<void> deactivateAlert(String alertUuid) async {
    await _execute(
      'UPDATE user_alerts SET is_active = FALSE WHERE alert_uuid = \$1',
      [alertUuid],
    );
  }

  static Future<void> deleteAlert(String alertUuid) async {
    await _execute(
      'DELETE FROM user_alerts WHERE alert_uuid = \$1',
      [alertUuid],
    );
  }

  // ── Alert History ─────────────────────────────────────────────────────────

  static Future<void> logAlertHistory({
    required int userId,
    required String symbol,
    required String alertType,
    required double triggerPrice,
    required double threshold,
  }) async {
    await _execute(
      '''INSERT INTO alert_history (user_id, symbol, alert_type, trigger_price, threshold)
         VALUES (\$1, \$2, \$3, \$4, \$5)''',
      [userId, symbol, alertType, triggerPrice, threshold],
    );
  }

  static Future<List<Map<String, dynamic>>> getAlertHistory(int userId,
      {int limit = 50}) async {
    return _query(
      '''SELECT symbol, alert_type, trigger_price, threshold, triggered_at
         FROM alert_history WHERE user_id = \$1
         ORDER BY triggered_at DESC LIMIT \$2''',
      [userId, limit],
    );
  }

  // ── Admin: delete user ────────────────────────────────────────────────────
  static Future<void> deleteUser(int userId) async {
    await _execute('DELETE FROM users WHERE id = \$1', [userId]);
  }

  static String get adminPhone => _adminPhone;
}
