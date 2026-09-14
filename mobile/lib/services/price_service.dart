// lib/services/price_service.dart
// ─────────────────────────────────────────────────────────────────────────────
// Fetches live prices from Binance Public REST API (no API key needed)
// ─────────────────────────────────────────────────────────────────────────────

import 'dart:convert';
import 'package:http/http.dart' as http;

class PriceService {
  static const String _base = 'https://api.binance.com/api/v3';

  /// Fetch current price for a single symbol e.g. "BTCUSDT"
  static Future<double?> getPrice(String symbol) async {
    try {
      final uri = Uri.parse('$_base/ticker/price?symbol=$symbol');
      final res = await http.get(uri).timeout(const Duration(seconds: 8));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        return double.tryParse(data['price'] as String);
      }
    } catch (_) {}
    return null;
  }

  /// Fetch 24hr stats for a single symbol
  static Future<Map<String, dynamic>?> get24hrStats(String symbol) async {
    try {
      final uri = Uri.parse('$_base/ticker/24hr?symbol=$symbol');
      final res = await http.get(uri).timeout(const Duration(seconds: 10));
      if (res.statusCode == 200) {
        return jsonDecode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  /// Fetch prices for multiple symbols in one call
  static Future<Map<String, double>> getPrices(List<String> symbols) async {
    final result = <String, double>{};
    if (symbols.isEmpty) return result;

    try {
      // Binance supports comma-separated list with ["BTC","ETH"] format
      final symbolsJson = jsonEncode(symbols);
      final uri = Uri.parse(
          '$_base/ticker/price?symbols=${Uri.encodeComponent(symbolsJson)}');
      final res = await http.get(uri).timeout(const Duration(seconds: 10));
      if (res.statusCode == 200) {
        final list = jsonDecode(res.body) as List;
        for (final item in list) {
          final sym = item['symbol'] as String;
          final price = double.tryParse(item['price'] as String);
          if (price != null) result[sym] = price;
        }
      }
    } catch (_) {
      // Fallback: fetch one by one
      for (final sym in symbols) {
        final p = await getPrice(sym);
        if (p != null) result[sym] = p;
      }
    }
    return result;
  }

  /// Search Binance for available symbols matching a query
  static Future<List<Map<String, String>>> searchSymbols(String query) async {
    try {
      final uri = Uri.parse('$_base/ticker/price');
      final res = await http.get(uri).timeout(const Duration(seconds: 10));
      if (res.statusCode == 200) {
        final list = jsonDecode(res.body) as List;
        final q = query.toUpperCase();
        return list
            .where((e) => (e['symbol'] as String).contains(q) &&
                (e['symbol'] as String).endsWith('USDT'))
            .take(20)
            .map((e) {
              final sym = e['symbol'] as String;
              final display = sym.replaceAll('USDT', '');
              return {'symbol': sym, 'display': display};
            })
            .toList();
      }
    } catch (_) {}
    return [];
  }

  /// Format price nicely
  static String formatPrice(double price) {
    if (price >= 1000) {
      return price.toStringAsFixed(2);
    } else if (price >= 1) {
      return price.toStringAsFixed(4);
    } else {
      return price.toStringAsFixed(8);
    }
  }
}
