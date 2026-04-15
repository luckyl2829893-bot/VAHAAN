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
  String? _detectedModel;
  double _baseFine = 500;
  double _wealthMultiplier = 1.0;
  bool _isScanning = false;

  void _simulateScan() async {
    setState(() => _isScanning = true);
    await Future.delayed(2.seconds);
    setState(() {
      _detectedPlate = "DL 8C AD 5566";
      _detectedModel = "Mercedes-Benz G-Class";
      _wealthMultiplier = 8.5; // High wealth multiplier for expensive car
      _isScanning = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ARGTheme.darkBg,
      appBar: AppBar(
        title: const Text('ENFORCEMENT HUB', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 2)),
        centerTitle: true,
        backgroundColor: Colors.transparent,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildScannerSection(),
            const SizedBox(height: 32),
            if (_detectedPlate == null) _buildPatrolIntelligence(),
            if (_detectedPlate != null) _buildChallanCalculator(),
          ],
        ),
      ),
    );
  }

  Widget _buildPatrolIntelligence() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('PATROL INTELLIGENCE', style: TextStyle(color: ARGTheme.primaryBlue, fontWeight: FontWeight.bold, fontSize: 12)),
        const SizedBox(height: 16),
        Container(
          height: 150,
          decoration: BoxDecoration(
            color: ARGTheme.surface,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: Colors.white.withOpacity(0.05)),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.map_rounded, color: Colors.white10, size: 50),
              const SizedBox(height: 8),
              const Text('LIVE VIOLATION HEATMAP', style: TextStyle(color: Colors.white60, fontSize: 12)),
              const Text('High Activity: Sector 45', style: TextStyle(color: Colors.redAccent, fontSize: 10, fontWeight: FontWeight.bold)),
            ],
          ),
        ),
        const SizedBox(height: 24),
        const Text('CRITICAL WANTED LIST', style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold, fontSize: 12)),
        const SizedBox(height: 12),
        _buildWantedItem("HR 26 DA 9900", "Hit & Run Suspect", Colors.redAccent),
        _buildWantedItem("DL 8C BA 1212", "Stolen Vehicle", Colors.orangeAccent),
      ],
    ).animate().fadeIn(delay: 400.ms);
  }

  Widget _buildWantedItem(String plate, String reason, Color color) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(color: Colors.white.withOpacity(0.03), borderRadius: BorderRadius.circular(16)),
      child: Row(
        children: [
          Icon(Icons.warning_rounded, color: color, size: 16),
          const SizedBox(width: 12),
          Text(plate, style: const TextStyle(fontWeight: FontWeight.bold)),
          const Spacer(),
          Text(reason, style: TextStyle(color: color.withOpacity(0.7), fontSize: 11)),
        ],
      ),
    );
  }

  Widget _buildScannerSection() {
    return Container(
      height: 250,
      decoration: BoxDecoration(
        color: Colors.black,
        borderRadius: BorderRadius.circular(32),
        border: Border.all(color: ARGTheme.primaryBlue.withOpacity(0.3)),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(30),
        child: Stack(
          fit: StackFit.expand,
          children: [
            _isScanning 
              ? const Center(child: CircularProgressIndicator(color: ARGTheme.primaryBlue))
              : Center(child: Icon(Icons.qr_code_scanner_rounded, color: Colors.white10, size: 80)),
            
            Positioned(
              bottom: 20,
              left: 40, right: 40,
              child: ElevatedButton.icon(
                onPressed: _isScanning ? null : _simulateScan,
                icon: const Icon(Icons.camera_alt_rounded),
                label: const Text('SCAN VEHICLE PLATE'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: ARGTheme.primaryBlue,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChallanCalculator() {
    double totalFine = _baseFine * _wealthMultiplier;
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('AI DETECTION RESULTS', style: TextStyle(color: ARGTheme.primaryBlue, fontWeight: FontWeight.bold, fontSize: 12)),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(color: ARGTheme.surface, borderRadius: BorderRadius.circular(24)),
          child: Column(
            children: [
              _buildResultRow("Plate Number", _detectedPlate!, Icons.badge_rounded),
              const Divider(color: Colors.white10, height: 32),
              _buildResultRow("Vehicle Model", _detectedModel!, Icons.directions_car_rounded, isEditable: true),
              const Divider(color: Colors.white10, height: 32),
              _buildResultRow("Wealth Multiplier", "x${_wealthMultiplier.toStringAsFixed(1)}", Icons.trending_up_rounded),
            ],
          ),
        ),
        const SizedBox(height: 32),
        const Text('EQUITY-BASED FINE CALCULATION', style: TextStyle(color: ARGTheme.successGreen, fontWeight: FontWeight.bold, fontSize: 12)),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [ARGTheme.successGreen.withOpacity(0.1), Colors.transparent]),
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: ARGTheme.successGreen.withOpacity(0.2)),
          ),
          child: Column(
            children: [
              _buildFineRow("Base Violation Fine", "₹${_baseFine.toInt()}"),
              const SizedBox(height: 12),
              _buildFineRow("Wealth Adjustment", "x${_wealthMultiplier.toStringAsFixed(1)}"),
              const Divider(color: Colors.white10, height: 24),
              _buildFineRow("TOTAL CHALLAN", "₹${totalFine.toInt()}", isTotal: true),
            ],
          ),
        ),
        const SizedBox(height: 32),
        ElevatedButton(
          onPressed: () {},
          style: ElevatedButton.styleFrom(
            backgroundColor: ARGTheme.successGreen,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 20),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          ),
          child: const Center(child: Text('ISSUE SMART CHALLAN', style: TextStyle(fontWeight: FontWeight.bold))),
        ),
      ],
    ).animate().fadeIn().slideY(begin: 0.1);
  }

  Widget _buildResultRow(String label, String value, IconData icon, {bool isEditable = false}) {
    return Row(
      children: [
        Icon(icon, color: Colors.white30, size: 20),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: const TextStyle(color: Colors.white30, fontSize: 11)),
              Text(value, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
            ],
          ),
        ),
        if (isEditable) const Icon(Icons.edit_note_rounded, color: ARGTheme.primaryBlue),
      ],
    );
  }

  Widget _buildFineRow(String label, String value, {bool isTotal = false}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: TextStyle(color: isTotal ? Colors.white : Colors.white60, fontWeight: isTotal ? FontWeight.bold : FontWeight.normal)),
        Text(value, style: TextStyle(color: isTotal ? ARGTheme.successGreen : Colors.white, fontSize: isTotal ? 24 : 16, fontWeight: FontWeight.bold)),
      ],
    );
  }
}
