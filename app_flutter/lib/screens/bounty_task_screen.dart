import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../core/theme.dart';

class BountyTaskScreen extends StatefulWidget {
  const BountyTaskScreen({super.key});

  @override
  State<BountyTaskScreen> createState() => _BountyTaskScreenState();
}

class _BountyTaskScreenState extends State<BountyTaskScreen> {
  int _completedTasks = 0;
  double _potentialBounty = 0.0;
  
  // Mock image tasks from the Sentinel Mind
  final List<Map<String, String>> _tasks = [
    {'image': 'vehicle_1.jpg', 'hint': 'Check Brand & Grill'},
    {'image': 'vehicle_2.jpg', 'hint': 'Identify Luxury Trim'},
    {'image': 'vehicle_3.jpg', 'hint': 'Verify Plate Clarity'},
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ARGTheme.darkBg,
      appBar: AppBar(
        title: const Text('BOUNTY HUNTER', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 2)),
        centerTitle: true,
        backgroundColor: Colors.transparent,
        actions: [
          Center(
            child: Padding(
              padding: const EdgeInsets.only(right: 16),
              child: Text('₹$_potentialBounty', style: const TextStyle(color: ARGTheme.successGreen, fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          _buildProgressHeader(),
          Expanded(
            child: PageView.builder(
              itemCount: _tasks.length,
              itemBuilder: (context, index) => _buildTaskCard(_tasks[index]),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressHeader() {
    return Container(
      padding: const EdgeInsets.all(24),
      color: Colors.white.withOpacity(0.02),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildStat("Tasks Done", "$_completedTasks"),
          _buildStat("Accuracy", "94%"),
          _buildStat("Rank", "Expert"),
        ],
      ),
    );
  }

  Widget _buildStat(String label, String value) {
    return Column(
      children: [
        Text(label, style: const TextStyle(color: Colors.white30, fontSize: 10)),
        Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18)),
      ],
    );
  }

  Widget _buildTaskCard(Map<String, String> task) {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                color: Colors.black,
                borderRadius: BorderRadius.circular(32),
                border: Border.all(color: Colors.white10),
              ),
              child: const Center(
                child: Icon(Icons.image_search_rounded, color: Colors.white10, size: 100),
              ),
            ),
          ),
          const SizedBox(height: 24),
          const Text('ANALYZE VEHICLE', style: TextStyle(color: ARGTheme.primaryBlue, fontWeight: FontWeight.bold, fontSize: 12)),
          const SizedBox(height: 12),
          TextField(
            style: const TextStyle(color: Colors.white),
            decoration: _inputDecoration("Enter Brand (e.g. BMW, Toyota)"),
          ),
          const SizedBox(height: 12),
          TextField(
            style: const TextStyle(color: Colors.white),
            decoration: _inputDecoration("Enter Estimated Price (₹ Lakhs)"),
          ),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: () {
              setState(() {
                _completedTasks++;
                _potentialBounty += 50.0;
              });
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Submission sent to Sentinel for verification!'))
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: ARGTheme.primaryBlue,
              padding: const EdgeInsets.symmetric(vertical: 18),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            ),
            child: const Text('SUBMIT ANNOTATION', style: TextStyle(fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  InputDecoration _inputDecoration(String hint) {
    return InputDecoration(
      hintText: hint,
      hintStyle: const TextStyle(color: Colors.white24, fontSize: 13),
      filled: true,
      fillColor: Colors.white.withOpacity(0.05),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
    );
  }
}
