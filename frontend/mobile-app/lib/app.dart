import 'package:flutter/material.dart';

import 'features/auth/login_screen.dart';
import 'features/shell/main_shell.dart';

class SenarioSparkApp extends StatefulWidget {
  const SenarioSparkApp({super.key, this.enablePlayback = true});

  final bool enablePlayback;

  @override
  State<SenarioSparkApp> createState() => _SenarioSparkAppState();
}

class _SenarioSparkAppState extends State<SenarioSparkApp> {
  bool _authenticated = false;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'SenarioSpark',
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.light,
        scaffoldBackgroundColor: const Color(0xFFFAFAF7),
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF111111),
          brightness: Brightness.light,
        ),
        textTheme: ThemeData.light().textTheme.apply(
          bodyColor: const Color(0xFF111111),
          displayColor: const Color(0xFF111111),
        ),
      ),
      home: AnimatedSwitcher(
        duration: const Duration(milliseconds: 240),
        child: _authenticated
            ? MainShell(enablePlayback: widget.enablePlayback)
            : LoginScreen(onLogin: () => setState(() => _authenticated = true)),
      ),
    );
  }
}
