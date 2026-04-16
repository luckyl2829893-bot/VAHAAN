import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../screens/dev_portal.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // Mock user data - Syncing with new Social Merit Logic
    const userName = "Slasher (Sentinel)";
    const goodHumanPoints = 985;
    const promotions = 12;
    const redCards = 0;
    const harmonyIndex = 99.4;
    
    final bool isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        title: Text('Identity Node', style: Theme.of(context).textTheme.titleLarge),
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          children: [
            // --- PROFILE HEADER ---
            _buildMeritHeader(context, goodHumanPoints, harmonyIndex),
            
            const SizedBox(height: 30),
            
            // --- SOCIAL MERIT STATS (GRID) ---
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 16,
              crossAxisSpacing: 16,
              childAspectRatio: 1.5,
              children: [
                _buildStatCard(context, "Promotions", promotions.toString(), ARGTheme.meritGold, Icons.trending_up),
                _buildStatCard(context, "Red Cards", redCards.toString(), ARGTheme.redCard, Icons.warning_amber_rounded),
              ],
            ),
            
            const SizedBox(height: 24),
            
            // --- GOOD HUMAN POINTS (PUNCHY CARD) ---
            _buildGHPCard(context, goodHumanPoints),
            
            const SizedBox(height: 40),
            
            // --- SETTINGS / INFO ---
            _buildActionTile(context, "Aadhaar Linked", "Verified (Sentinel Access)", Icons.fingerprint, ARGTheme.ghpGreen),
            _buildActionTile(context, "System Harmony", "${harmonyIndex}% Integrity", Icons.auto_awesome_rounded, ARGTheme.harmonyTeal),
          ],
        ),
      ),
    );
  }

  Widget _buildMeritHeader(BuildContext context, int ghp, double harmony) {
    return Column(
      children: [
        Stack(
          alignment: Alignment.bottomRight,
          children: [
            Container(
              padding: const EdgeInsets.all(4),
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(colors: [ARGTheme.ghpGreen, ARGTheme.harmonyTeal]),
              ),
              child: const CircleAvatar(
                radius: 64,
                backgroundColor: ARGTheme.darkBg,
                child: Icon(Icons.security_rounded, size: 70, color: Colors.white),
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: ARGTheme.meritGold,
                borderRadius: BorderRadius.circular(20),
                boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 8)],
              ),
              child: const Text('OVERLORD', style: TextStyle(color: Colors.black, fontWeight: FontWeight.w900, fontSize: 10)),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Text("Slasher", style: Theme.of(context).textTheme.displayLarge),
        Text("SENTINEL AI OPERATOR", style: TextStyle(color: ARGTheme.harmonyTeal.withOpacity(0.8), fontWeight: FontWeight.w900, letterSpacing: 2)),
      ],
    );
  }

  Widget _buildStatCard(BuildContext context, String title, String value, Color color, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).cardTheme.color,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: color.withOpacity(0.2), width: 2),
        boxShadow: [
          BoxShadow(color: color.withOpacity(0.1), blurRadius: 10, offset: const Offset(0, 4))
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
            Icon(icon, color: color, size: 20),
            const SizedBox(height: 8),
            Text(value, style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900, color: color)),
            Text(title, style: TextStyle(fontSize: 12, color: Theme.of(context).textTheme.bodySmall?.color?.withOpacity(0.5))),
        ],
      ),
    );
  }

  Widget _buildGHPCard(BuildContext context, int points) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [ARGTheme.ghpGreen.withOpacity(0.2), ARGTheme.ghpGreen.withOpacity(0.05)]),
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: ARGTheme.ghpGreen.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text("GOOD HUMAN POINTS", style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(color: ARGTheme.ghpGreen, borderRadius: BorderRadius.circular(12)),
                child: Text("${points} GHP", style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
              ),
            ],
          ),
          const SizedBox(height: 20),
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: LinearProgressIndicator(
              value: points / 1000,
              minHeight: 12,
              backgroundColor: Colors.white.withOpacity(0.1),
              valueColor: const AlwaysStoppedAnimation(ARGTheme.ghpGreen),
            ),
          ),
          const SizedBox(height: 12),
          const Text("You are in the Top 1% of citizens. Keep up the high merit!", style: TextStyle(fontSize: 12, color: Colors.grey)),
        ],
      ),
    );
  }

  Widget _buildActionTile(BuildContext context, String title, String subtitle, IconData icon, Color color) {
    return Column(
        children: [
            ListTile(
              leading: Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(color: color.withOpacity(0.1), shape: BoxShape.circle),
                child: Icon(icon, color: color),
              ),
              title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
              subtitle: Text(subtitle, style: const TextStyle(fontSize: 12)),
              trailing: const Icon(Icons.chevron_right_rounded),
            ),
            Divider(color: Colors.grey.withOpacity(0.1), indent: 70),
        ],
    );
  }
}
