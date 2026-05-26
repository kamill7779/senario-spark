import 'package:flutter/material.dart';

import '../home/home_screen.dart';
import '../player/player_screen.dart';
import '../profile/profile_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key, this.enablePlayback = true});

  final bool enablePlayback;

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    final screens = [
      const HomeScreen(),
      PlayerScreen(enablePlayback: widget.enablePlayback),
      const ProfileScreen(),
    ];

    return Scaffold(
      body: SafeArea(child: screens[_selectedIndex]),
      bottomNavigationBar: NavigationBarTheme(
        data: NavigationBarThemeData(
          backgroundColor: Colors.white,
          indicatorColor: const Color(0xFF111111),
          labelTextStyle: WidgetStateProperty.resolveWith((states) {
            final selected = states.contains(WidgetState.selected);
            return TextStyle(
              color: selected
                  ? const Color(0xFF111111)
                  : const Color(0xFF777777),
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
            );
          }),
          iconTheme: WidgetStateProperty.resolveWith((states) {
            final selected = states.contains(WidgetState.selected);
            return IconThemeData(
              color: selected ? Colors.white : const Color(0xFF777777),
            );
          }),
        ),
        child: NavigationBar(
          selectedIndex: _selectedIndex,
          onDestinationSelected: (index) {
            setState(() => _selectedIndex = index);
          },
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.grid_view_rounded),
              label: '首页',
            ),
            NavigationDestination(
              icon: Icon(Icons.play_arrow_rounded),
              label: '播放',
            ),
            NavigationDestination(
              icon: Icon(Icons.person_outline_rounded),
              label: '我的',
            ),
          ],
        ),
      ),
    );
  }
}
