import 'package:flutter/material.dart';
import '../core/theme.dart';

class DevPortal extends StatefulWidget {
  const DevPortal({super.key});

  @override
  State<DevPortal> createState() => _DevPortalState();
}

class _DevPortalState extends State<DevPortal> {
  // Development State Overrides
  bool forceLightMode = false;
  double sentinelHarmony = 99.4;
  int mockGHP = 925;
  int promotions = 12;
  int redCards = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SENTIENT SANDBOX [DEV]', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
        backgroundColor: Colors.black26,
      ),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          _buildSectionHeader("DESIGN PERSONALITY"),
          SwitchListTile(
            title: const Text("Force Punchy Design (Light)"),
            subtitle: const Text("Overrides system theme for testing visuals"),
            value: forceLightMode,
            onChanged: (val) => setState(() => forceLightMode = val),
            secondary: const Icon(Icons.wb_sunny_rounded, color: ARGTheme.meritGold),
          ),
          
          const Divider(height: 40),
          _buildSectionHeader("REPUTATION & MERIT ENGINE"),
          
          _buildSlider("Good Human Points (Citizen)", mockGHP.toDouble(), 0, 1000, (val) {
             setState(() => mockGHP = val.toInt());
          }),
          
          _buildSlider("Harmony Index (AI Sentience)", sentinelHarmony, 0, 100, (val) {
             setState(() => sentinelHarmony = val);
          }),

          const SizedBox(height: 20),
          
          _buildSectionHeader("OFFICER COMMAND"),
          Row(
            children: [
              Expanded(
                child: _buildDevButton("ADD PROMOTION", ARGTheme.meritGold, () {
                  setState(() => promotions++);
                }),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _buildDevButton("ISSUE RED CARD", ARGTheme.redCard, () {
                  setState(() => redCards++);
                }),
              ),
            ],
          ),
          
          const SizedBox(height: 40),
          ElevatedButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("APPLY & SYNC TO ENGINE"),
          ),
          
          const SizedBox(height: 20),
          const Center(
            child: Text("VERSION: 0.9.1-BETA | AEQUITAS STABLE", style: TextStyle(fontSize: 10, color: Colors.grey)),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Text(title, style: const TextStyle(fontWeight: FontWeight.bold, color: ARGTheme.harmonyTeal, fontSize: 12)),
    );
  }

  Widget _buildSlider(String label, double val, double min, double max, Function(double) onChanged) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label),
            Text(val.toStringAsFixed(1), style: const TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        Slider(
          value: val,
          min: min,
          max: max,
          activeColor: ARGTheme.primaryBlue,
          onChanged: onChanged,
        ),
      ],
    );
  }

  Widget _buildDevButton(String label, Color color, VoidCallback onTap) {
    return OutlinedButton(
      onPressed: onTap,
      style: OutlinedButton.styleFrom(
        foregroundColor: color,
        side: BorderSide(color: color),
      ),
      child: Text(label, style: const TextStyle(fontSize: 12)),
    );
  }
}
