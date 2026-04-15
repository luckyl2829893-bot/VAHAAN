import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../core/theme.dart';

class HomeDashboard extends StatelessWidget {
  const HomeDashboard({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ARGTheme.darkBg,
      body: CustomScrollView(
        slivers: [
          _buildAppBar(context),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Operations Center',
                    style: TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold),
                  ).animate().fadeIn().slideY(begin: 0.2),
                  const Text(
                    'Select a sector to manage current traffic equity.',
                    style: TextStyle(color: Colors.white60, fontSize: 16),
                  ).animate().fadeIn(delay: 200.ms),
                  const SizedBox(height: 40),
                  
                  _buildRoleCard(
                    context,
                    title: 'Citizen Portal',
                    subtitle: 'Reports, Safety Scores & Rewards',
                    icon: Icons.person_pin_circle_rounded,
                    color: ARGTheme.successGreen,
                    onTap: () => context.push('/citizen'), 
                  ).animate().fadeIn(delay: 400.ms).slideX(begin: 0.1),
                  
                  const SizedBox(height: 20),
                  
                  _buildRoleCard(
                    context,
                    title: 'Enforcement Hub',
                    subtitle: 'Police Duty & Plate Recognition',
                    icon: Icons.local_police_rounded,
                    color: ARGTheme.primaryBlue,
                    onTap: () => context.push('/officer'),
                  ).animate().fadeIn(delay: 600.ms).slideX(begin: 0.1),
                  
                  const SizedBox(height: 20),
                  
                  _buildRoleCard(
                    context,
                    title: 'Sentinel Mind',
                    subtitle: 'Admin Control & System Overlord',
                    icon: Icons.visibility_rounded,
                    color: ARGTheme.accentAmber,
                    onTap: () => context.push('/sentinel'),
                  ).animate().fadeIn(delay: 800.ms).slideX(begin: 0.1),
                ],
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/report'),
        icon: const Icon(Icons.add_a_photo_rounded),
        label: const Text('QUICK REPORT'),
        backgroundColor: ARGTheme.primaryBlue,
      ).animate().scale(delay: 1200.ms, curve: Curves.easeOutBack),
    );
  }

  Widget _buildAppBar(BuildContext context) {
    return SliverAppBar(
      expandedHeight: 100,
      backgroundColor: ARGTheme.darkBg,
      flexibleSpace: const FlexibleSpaceBar(
        title: Text('ROADGUARD | HQ', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, letterSpacing: 2)),
        centerTitle: true,
      ),
      actions: [
        IconButton(
          onPressed: () => context.push('/profile'),
          icon: Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(color: ARGTheme.primaryBlue.withOpacity(0.1), shape: BoxShape.circle),
            child: const Icon(Icons.person_outline_rounded, color: ARGTheme.primaryBlue),
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
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: ARGTheme.surface,
          borderRadius: BorderRadius.circular(32),
          border: Border.all(color: Colors.white.withOpacity(0.05)),
          boxShadow: [
            BoxShadow(color: color.withOpacity(0.05), blurRadius: 20, spreadRadius: 2),
          ],
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
                  Text(title, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Text(subtitle, style: const TextStyle(color: Colors.white54, fontSize: 13)),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios_rounded, color: Colors.white24, size: 16),
          ],
        ),
      ),
    );
  }
}
