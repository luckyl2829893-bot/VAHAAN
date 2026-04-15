import 'package:flutter/material.dart';
import 'core/theme.dart';
import 'core/router.dart';

void main() {
  runApp(const AequitasRoadGuard());
}

class AequitasRoadGuard extends StatelessWidget {
  const AequitasRoadGuard({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Aequitas RoadGuard',
      debugShowCheckedModeBanner: false,
      theme: ARGTheme.darkTheme,
      routerConfig: appRouter,
    );
  }
}
