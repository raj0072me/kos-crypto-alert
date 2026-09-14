// lib/models/models.dart
// ─────────────────────────────────────────────────────────────────────────────
// Shared data models matching the NeonDB schema exactly
// ─────────────────────────────────────────────────────────────────────────────

import 'dart:convert';
import 'dart:typed_data';

class UserSession {
  final int userId;
  final String displayName;
  final String phone;
  final bool isAdmin;
  final String token;

  /// Raw PNG bytes from the database profile_pic column.
  /// Null when the user hasn't uploaded a photo yet.
  final Uint8List? profilePicBytes;

  const UserSession({
    required this.userId,
    required this.displayName,
    required this.phone,
    required this.isAdmin,
    required this.token,
    this.profilePicBytes,
  });

  /// Initials derived from display name — shown when no profile pic exists.
  String get initials {
    final parts = displayName.trim().split(RegExp(r'\s+'));
    if (parts.length >= 2) {
      return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
    }
    return displayName.isNotEmpty
        ? displayName.substring(0, displayName.length.clamp(0, 2)).toUpperCase()
        : '?';
  }

  Map<String, dynamic> toJson() => {
    'userId': userId,
    'displayName': displayName,
    'phone': phone,
    'isAdmin': isAdmin,
    'token': token,
    // profilePicBytes is not persisted to secure storage (too large);
    // it is re-fetched on every login.
  };

  factory UserSession.fromJson(Map<String, dynamic> j) => UserSession(
    userId: j['userId'] as int,
    displayName: j['displayName'] as String,
    phone: j['phone'] as String? ?? '',
    isAdmin: j['isAdmin'] as bool,
    token: j['token'] as String,
    // profilePicBytes not stored — will be null after cold-start resume
    profilePicBytes: null,
  );
}

class WatchedCoin {
  final int id;
  final int userId;
  final String symbol;       // e.g. "BTCUSDT"
  final String displaySymbol; // e.g. "BTC"

  // Live price (not stored in DB, fetched at runtime)
  double? currentPrice;
  double? priceChange24h;
  bool  priceUp = true;

  WatchedCoin({
    required this.id,
    required this.userId,
    required this.symbol,
    required this.displaySymbol,
    this.currentPrice,
    this.priceChange24h,
  });

  factory WatchedCoin.fromJson(Map<String, dynamic> j) => WatchedCoin(
    id: j['id'] as int,
    userId: j['user_id'] as int,
    symbol: j['symbol'] as String,
    displaySymbol: j['display_symbol'] as String,
  );
}

class CoinAlert {
  final int id;
  final int userId;
  final String symbol;
  final String alertUuid;
  final String alertType;   // 'above' | 'below'
  final double price;
  final String? label;
  bool isActive;
  final bool loopAlarm;

  CoinAlert({
    required this.id,
    required this.userId,
    required this.symbol,
    required this.alertUuid,
    required this.alertType,
    required this.price,
    this.label,
    required this.isActive,
    required this.loopAlarm,
  });

  factory CoinAlert.fromJson(Map<String, dynamic> j) => CoinAlert(
    id: j['id'] as int,
    userId: j['user_id'] as int,
    symbol: j['symbol'] as String,
    alertUuid: j['alert_uuid'] as String,
    alertType: j['alert_type'] as String,
    price: double.parse(j['price'].toString()),
    label: j['label'] as String?,
    isActive: j['is_active'] as bool,
    loopAlarm: j['loop_alarm'] as bool,
  );
}

class AppUser {
  final int id;
  final String phone;
  final String displayName;
  final bool isAdmin;

  /// Decoded PNG bytes — null if no photo has been set.
  final Uint8List? profilePicBytes;

  const AppUser({
    required this.id,
    required this.phone,
    required this.displayName,
    required this.isAdmin,
    this.profilePicBytes,
  });

  factory AppUser.fromJson(Map<String, dynamic> j) => AppUser(
    id: j['id'] as int,
    phone: j['phone'] as String,
    displayName: j['display_name'] as String,
    isAdmin: j['is_admin'] as bool? ?? false,
    profilePicBytes: _decodeProfilePic(j['profile_pic']),
  );

  /// Handles PostgreSQL bytea returned by Neon HTTP API.
  ///
  /// Neon returns bytea in one of two ways:
  ///   • As a hex string prefixed with `\x`  → we decode the hex
  ///   • As a base64 string                  → we base64-decode it
  static Uint8List? _decodeProfilePic(dynamic value) {
    if (value == null) return null;
    try {
      if (value is Uint8List) return value;
      if (value is List<int>) return Uint8List.fromList(value);
      final str = value.toString().trim();
      if (str.isEmpty) return null;

      // Handle PostgreSQL hex bytea format: \x89504e47... or \\x89504e47...
      String hex = str;
      if (hex.startsWith(r'\x') || hex.startsWith('\\x')) {
        hex = hex.replaceFirst(RegExp(r'^\\*x'), '');
      }

      if (RegExp(r'^[0-9a-fA-F]+$').hasMatch(hex) && hex.length % 2 == 0) {
        final len = hex.length ~/ 2;
        final bytes = Uint8List(len);
        for (var i = 0; i < len; i++) {
          bytes[i] = int.parse(hex.substring(i * 2, i * 2 + 2), radix: 16);
        }
        return bytes;
      }

      return base64Decode(str);
    } catch (_) {
      return null;
    }
  }
}
