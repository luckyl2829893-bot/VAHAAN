import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../core/theme.dart';

class SentinelMind extends StatefulWidget {
  const SentinelMind({super.key});

  @override
  State<SentinelMind> createState() => _SentinelMindState();
}

class _SentinelMindState extends State<SentinelMind> {
  double _multiplierSensitivity = 1.0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ARGTheme.darkBg,
      appBar: AppBar(
        title: const Text('SENTINEL MIND', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 2)),
        centerTitle: true,
        backgroundColor: Colors.transparent,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSystemHealth(),
            const SizedBox(height: 32),
            _buildRetrainingQueue(),
            const SizedBox(height: 32),
            _buildEconomicConfig(),
            const SizedBox(height: 32),
            _buildCommunityTasking(),
          ],
        ),
      ),
    );
  }

  Widget _buildCommunityTasking() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('COMMUNITY ANNOTATION ENGINE', style: TextStyle(color: ARGTheme.successGreen, fontWeight: FontWeight.bold, fontSize: 12)),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(color: ARGTheme.surface, borderRadius: BorderRadius.circular(24)),
          child: Column(
            children: [
              const Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Active Bounty Tasks', style: TextStyle(color: Colors.white70)),
                  Text('42 Active Citizens', style: TextStyle(color: ARGTheme.primaryBlue, fontSize: 10)),
                ],
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: () {},
                icon: const Icon(Icons.shuffle_rounded),
                label: const Text('PUSH NEW IMAGE BATCH'),
                style: ElevatedButton.styleFrom(backgroundColor: ARGTheme.primaryBlue.withOpacity(0.1), foregroundColor: ARGTheme.primaryBlue),
              ),
            ],
          ),
        ),
      ],
    ).animate().fadeIn(delay: 1.seconds);
  }

  Widget _buildSystemHealth() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: ARGTheme.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('System Cognitive Health', style: TextStyle(fontWeight: FontWeight.bold)),
              const Text('99.9%', style: TextStyle(color: ARGTheme.successGreen, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 16),
          LinearProgressIndicator(value: 0.999, backgroundColor: Colors.white10, color: ARGTheme.successGreen, borderRadius: BorderRadius.circular(10), minHeight: 8),
        ],
      ),
    ).animate().fadeIn();
  }

  Widget _buildRetrainingQueue() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('AI RETRAINING QUEUE (CLEANING)', style: TextStyle(color: ARGTheme.primaryBlue, fontWeight: FontWeight.bold, fontSize: 12)),
        const SizedBox(height: 16),
        SizedBox(
          height: 120,
          child: ListView(
            scrollDirection: Axis.horizontal,
            children: [
              _buildCleanableItem("Car? Low Conf", "DL 3C AB 1234"),
              _buildCleanableItem("Brand? 65%", "UP 16 AX 9988"),
              _buildCleanableItem("Night Scan", "HR 26 DA 1122"),
            ],
          ),
        ),
      ],
    ).animate().fadeIn(delay: 400.ms);
  }

  Widget _buildCleanableItem(String issue, String plate) {
    return Container(
      width: 150,
      margin: const EdgeInsets.only(right: 16),
      decoration: BoxDecoration(color: Colors.white.withOpacity(0.05), borderRadius: BorderRadius.circular(20), border: Border.all(color: Colors.white10)),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.psychology_rounded, color: Colors.white30),
          const SizedBox(height: 8),
          Text(issue, style: const TextStyle(fontSize: 10, color: Colors.white70)),
          Text(plate, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  Widget _buildEconomicConfig() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('WEALTH MULTIPLIER LOGIC', style: TextStyle(color: ARGTheme.accentAmber, fontWeight: FontWeight.bold, fontSize: 12)),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(color: ARGTheme.surface, borderRadius: BorderRadius.circular(24)),
          child: Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Equity Sensitivity', style: TextStyle(color: Colors.white70)),
                  Text('${_multiplierSensitivity.toStringAsFixed(1)}x', style: const TextStyle(color: ARGTheme.accentAmber, fontWeight: FontWeight.bold)),
                ],
              ),
              Slider(
                value: _multiplierSensitivity,
                min: 0.5,
                max: 5.0,
                activeColor: ARGTheme.accentAmber,
                onChanged: (val) => setState(() => _multiplierSensitivity = val),
              ),
              const Text('higher sensitivity increases fine disparity between luxury and economy vehicles.', style: TextStyle(color: Colors.white24, fontSize: 10), textAlign: TextAlign.center),
            ],
          ),
        ),
      ],
    ).animate().fadeIn(delay: 800.ms);
  }
}
