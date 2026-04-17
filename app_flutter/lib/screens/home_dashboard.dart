import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../core/theme.dart';
import '../main.dart'; // To access themeNotifier

class HomeDashboard extends StatelessWidget {
  const HomeDashboard({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: CustomScrollView(
        slivers: [
          _buildAppBar(context),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                   _buildHeader(context),
                  const SizedBox(height: 40),
                  
                  _buildRoleCard(
                    context,
                    title: 'Citizen Portal', // Corrected name
                    subtitle: 'Good Human Points & Rewards',
                    icon: Icons.person_pin_circle_rounded,
                    color: ARGTheme.ghpGreen,
                    onTap: () => context.push('/citizen'), 
                  ).animate().fadeIn(delay: 400.ms).slideX(begin: 0.1),
                  
                  const SizedBox(height: 20),
                  
                  _buildRoleCard(
                    context,
                    title: 'Enforcement Hub',
                    subtitle: 'Officer Merit & Red Cards',
                    icon: Icons.local_police_rounded,
                    color: ARGTheme.electricBlue,
                    onTap: () => context.push('/officer'),
                  ).animate().fadeIn(delay: 600.ms).slideX(begin: 0.1),
                  
                  const SizedBox(height: 20),
                  
                  _buildRoleCard(
                    context,
                    title: 'Sentinel Mind',
                    subtitle: 'AI Sentience & Grading Workspace',
                    icon: Icons.auto_awesome_rounded,
                    color: ARGTheme.harmonyTeal,
                    onTap: () => context.push('/sentinel'),
                  ).animate().fadeIn(delay: 800.ms).slideX(begin: 0.1),
                ],
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
            FloatingActionButton(
                heroTag: 'themeToggle',
                mini: true,
                onPressed: () {
                    themeNotifier.value = themeNotifier.value == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
                },
                backgroundColor: ARGTheme.meritGold,
                child: Icon(
                    themeNotifier.value == ThemeMode.dark ? Icons.wb_sunny_rounded : Icons.nightlight_round,
                    color: Colors.black,
                ),
            ).animate().scale(delay: 1000.ms),
            const SizedBox(height: 10),
            FloatingActionButton.extended(
                heroTag: 'report',
                onPressed: () => context.push('/report'),
                icon: const Icon(Icons.add_location_alt_rounded),
                label: const Text('HARMONY REPORT'),
                backgroundColor: ARGTheme.electricBlue,
            ).animate().scale(delay: 1200.ms, curve: Curves.easeOutBack),
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
      return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
              Text(
                'HQ Operations',
                style: Theme.of(context).textTheme.displayLarge,
              ).animate().fadeIn().slideY(begin: 0.2),
              const Text(
                'Manage real-time traffic equity and social merit.',
                style: TextStyle(color: Colors.grey, fontSize: 16),
              ).animate().fadeIn(delay: 200.ms),
          ]
      );
  }

  Widget _buildAppBar(BuildContext context) {
    return SliverAppBar(
      expandedHeight: 80,
      backgroundColor: Colors.transparent,
      elevation: 0,
      flexibleSpace: FlexibleSpaceBar(
        title: GestureDetector(
          onLongPress: () => context.push('/dev'),
          child: Text('VAHAAN | HQ', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontSize: 14, letterSpacing: 3)),
        ),
        centerTitle: true,
      ),
      actions: [
        IconButton(
          onPressed: () => context.push('/profile'),
          icon: Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(color: ARGTheme.electricBlue.withOpacity(0.1), shape: BoxShape.circle),
            child: const Icon(Icons.security_rounded, color: ARGTheme.electricBlue),
          ),
        ),
        const SizedBox(width: 16),
      ],
    );
  }

  Widget _buildRoleCard(BuildContext context, {
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    final bool isDark = Theme.of(context).brightness == Brightness.dark;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: Theme.of(context).cardTheme.color,
          borderRadius: BorderRadius.circular(32),
          border: Border.all(color: color.withOpacity(isDark ? 0.1 : 0.3), width: 2),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(20)),
              child: Icon(icon, color: color, size: 32),
            ),
            const SizedBox(width: 20),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Text(subtitle, style: TextStyle(color: Colors.grey[600], fontSize: 13)),
                ],
              ),
            ),
            Icon(Icons.arrow_forward_ios_rounded, color: color.withOpacity(0.3), size: 16),
          ],
        ),
      ),
    );
  }
}
