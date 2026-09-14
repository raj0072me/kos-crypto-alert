// lib/widgets/coin_icon.dart
// ─────────────────────────────────────────────────────────────────────────────
// Renders cryptocurrency icons with automatic CDN fetching and fallback badges.
// ─────────────────────────────────────────────────────────────────────────────

import 'package:flutter/material.dart';

class CoinIcon extends StatelessWidget {
  final String symbol; // e.g. "BTC", "BTCUSDT", "ETH", "SOL"
  final double size;

  const CoinIcon({
    super.key,
    required this.symbol,
    this.size = 38,
  });

  static const Set<String> _bundledCoins = {
    'btc', 'eth', 'sol', 'bnb', 'xrp', 'alice',
  };

  String get _cleanSymbol {
    var sym = symbol.trim().toUpperCase();
    if (sym.endsWith('USDT') && sym.length > 4) {
      sym = sym.substring(0, sym.length - 4);
    } else if (sym.endsWith('BUSD') && sym.length > 4) {
      sym = sym.substring(0, sym.length - 4);
    } else if (sym.endsWith('BTC') && sym.length > 3) {
      sym = sym.substring(0, sym.length - 3);
    }
    return sym.toLowerCase();
  }

  @override
  Widget build(BuildContext context) {
    final clean = _cleanSymbol;

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: const Color(0xFF21262D),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.25),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: ClipOval(
        child: _bundledCoins.contains(clean)
            ? Image.asset(
                'assets/coins/$clean.png',
                width: size,
                height: size,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => _buildNetworkIcon(clean),
              )
            : _buildNetworkIcon(clean),
      ),
    );
  }

  Widget _buildNetworkIcon(String clean) {
    return Image.network(
      'https://assets.coincap.io/assets/icons/$clean@2x.png',
      width: size,
      height: size,
      fit: BoxFit.cover,
      errorBuilder: (_, __, ___) {
        return Image.network(
          'https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/$clean.png',
          width: size,
          height: size,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => _buildFallbackBadge(clean),
        );
      },
    );
  }

  Widget _buildFallbackBadge(String clean) {
    const palette = [
      [Color(0xFFF7931A), Colors.white], // Orange (BTC)
      [Color(0xFF627EEA), Colors.white], // Blue (ETH)
      [Color(0xFF14F195), Colors.black], // Green (SOL)
      [Color(0xFFF3BA2F), Colors.black], // Yellow (BNB)
      [Color(0xFF2775CA), Colors.white], // Deep Blue
      [Color(0xFFE84142), Colors.white], // Red (AVAX)
      [Color(0xFFA052FF), Colors.white], // Purple
      [Color(0xFF00B8D9), Colors.white], // Cyan
    ];

    final hash = clean.codeUnits.fold<int>(0, (prev, elem) => prev + elem);
    final colorPair = palette[hash % palette.length];
    final text = clean.isNotEmpty
        ? (clean.length <= 3 ? clean.toUpperCase() : clean.substring(0, 2).toUpperCase())
        : '?';

    return Container(
      width: size,
      height: size,
      color: colorPair[0],
      alignment: Alignment.center,
      child: Text(
        text,
        style: TextStyle(
          color: colorPair[1],
          fontWeight: FontWeight.bold,
          fontSize: size * 0.36,
          letterSpacing: -0.5,
        ),
      ),
    );
  }
}
