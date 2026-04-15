import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../core/theme.dart';

class RoleSelectionScreen extends StatelessWidget {
  const RoleSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 40),
              Text(
                'Verify Identity',
                style: Theme.of(context).textTheme.displayLarge,
              ).animate().fadeIn().slideX(begin: -0.2),
              const SizedBox(height: 8),
              Text(
                'Choose your role in the Aequitas ecosystem.',
                style: Theme.of(context).textTheme.bodyLarge,
              ).animate().fadeIn(delay: 200.ms).slideX(begin: -0.2),
              const SizedBox(height: 48),
              
              Expanded(
                child: ListView(
                  children: [
                    _RoleCard(
                      title: 'CITIZEN',
                      subtitle: 'The Eyes: Report violations & earn bounties.',
                      icon: Icons.remove_red_eye_rounded,
                      color: ARGTheme.primaryBlue,
                      onTap: () => context.go('/dashboard'),
                    ).animate().fadeIn(delay: 400.ms).slideY(begin: 0.2),
                    
                    const SizedBox(height: 20),
                    
                    _RoleCard(
                      title: 'SCOUT',
                      subtitle: 'The Verifiers: Help AI identify unknown vehicles.',
                      icon: Icons.shield_rounded,
                      color: ARGTheme.successGreen,
                      onTap: () => context.go('/dashboard'),
                    ).animate().fadeIn(delay: 600.ms).slideY(begin: 0.2),
                    
                    const SizedBox(height: 20),
                    
                    _RoleCard(
                      title: 'SENTINEL',
                      subtitle: 'The Admin: System overrides & contractor audits.',
                      icon: Icons.admin_panel_settings_rounded,
                      color: ARGTheme.accentAmber,
                      onTap: () => context.go('/dashboard'),
                    ).animate().fadeIn(delay: 800.ms).slideY(begin: 0.2),
                  ],
                ),
              ),
              
              const SizedBox(height: 20),
              Center(
                child: Text(
                  'Powered by ARG Cloud Intelligence',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.white24),
                ),
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }
}

class _RoleCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _RoleCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: color.withOpacity(0.05),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: color.withOpacity(0.2), width: 1.5),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: color, size: 32),
            ),
            const SizedBox(width: 20),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: color,
                      letterSpacing: 1.2,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: const TextStyle(
                      fontSize: 14,
                      color: Colors.white60,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded, color: Colors.white24),
          ],
        ),
      ),
    );
  }
}
