import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../core/theme.dart';

class EnforcementHub extends StatefulWidget {
  const EnforcementHub({super.key});

  @override
  State<EnforcementHub> createState() => _EnforcementHubState();
}

class _EnforcementHubState extends State<EnforcementHub> {
  String? _detectedPlate;
  bool _isScanning = false;

  // Mock Performance Data
  int flaggedCount = 142;
  int challansIssued = 89;
  double promoProbability = 0.72; // 72%
  
  // Status: 0=Red, 1=Orange, 2=Yellow, 3=Green
  int integrityStatus = 2; 

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        title: Text('ENFORCEMENT COMMAND', style: Theme.of(context).textTheme.titleLarge),
        centerTitle: true,
        backgroundColor: Colors.transparent,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // --- PERFORMANCE HUB (TRENDS) ---
            _buildPerformanceGrid(),
            const SizedBox(height: 32),
            
            // --- PROMOTION VELOCITY ---
            _buildPromotionTracker(),
            const SizedBox(height: 32),
            
            // --- INTEGRITY STATUS & DIRECTIVES ---
            _buildIntegrityGauge(),
            if (integrityStatus < 3) _buildDirectives(),
            
            const SizedBox(height: 32),
            _buildScannerSection(),
          ],
        ),
      ),
    );
  }

  Widget _buildPerformanceGrid() {
    return Row(
      children: [
        Expanded(child: _buildMetricCard("Flagged Vehicles", flaggedCount.toString(), "+12% Weekly", Icons.radar_rounded)),
        const SizedBox(width: 16),
        Expanded(child: _buildMetricCard("Challans Issued", challansIssued.toString(), "+5% Monthly", Icons.receipt_long_rounded)),
      ],
    ).animate().fadeIn();
  }

  Widget _buildMetricCard(String label, String val, String trend, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: Theme.of(context).cardTheme.color, borderRadius: BorderRadius.circular(24), border: Border.all(color: Colors.white.withOpacity(0.05))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
            Icon(icon, color: ARGTheme.primaryBlue, size: 20),
            const SizedBox(height: 12),
            Text(val, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
            Text(label, style: const TextStyle(fontSize: 10, color: Colors.grey)),
            const SizedBox(height: 8),
            Text(trend, style: const TextStyle(color: ARGTheme.ghpGreen, fontSize: 10, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  Widget _buildPromotionTracker() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(color: Theme.of(context).cardTheme.color, borderRadius: BorderRadius.circular(28), border: Border.all(color: ARGTheme.meritGold.withOpacity(0.3))),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
                const Text("PROMOTION PROBABILITY", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 1)),
                Text("${(promoProbability * 100).toInt()}%", style: const TextStyle(color: ARGTheme.meritGold, fontWeight: FontWeight.w900, fontSize: 18)),
            ],
          ),
          const SizedBox(height: 16),
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: LinearProgressIndicator(value: promoProbability, minHeight: 10, backgroundColor: Colors.white10, valueColor: const AlwaysStoppedAnimation(ARGTheme.meritGold)),
          ),
          const SizedBox(height: 12),
          const Text("High probability for next Rank. Keep patrol volume steady.", style: TextStyle(fontSize: 10, color: Colors.grey)),
        ],
      ),
    ).animate().fadeIn(delay: 200.ms);
  }

  Widget _buildIntegrityGauge() {
    final List<Color> colors = [ARGTheme.redCard, Colors.orangeAccent, Colors.amber, ARGTheme.ghpGreen];
    final List<String> statusNames = ["DANGER", "WARNING", "CAUTION", "ELITE"];
    
    return Container(
        margin: const EdgeInsets.only(bottom: 16),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
            color: colors[integrityStatus].withOpacity(0.05),
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: colors[integrityStatus].withOpacity(0.2)),
        ),
        child: Row(
            children: [
                Icon(Icons.shield_rounded, color: colors[integrityStatus]),
                const SizedBox(width: 16),
                Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                        const Text("INTEGRITY STATUS", style: TextStyle(fontSize: 10, color: Colors.grey)),
                        Text(statusNames[integrityStatus], style: TextStyle(color: colors[integrityStatus], fontWeight: FontWeight.w900, fontSize: 18)),
                    ],
                ),
            ],
        ),
    );
  }

  Widget _buildDirectives() {
      return Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: Colors.white.withOpacity(0.03), borderRadius: BorderRadius.circular(20)),
          child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                  Text("REHABILITATION DIRECTIVE", style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold, fontSize: 10)),
                  SizedBox(height: 8),
                  Text("• Your integrity is below Elite (Green).", style: TextStyle(fontSize: 12)),
                  Text("• Resolve 5 pending community reports to restore health.", style: TextStyle(fontSize: 12, color: Colors.grey)),
              ],
          ),
      ).animate().shake();
  }

  Widget _buildScannerSection() {
    return Container(
      height: 120,
      decoration: BoxDecoration(color: Colors.black, borderRadius: BorderRadius.circular(24), border: Border.all(color: ARGTheme.electricBlue.withOpacity(0.3))),
      child: Center(
        child: ElevatedButton.icon(onPressed: () {}, icon: const Icon(Icons.qr_code_scanner_rounded), label: const Text("LAUNCH PLATE SCANNER")),
      ),
    );
  }
}
