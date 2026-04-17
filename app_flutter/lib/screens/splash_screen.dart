import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../core/theme.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _navigateToNext();
  }

  Future<void> _navigateToNext() async {
    await Future.delayed(const Duration(milliseconds: 2500));
    if (mounted) {
      context.go('/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        width: double.infinity,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              ARGTheme.darkBg,
              ARGTheme.darkBg.withBlue(60),
            ],
          ),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: ARGTheme.primaryBlue.withOpacity(0.1),
                border: Border.all(color: ARGTheme.primaryBlue.withOpacity(0.3), width: 2),
              ),
              child: const Icon(
                Icons.security_rounded,
                size: 64,
                color: ARGTheme.primaryBlue,
              ),
            )
            .animate()
            .scale(duration: 800.ms, curve: Curves.easeOutBack)
            .shimmer(delay: 1.seconds, duration: 2.seconds),
            
            const SizedBox(height: 24),
            
            Text(
              'VAHAAN',
              style: Theme.of(context).textTheme.displayLarge?.copyWith(
                letterSpacing: 4,
                color: Colors.white,
              ),
            )
            .animate()
            .fadeIn(delay: 400.ms)
            .slideY(begin: 0.2, end: 0),
            
            Text(
              'VAHAAN',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                letterSpacing: 8,
                color: ARGTheme.primaryBlue,
                fontWeight: FontWeight.w300,
              ),
            )
            .animate()
            .fadeIn(delay: 800.ms)
            .slideY(begin: 0.2, end: 0),
            
            const SizedBox(height: 60),
            
            const CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation<Color>(ARGTheme.primaryBlue),
            )
            .animate()
            .fadeIn(delay: 1200.ms),
          ],
        ),
      ),
    );
  }
}
