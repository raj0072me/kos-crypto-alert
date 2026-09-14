// lib/screens/add_alert_dialog.dart
// ─────────────────────────────────────────────────────────────────────────────
// Modal dialog to set a new Above/Below price alert on a watched coin.
// Saves directly to NeonDB user_alerts table.
// ─────────────────────────────────────────────────────────────────────────────

import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/db_service.dart';
import '../services/price_service.dart';
import '../widgets/coin_icon.dart';

class AddAlertDialog extends StatefulWidget {
  final int userId;
  final WatchedCoin coin;
  final double currentPrice;

  const AddAlertDialog({
    super.key,
    required this.userId,
    required this.coin,
    required this.currentPrice,
  });

  @override
  State<AddAlertDialog> createState() => _AddAlertDialogState();
}

class _AddAlertDialogState extends State<AddAlertDialog> {
  late TextEditingController _priceController;
  final _labelController = TextEditingController();
  String _alertType = 'above';
  bool _loopAlarm = false;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    // Default threshold is current price rounded nicely
    _priceController = TextEditingController(
      text: PriceService.formatPrice(widget.currentPrice),
    );
  }

  @override
  void dispose() {
    _priceController.dispose();
    _labelController.dispose();
    super.dispose();
  }

  Future<void> _saveAlert() async {
    final rawPrice = double.tryParse(_priceController.text.trim());
    if (rawPrice == null || rawPrice <= 0) {
      setState(() => _error = 'Please enter a valid positive price');
      return;
    }

    setState(() {
      _saving = true;
      _error = null;
    });

    try {
      final uuid = 'alert_${DateTime.now().millisecondsSinceEpoch}_${widget.coin.id}';
      await DbService.createAlert(
        userId: widget.userId,
        symbol: widget.coin.symbol,
        alertUuid: uuid,
        alertType: _alertType,
        price: rawPrice,
        label: _labelController.text.trim().isEmpty ? null : _labelController.text.trim(),
        loopAlarm: _loopAlarm,
      );

      if (!mounted) return;
      Navigator.of(context).pop(true); // Return true to trigger refresh
    } catch (e) {
      setState(() {
        _saving = false;
        _error = 'Failed to save alert: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    const primary = Color(0xFF00D4AA);
    const cardBg = Color(0xFF161B22);
    const border = Color(0xFF30363D);

    return AlertDialog(
      backgroundColor: cardBg,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: border),
      ),
      title: Row(
        children: [
          CoinIcon(symbol: widget.coin.symbol, size: 28),
          const SizedBox(width: 10),
          Text(
            'Alert: ${widget.coin.displaySymbol}',
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Current Price Banner
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: const Color(0xFF0D1117),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: border),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Live Price:', style: TextStyle(color: Color(0xFF8B949E), fontSize: 13)),
                  Text(
                    '\$${PriceService.formatPrice(widget.currentPrice)}',
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                      color: Color(0xFF00D4AA),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),

            // Direction Buttons (Above / Below)
            const Text(
              'ALERT TYPE',
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF8B949E), letterSpacing: 1),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: ChoiceChip(
                    label: const Center(child: Text('▲ Price Rises Above')),
                    selected: _alertType == 'above',
                    selectedColor: const Color(0xFF238636).withOpacity(0.4),
                    onSelected: (val) {
                      if (val) setState(() => _alertType = 'above');
                    },
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ChoiceChip(
                    label: const Center(child: Text('▼ Price Drops Below')),
                    selected: _alertType == 'below',
                    selectedColor: const Color(0xFFDA3633).withOpacity(0.4),
                    onSelected: (val) {
                      if (val) setState(() => _alertType = 'below');
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Target Price Input
            const Text(
              'TARGET PRICE (USDT)',
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF8B949E), letterSpacing: 1),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _priceController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              decoration: const InputDecoration(
                prefixText: '\$ ',
                hintText: '0.00',
              ),
            ),
            const SizedBox(height: 14),

            // Optional Label
            const Text(
              'LABEL (OPTIONAL)',
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF8B949E), letterSpacing: 1),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _labelController,
              decoration: const InputDecoration(
                hintText: 'e.g. Resistance level / Stop Loss',
              ),
            ),
            const SizedBox(height: 14),

            // Looping Alarm Switch
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Continuous Alarm Loop', style: TextStyle(fontSize: 14)),
              subtitle: const Text(
                'Rings non-stop until dismissed',
                style: TextStyle(fontSize: 12, color: Color(0xFF8B949E)),
              ),
              value: _loopAlarm,
              activeColor: primary,
              onChanged: (v) => setState(() => _loopAlarm = v),
            ),

            if (_error != null) ...[
              const SizedBox(height: 10),
              Text(_error!, style: const TextStyle(color: Color(0xFFFF6B6B), fontSize: 12)),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Cancel', style: TextStyle(color: Color(0xFF8B949E))),
        ),
        ElevatedButton(
          onPressed: _saving ? null : _saveAlert,
          style: ElevatedButton.styleFrom(
            backgroundColor: primary,
            foregroundColor: Colors.black,
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
          ),
          child: _saving
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2, valueColor: AlwaysStoppedAnimation(Colors.black)),
                )
              : const Text('Save Alert', style: TextStyle(fontWeight: FontWeight.bold)),
        ),
      ],
    );
  }
}
