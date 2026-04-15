import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:go_router/go_router.dart';
import '../core/theme.dart';

class CitizenPortal extends StatelessWidget {
  const CitizenPortal({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ARGTheme.darkBg,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text('CITIZEN PORTAL', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 2)),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSafetyScore(context),
            const SizedBox(height: 32),
            _buildQuickActions(context),
            const SizedBox(height: 32),
            _buildRecentActivity(context),
          ],
        ),
      ),
    );
  }

  Widget _buildSafetyScore(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [ARGTheme.primaryBlue.withOpacity(0.2), Colors.transparent],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(32),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Row(
        children: [
          SizedBox(
            height: 100,
            width: 100,
            child: PieChart(
              PieChartData(
                sectionsSpace: 0,
                centerSpaceRadius: 35,
                sections: [
                  PieChartSectionData(color: ARGTheme.successGreen, value: 85, radius: 8, showTitle: false),
                  PieChartSectionData(color: Colors.white10, value: 15, radius: 8, showTitle: false),
                ],
              ),
            ),
          ),
          const SizedBox(width: 24),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Safety Score', style: TextStyle(color: Colors.white60, fontSize: 14)),
                const Text('850 / 1000', style: TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(color: ARGTheme.successGreen.withOpacity(0.2), borderRadius: BorderRadius.circular(12)),
                  child: const Text('EXCELLENT', style: TextStyle(color: ARGTheme.successGreen, fontSize: 10, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
          ),
        ],
      ),
    ).animate().fadeIn().slideX(begin: 0.1);
  }

  Widget _buildQuickActions(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Quick Access', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, letterSpacing: 1, color: Colors.white)),
        const SizedBox(height: 16),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          mainAxisSpacing: 16,
          crossAxisSpacing: 16,
          childAspectRatio: 1.5,
          children: [
            _QuickActionCard(
              title: 'Vehicle\nVitals',
              icon: Icons.electric_car_rounded,
              color: ARGTheme.primaryBlue,
              onTap: () {}, // Future route
            ),
            _QuickActionCard(
              title: 'Doc\nVault',
              icon: Icons.folder_rounded,
              color: ARGTheme.accentAmber,
              onTap: () => context.push('/vault'),
            ),
            _QuickActionCard(
              title: 'Earn\nBounties',
              icon: Icons.monetization_on_rounded,
              color: ARGTheme.successGreen,
              onTap: () => context.push('/bounties'),
            ),
          ],
        ),
      ],
    ).animate().fadeIn(delay: 400.ms);
  }

  Widget _buildRecentActivity(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text('Recent Activity', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, letterSpacing: 1, color: Colors.white)),
            TextButton(onPressed: () {}, child: const Text('View All', style: TextStyle(color: ARGTheme.primaryBlue))),
          ],
        ),
        const SizedBox(height: 12),
        const _ActivityItem(
          title: 'Speeding Fine Paid',
          subtitle: 'HR26DQ1234 • -₹1,250',
          icon: Icons.payment_rounded,
          color: ARGTheme.successGreen,
        ),
        const _ActivityItem(
          title: 'Bounty Credited',
          subtitle: 'Violation #8212 • +₹250',
          icon: Icons.currency_rupee_rounded,
          color: ARGTheme.primaryBlue,
        ),
        const _ActivityItem(
          title: 'Pothole Reported',
          subtitle: 'Sector 44, Gurgaon',
          icon: Icons.warning_amber_rounded,
          color: ARGTheme.accentAmber,
        ),
      ],
    ).animate().fadeIn(delay: 600.ms);
  }
}

class _QuickActionCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _QuickActionCard({required this.title, required this.icon, required this.color, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: ARGTheme.surface,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: Colors.white.withOpacity(0.05)),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 32),
            const SizedBox(height: 8),
            Text(title, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 14)),
          ],
        ),
      ),
    );
  }
}

class _ActivityItem extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;

  const _ActivityItem({required this.title, required this.subtitle, required this.icon, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ARGTheme.surface.withOpacity(0.5),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: color.withOpacity(0.1), shape: BoxShape.circle),
            child: Icon(icon, color: color, size: 20),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                Text(subtitle, style: const TextStyle(color: Colors.white54, fontSize: 13)),
              ],
            ),
          ),
          const Icon(Icons.arrow_forward_ios_rounded, color: Colors.white10, size: 14),
        ],
      ),
    );
  }
}
