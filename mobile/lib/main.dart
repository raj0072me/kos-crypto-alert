// lib/main.dart
// ─────────────────────────────────────────────────────────────────────────────
// KoS Crypto Alerts — Entry Point
// ─────────────────────────────────────────────────────────────────────────────

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:workmanager/workmanager.dart';

import 'services/alarm_service.dart';
import 'services/background_task.dart';
import 'screens/login_screen.dart';
import 'screens/dashboard_screen.dart';
import 'services/session_service.dart';

// Called by WorkManager in an isolate (background task)
@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    await BackgroundTask.run(task, inputData);
    return Future.value(true);
  });
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Force portrait mode
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Dark status bar icons
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
  ));

  // Initialize alarm notification channel
  await AlarmService.initialize();

  // Initialize WorkManager for background price monitoring
  await Workmanager().initialize(callbackDispatcher, isInDebugMode: false);

  runApp(const KosCryptoApp());
}

class KosCryptoApp extends StatelessWidget {
  const KosCryptoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'KoS Crypto Alerts',
      debugShowCheckedModeBanner: false,
      theme: _buildDarkTheme(),
      home: const AppEntry(),
    );
  }

  ThemeData _buildDarkTheme() {
    const primary = Color(0xFF00D4AA);      // Teal accent
    const surface = Color(0xFF0D1117);     // Near-black background
    const card    = Color(0xFF161B22);     // Card background
    const border  = Color(0xFF30363D);     // Subtle borders

    return ThemeData(
      brightness: Brightness.dark,
      useMaterial3: true,
      scaffoldBackgroundColor: surface,
      colorScheme: const ColorScheme.dark(
        primary:    primary,
        secondary:  Color(0xFFFF6B6B),
        surface:    surface,
        onPrimary:  Colors.black,
        onSurface:  Color(0xFFE6EDF3),
      ),
      cardTheme: CardTheme(
        color: card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: border, width: 1),
        ),
      ),
      fontFamily: 'Inter',
      textTheme: const TextTheme(
        displayLarge: TextStyle(color: Color(0xFFE6EDF3), fontWeight: FontWeight.bold),
        bodyLarge:    TextStyle(color: Color(0xFFC9D1D9)),
        bodyMedium:   TextStyle(color: Color(0xFF8B949E)),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: card,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: primary, width: 2),
        ),
        labelStyle: const TextStyle(color: Color(0xFF8B949E)),
        prefixIconColor: const Color(0xFF8B949E),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.black,
          padding: const EdgeInsets.symmetric(vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: surface,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: Color(0xFFE6EDF3),
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
        iconTheme: IconThemeData(color: Color(0xFFC9D1D9)),
      ),
    );
  }
}

/// Decide entry screen based on saved session
class AppEntry extends StatefulWidget {
  const AppEntry({super.key});

  @override
  State<AppEntry> createState() => _AppEntryState();
}

class _AppEntryState extends State<AppEntry> {
  @override
  void initState() {
    super.initState();
    _checkSession();
  }

  Future<void> _checkSession() async {
    final session = await SessionService.loadSession();
    if (!mounted) return;
    if (session != null) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => DashboardScreen(session: session)),
      );
    } else {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: CircularProgressIndicator(),
      ),
    );
  }
}
