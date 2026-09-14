// lib/screens/login_screen.dart
// ─────────────────────────────────────────────────────────────────────────────
// Phone-number based login matching the desktop app UX.
// ─────────────────────────────────────────────────────────────────────────────

import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/db_service.dart';
import '../services/session_service.dart';
import 'dashboard_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _phoneController = TextEditingController();
  bool _loading = false;
  String? _errorMessage;

  @override
  void dispose() {
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin(String phone) async {
    final cleanPhone = phone.trim();
    if (cleanPhone.isEmpty) {
      setState(() => _errorMessage = 'Please enter a phone number');
      return;
    }

    setState(() {
      _loading = true;
      _errorMessage = null;
    });

    try {
      final user = await DbService.getUserByPhone(cleanPhone);
      if (user == null) {
        setState(() {
          _loading = false;
          _errorMessage = 'User not found. Check phone number.';
        });
        return;
      }

      await DbService.updateLastLogin(user.id);

      final session = UserSession(
        userId: user.id,
        displayName: user.displayName,
        phone: user.phone,
        isAdmin: user.isAdmin,
        token: 'token_${user.id}_${DateTime.now().millisecondsSinceEpoch}',
        profilePicBytes: user.profilePicBytes,
      );

      await SessionService.saveSession(session);

      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => DashboardScreen(session: session)),
      );
    } catch (e) {
      setState(() {
        _loading = false;
        _errorMessage = 'Connection error: ${e.toString()}';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    const primary = Color(0xFF00D4AA);
    const cardBg = Color(0xFF161B22);
    const textMuted = Color(0xFF8B949E);

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 28.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Logo / Icon — larger, glowing
                Center(
                  child: Container(
                    width: 110,
                    height: 110,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: primary.withOpacity(0.30),
                          blurRadius: 28,
                          spreadRadius: 4,
                        ),
                      ],
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(55),
                      child: Image.asset(
                        'assets/images/logo.png',
                        width: 110,
                        height: 110,
                        fit: BoxFit.cover,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 22),

                // Title
                const Text(
                  'KoS Crypto Alerts',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 26,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Real-Time NeonDB Price Sync & Alarms',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: textMuted, fontSize: 13),
                ),
                const SizedBox(height: 36),

                // Input Card
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: cardBg,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFF30363D)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const Text(
                        'Phone Number',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: textMuted,
                        ),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _phoneController,
                        keyboardType: TextInputType.phone,
                        style: const TextStyle(fontSize: 16),
                        decoration: InputDecoration(
                          // Properly styled hint — clearly faded, not pre-filled
                          hintText: '9898989898',
                          hintStyle: TextStyle(
                            color: textMuted.withOpacity(0.45),
                            fontSize: 16,
                            fontStyle: FontStyle.italic,
                            letterSpacing: 0.5,
                          ),
                          prefixIcon: const Icon(Icons.phone_android_rounded),
                          contentPadding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 14),
                        ),
                        onSubmitted: (v) => _handleLogin(v),
                      ),
                      if (_errorMessage != null) ...[
                        const SizedBox(height: 12),
                        Text(
                          _errorMessage!,
                          style: const TextStyle(
                            color: Color(0xFFFF6B6B),
                            fontSize: 12,
                          ),
                        ),
                      ],
                      const SizedBox(height: 18),
                      ElevatedButton(
                        onPressed: _loading
                            ? null
                            : () => _handleLogin(_phoneController.text),
                        child: _loading
                            ? const SizedBox(
                                width: 22,
                                height: 22,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2.5,
                                  valueColor:
                                      AlwaysStoppedAnimation(Colors.black),
                                ),
                              )
                            : const Text('Log In'),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 28),

                // Quick Login Buttons
                const Text(
                  'QUICK LOGIN',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: textMuted,
                    fontSize: 11,
                    letterSpacing: 1.2,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 13),
                          side: const BorderSide(color: Color(0xFF30363D)),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10)),
                        ),
                        icon: const Icon(Icons.admin_panel_settings_rounded,
                            size: 18, color: primary),
                        label: const Text('Admin',
                            style: TextStyle(color: Colors.white)),
                        onPressed: _loading
                            ? null
                            : () {
                                _phoneController.text = '9899654695';
                                _handleLogin('9899654695');
                              },
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 13),
                          side: const BorderSide(color: Color(0xFF30363D)),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10)),
                        ),
                        icon: const Icon(Icons.person_outline_rounded,
                            size: 18, color: Colors.blueAccent),
                        label: const Text('Mehboob',
                            style: TextStyle(color: Colors.white)),
                        onPressed: _loading
                            ? null
                            : () {
                                _phoneController.text = '9818011930';
                                _handleLogin('9818011930');
                              },
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
