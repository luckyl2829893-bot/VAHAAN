import 'package:flutter/material.dart';
import 'core/theme.dart';
import 'core/router.dart';

// Global Notifier for Manual Theme Toggling (Dev Phase)
final ValueNotifier<ThemeMode> themeNotifier = ValueNotifier(ThemeMode.dark);

void main() {
  runApp(const AequitasRoadGuard());
}

class AequitasRoadGuard extends StatelessWidget {
  const AequitasRoadGuard({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: themeNotifier,
      builder: (_, ThemeMode currentMode, __) {
        return MaterialApp.router(
          title: 'Aequitas RoadGuard',
          debugShowCheckedModeBanner: false,
          theme: ARGTheme.lightTheme,
          darkTheme: ARGTheme.darkTheme,
          themeMode: currentMode,
          routerConfig: appRouter,
        );
      },
    );
  }
}
