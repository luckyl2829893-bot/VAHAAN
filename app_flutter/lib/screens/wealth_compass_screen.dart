import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../core/theme.dart';
import '../core/api_service.dart';
import '../models/vehicle.dart';

class WealthCompassScreen extends StatefulWidget {
  const WealthCompassScreen({super.key});

  @override
  State<WealthCompassScreen> createState() => _WealthCompassScreenState();
}

class _WealthCompassScreenState extends State<WealthCompassScreen> {
  final TextEditingController _controller = TextEditingController();
  Vehicle? _vehicle;
  bool _loading = false;

  void _search() async {
    if (_controller.text.isEmpty) return;
    
    setState(() => _loading = true);
    final result = await APIService.lookupPlate(_controller.text.toUpperCase());
    setState(() {
      _vehicle = result;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Wealth Compass'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            _buildSearchBox(),
            const SizedBox(height: 32),
            if (_loading)
              const CircularProgressIndicator()
            else if (_vehicle != null)
              _buildVehicleCard()
            else
              _buildEmptyState(),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchBox() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      decoration: BoxDecoration(
        color: ARGTheme.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
      ),
      child: TextField(
        controller: _controller,
        textCapitalization: TextCapitalization.characters,
        decoration: InputDecoration(
          hintText: 'ENTER LICENSE PLATE',
          hintStyle: const TextStyle(color: Colors.white24, letterSpacing: 2),
          border: InputBorder.none,
          suffixIcon: IconButton(
            icon: const Icon(Icons.search_rounded, color: ARGTheme.primaryBlue),
            onPressed: _search,
          ),
        ),
        onSubmitted: (_) => _search(),
      ),
    );
  }

  Widget _buildVehicleCard() {
    final v = _vehicle!;
    return Column(
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: ARGTheme.primaryBlue.withOpacity(0.05),
            borderRadius: BorderRadius.circular(32),
            border: Border.all(color: ARGTheme.primaryBlue.withOpacity(0.2)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(v.plateNumber, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, letterSpacing: 2)),
                  _buildRiskBadge(v.wealthMultiplier),
                ],
              ),
              const SizedBox(height: 24),
              _buildInfoRow('Owner', v.ownerName),
              _buildInfoRow('Vehicle', '${v.make} ${v.model}'),
              _buildInfoRow('Class', v.vehicleClass),
              const Divider(color: Colors.white10, height: 32),
              Row(
                children: [
                  Expanded(child: _buildValueBox('Invoice Price', '₹${v.invoicePrice.toInt().toString()}', ARGTheme.primaryBlue)),
                  const SizedBox(width: 16),
                  Expanded(child: _buildValueBox('Multipler', '${v.wealthMultiplier}x', ARGTheme.accentAmber)),
                ],
              ),
            ],
          ),
        ).animate().fadeIn().scale(curve: Curves.easeOutBack),
        
        const SizedBox(height: 24),
        
        ElevatedButton(
          onPressed: () {},
          style: ElevatedButton.styleFrom(
            backgroundColor: ARGTheme.primaryBlue,
            padding: const EdgeInsets.all(20),
          ),
          child: const Text('VIEW FULL HISTORY'),
        ).animate().fadeIn(delay: 400.ms),
      ],
    );
  }

  Widget _buildRiskBadge(double multiplier) {
    Color color = multiplier > 5.0 ? ARGTheme.errorRed : multiplier > 2.0 ? ARGTheme.accentAmber : ARGTheme.successGreen;
    String label = multiplier > 5.0 ? 'HIGH RISK' : multiplier > 2.0 ? 'MEDIUM' : 'LOW RISK';
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(12)),
      child: Text(label, style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold)),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Row(
        children: [
          Text('$label: ', style: const TextStyle(color: Colors.white38)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  Widget _buildValueBox(String label, String value, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: Colors.white38, fontSize: 12)),
        Text(value, style: TextStyle(color: color, fontSize: 20, fontWeight: FontWeight.bold)),
      ],
    );
  }

  Widget _buildEmptyState() {
    return Column(
      children: [
        const SizedBox(height: 40),
        Icon(Icons.directions_car_rounded, size: 80, color: Colors.white.withOpacity(0.05)),
        const SizedBox(height: 16),
        const Text('Search for a vehicle to view its\nWealth Compass profile.', 
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.white24),
        ),
      ],
    ).animate().fadeIn();
  }
}
