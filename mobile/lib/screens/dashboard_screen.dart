// lib/screens/dashboard_screen.dart
// ─────────────────────────────────────────────────────────────────────────────
// Main Dashboard: Live Binance prices, NeonDB alert sync, and real-time triggers.
// ─────────────────────────────────────────────────────────────────────────────

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:workmanager/workmanager.dart';

import '../models/models.dart';
import '../services/db_service.dart';
import '../services/price_service.dart';
import '../services/alarm_service.dart';
import '../services/session_service.dart';
import '../services/background_task.dart';
import 'login_screen.dart';
import 'admin_screen.dart';
import 'add_alert_dialog.dart';

class DashboardScreen extends StatefulWidget {
  final UserSession session;
  const DashboardScreen({super.key, required this.session});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> with WidgetsBindingObserver {
  List<WatchedCoin> _coins = [];
  List<CoinAlert> _alerts = [];
  Map<String, double> _prevPrices = {};
  Timer? _priceTimer;
  bool _loading = true;
  bool _isAlarmRinging = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initDashboard();
    _startWorkManager();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _priceTimer?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _pollPrices();
      _checkAlarmStatus();
    }
  }

  void _checkAlarmStatus() {
    if (mounted) {
      setState(() => _isAlarmRinging = AlarmService.isRinging);
    }
  }

  Future<void> _initDashboard() async {
    await _loadCoinsAndAlerts();
    // Start fast foreground polling (every 4 seconds)
    _priceTimer = Timer.periodic(const Duration(seconds: 4), (_) => _pollPrices());
  }

  void _startWorkManager() {
    // Schedule background periodic price check (every 15 mins by Android limits)
    Workmanager().registerPeriodicTask(
      'kos_periodic_monitor',
      BackgroundTask.taskName,
      frequency: const Duration(minutes: 15),
      existingWorkPolicy: ExistingWorkPolicy.keep,
    );
  }

  Future<void> _loadCoinsAndAlerts() async {
    try {
      final coins = await DbService.getWatchedCoins(widget.session.userId);
      final alerts = await DbService.getActiveAlerts(widget.session.userId);

      if (mounted) {
        setState(() {
          _coins = coins;
          _alerts = alerts;
          _loading = false;
        });
      }
      await _pollPrices();
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _pollPrices() async {
    if (_coins.isEmpty) return;
    final symbols = _coins.map((c) => c.symbol).toList();
    final prices = await PriceService.getPrices(symbols);

    if (!mounted) return;

    setState(() {
      for (final coin in _coins) {
        final newPrice = prices[coin.symbol];
        if (newPrice != null) {
          final old = _prevPrices[coin.symbol] ?? newPrice;
          coin.priceUp = newPrice >= old;
          coin.currentPrice = newPrice;
          _prevPrices[coin.symbol] = newPrice;
        }
      }
    });

    // Check alerts in foreground
    _evaluateAlerts(prices);
  }

  Future<void> _evaluateAlerts(Map<String, double> prices) async {
    for (final alert in _alerts) {
      if (!alert.isActive) continue;
      final currentPrice = prices[alert.symbol];
      if (currentPrice == null) continue;

      bool trigger = false;
      if (alert.alertType == 'above' && currentPrice >= alert.price) {
        trigger = true;
      } else if (alert.alertType == 'below' && currentPrice <= alert.price) {
        trigger = true;
      }

      if (trigger) {
        setState(() => _isAlarmRinging = true);
        await AlarmService.fireAlarm(
          symbol: alert.symbol.replaceAll('USDT', ''),
          alertType: alert.alertType,
          triggerPrice: currentPrice,
          threshold: alert.price,
          loop: alert.loopAlarm,
        );

        await DbService.logAlertHistory(
          userId: widget.session.userId,
          symbol: alert.symbol,
          alertType: alert.alertType,
          triggerPrice: currentPrice,
          threshold: alert.price,
        );

        if (!alert.loopAlarm) {
          alert.isActive = false;
          await DbService.deactivateAlert(alert.alertUuid);
        }
      }
    }
  }

  Future<void> _stopAlarmNow() async {
    await AlarmService.stopAlarm();
    setState(() => _isAlarmRinging = false);
  }

  Future<void> _showAddCoinDialog() async {
    final searchCtrl = TextEditingController();
    List<Map<String, String>> searchResults = [];
    bool isSearching = false;

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF161B22),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setModalState) => Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(ctx).viewInsets.bottom,
            top: 20,
            left: 20,
            right: 20,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Add Coin to Watchlist',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: searchCtrl,
                textCapitalization: TextCapitalization.characters,
                decoration: const InputDecoration(
                  hintText: 'Search coin e.g. SOL, DOGE, ADA',
                  prefixIcon: Icon(Icons.search_rounded),
                ),
                onChanged: (v) async {
                  if (v.trim().isEmpty) return;
                  setModalState(() => isSearching = true);
                  final res = await PriceService.searchSymbols(v.trim());
                  setModalState(() {
                    searchResults = res;
                    isSearching = false;
                  });
                },
              ),
              const SizedBox(height: 12),
              if (isSearching) const LinearProgressIndicator(),
              SizedBox(
                height: 240,
                child: ListView.builder(
                  itemCount: searchResults.length,
                  itemBuilder: (c, idx) {
                    final item = searchResults[idx];
                    return ListTile(
                      title: Text(item['display'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold)),
                      subtitle: Text(item['symbol'] ?? '', style: const TextStyle(color: Color(0xFF8B949E))),
                      trailing: const Icon(Icons.add_circle_outline_rounded, color: Color(0xFF00D4AA)),
                      onTap: () async {
                        await DbService.addWatchedCoin(
                          widget.session.userId,
                          item['symbol']!,
                          item['display']!,
                        );
                        Navigator.pop(ctx);
                        _loadCoinsAndAlerts();
                      },
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    const primary = Color(0xFF00D4AA);
    const cardBg = Color(0xFF161B22);
    const textMuted = Color(0xFF8B949E);

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.show_chart_rounded, color: primary, size: 24),
            const SizedBox(width: 8),
            Text(widget.session.displayName),
          ],
        ),
        actions: [
          if (widget.session.isAdmin)
            IconButton(
              icon: const Icon(Icons.admin_panel_settings_rounded, color: primary),
              tooltip: 'Admin Console',
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const AdminScreen()),
              ),
            ),
          IconButton(
            icon: const Icon(Icons.logout_rounded),
            tooltip: 'Logout',
            onPressed: () async {
              await SessionService.clearSession();
              if (mounted) {
                Navigator.of(context).pushReplacement(
                  MaterialPageRoute(builder: (_) => const LoginScreen()),
                );
              }
            },
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: primary,
        foregroundColor: Colors.black,
        icon: const Icon(Icons.add_rounded),
        label: const Text('Add Coin', style: TextStyle(fontWeight: FontWeight.bold)),
        onPressed: _showAddCoinDialog,
      ),
      body: Column(
        children: [
          // Flashing Banner when Alarm is Ringing
          if (_isAlarmRinging)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              color: const Color(0xFFDA3633),
              child: Row(
                children: [
                  const Icon(Icons.warning_amber_rounded, color: Colors.white),
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Text(
                      '🚨 ALARM RINGING!',
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                    ),
                  ),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(backgroundColor: Colors.white, foregroundColor: Colors.black),
                    onPressed: _stopAlarmNow,
                    child: const Text('DISMISS'),
                  ),
                ],
              ),
            ),

          // Main List
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _coins.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.currency_bitcoin_rounded, size: 64, color: textMuted.withOpacity(0.5)),
                            const SizedBox(height: 12),
                            const Text('No coins added yet', style: TextStyle(color: textMuted, fontSize: 16)),
                            const SizedBox(height: 8),
                            ElevatedButton(
                              onPressed: _showAddCoinDialog,
                              child: const Text('Add Your First Coin'),
                            ),
                          ],
                        ),
                      )
                    : RefreshIndicator(
                        onRefresh: _loadCoinsAndAlerts,
                        child: ListView.builder(
                          padding: const EdgeInsets.fromLTRB(16, 12, 16, 80),
                          itemCount: _coins.length,
                          itemBuilder: (ctx, idx) {
                            final coin = _coins[idx];
                            final coinAlerts = _alerts.where((a) => a.symbol == coin.symbol && a.isActive).toList();
                            final isUp = coin.priceUp;

                            return Card(
                              margin: const EdgeInsets.only(bottom: 12),
                              child: Padding(
                                padding: const EdgeInsets.all(14.0),
                                child: Column(
                                  children: [
                                    // Header: Symbol + Live Price + Action
                                    Row(
                                      children: [
                                        // Coin Avatar
                                        CircleAvatar(
                                          backgroundColor: primary.withOpacity(0.15),
                                          child: Text(
                                            coin.displaySymbol.substring(0, coin.displaySymbol.length.clamp(0, 3)),
                                            style: const TextStyle(fontWeight: FontWeight.bold, color: primary, fontSize: 12),
                                          ),
                                        ),
                                        const SizedBox(width: 12),
                                        // Symbol info
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                coin.displaySymbol,
                                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
                                              ),
                                              Text(
                                                coin.symbol,
                                                style: const TextStyle(color: textMuted, fontSize: 12),
                                              ),
                                            ],
                                          ),
                                        ),
                                        // Price Ticker
                                        Column(
                                          crossAxisAlignment: CrossAxisAlignment.end,
                                          children: [
                                            Text(
                                              coin.currentPrice != null
                                                  ? '\$${PriceService.formatPrice(coin.currentPrice!)}'
                                                  : 'Loading...',
                                              style: TextStyle(
                                                fontWeight: FontWeight.bold,
                                                fontSize: 16,
                                                color: coin.currentPrice != null
                                                    ? (isUp ? const Color(0xFF00D4AA) : const Color(0xFFFF6B6B))
                                                    : Colors.white,
                                              ),
                                            ),
                                            Text(
                                              isUp ? '▲ Ticking up' : '▼ Ticking down',
                                              style: TextStyle(
                                                fontSize: 10,
                                                color: isUp ? const Color(0xFF00D4AA) : const Color(0xFFFF6B6B),
                                              ),
                                            ),
                                          ],
                                        ),
                                        const SizedBox(width: 8),
                                        // Set Alert Button
                                        IconButton(
                                          icon: const Icon(Icons.notification_add_rounded, color: primary),
                                          tooltip: 'Set Alert',
                                          onPressed: coin.currentPrice == null
                                              ? null
                                              : () async {
                                                  final created = await showDialog<bool>(
                                                    context: context,
                                                    builder: (_) => AddAlertDialog(
                                                      userId: widget.session.userId,
                                                      coin: coin,
                                                      currentPrice: coin.currentPrice!,
                                                    ),
                                                  );
                                                  if (created == true) _loadCoinsAndAlerts();
                                                },
                                        ),
                                        // Delete Coin
                                        IconButton(
                                          icon: const Icon(Icons.close_rounded, size: 18, color: textMuted),
                                          tooltip: 'Remove Coin',
                                          onPressed: () async {
                                            await DbService.removeWatchedCoin(widget.session.userId, coin.symbol);
                                            _loadCoinsAndAlerts();
                                          },
                                        ),
                                      ],
                                    ),

                                    // Active Alerts under this coin
                                    if (coinAlerts.isNotEmpty) ...[
                                      const Divider(color: Color(0xFF30363D), height: 20),
                                      Wrap(
                                        spacing: 8,
                                        runSpacing: 6,
                                        children: coinAlerts.map((a) {
                                          final isAbove = a.alertType == 'above';
                                          return Chip(
                                            backgroundColor: isAbove
                                                ? const Color(0xFF238636).withOpacity(0.25)
                                                : const Color(0xFFDA3633).withOpacity(0.25),
                                            side: BorderSide(
                                              color: isAbove ? const Color(0xFF238636) : const Color(0xFFDA3633),
                                            ),
                                            label: Text(
                                              '${isAbove ? '▲ >' : '▼ <'} \$${PriceService.formatPrice(a.price)} ${a.loopAlarm ? '🔁' : ''}',
                                              style: TextStyle(
                                                fontSize: 11,
                                                fontWeight: FontWeight.bold,
                                                color: isAbove ? const Color(0xFF3FB950) : const Color(0xFFF85149),
                                              ),
                                            ),
                                            deleteIcon: const Icon(Icons.close_rounded, size: 14),
                                            onDeleted: () async {
                                              await DbService.deleteAlert(a.alertUuid);
                                              _loadCoinsAndAlerts();
                                            },
                                          );
                                        }).toList(),
                                      ),
                                    ],
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}
