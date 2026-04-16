import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../core/theme.dart';

class SentinelMind extends StatefulWidget {
  const SentinelMind({super.key});

  @override
  State<SentinelMind> createState() => _SentinelMindState();
}

class _SentinelMindState extends State<SentinelMind> {
  double stabilityIndex = 99.4;
  bool isGrading = false;
  int currentImageIndex = 1;
  int totalImages = 463;
  
  // Input Controllers for the Lab
  final plateController = TextEditingController(text: "DL 8C AD 1234");
  final modelController = TextEditingController(text: "Mercedes G-Class");
  final brandController = TextEditingController(text: "Mercedes-Benz");

  void _syncToNeuralMemory() async {
    // Show self-learning effect
    if(mounted) {
       ScaffoldMessenger.of(context).showSnackBar(
         const SnackBar(
           backgroundColor: ARGTheme.harmonyTeal,
           content: Text("AI ACCOUNTABILITY SYNCED: NEURAL RETRAINING TRIGGERED.", style: TextStyle(fontWeight: FontWeight.bold)),
         )
       );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        title: Text(isGrading ? 'AI ACCOUNTABILITY LAB' : 'SENTINEL CORE COMMAND', style: Theme.of(context).textTheme.titleLarge),
        centerTitle: true,
        backgroundColor: Colors.transparent,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            if (!isGrading) ...[
                _buildStabilityMonitor(),
                const SizedBox(height: 32),
                _buildMainAnnotationLoop(),
            ] else ...[
                _buildInteractiveAILab(),
            ],
            const SizedBox(height: 32),
            _buildSystemInfrastructure(),
          ],
        ),
      ),
    );
  }

  Widget _buildInteractiveAILab() {
      return Column(
          children: [
              // --- IMAGE CAROUSEL & NAVIGATOR ---
              Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(color: Theme.of(context).cardTheme.color, borderRadius: BorderRadius.circular(32), border: Border.all(color: ARGTheme.meritGold)),
                  child: Column(
                      children: [
                          Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                  IconButton(onPressed: () => setState(() => currentImageIndex--), icon: const Icon(Icons.arrow_back_ios_new_rounded)),
                                  Text("IMAGE $currentImageIndex / $totalImages", style: const TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1)),
                                  IconButton(onPressed: () => setState(() => currentImageIndex++), icon: const Icon(Icons.arrow_forward_ios_rounded)),
                              ],
                          ),
                          const SizedBox(height: 20),
                          ClipRRect(
                              borderRadius: BorderRadius.circular(16),
                              child: Image.network(
                                  'https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&q=80&w=2069',
                                  height: 180, width: double.infinity, fit: BoxFit.cover,
                              ),
                          ),
                      ],
                  ),
              ).animate().slideY(begin: 0.1),
              
              const SizedBox(height: 24),
              
              // --- DUAL-INPUT VALIDATION FORM ---
              Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                      Expanded(child: _buildValidationForm("HUMAN INPUT", Colors.white)),
                      const SizedBox(width: 16),
                      Expanded(child: _buildValidationForm("AI PREDICTION", ARGTheme.harmonyTeal.withOpacity(0.5))),
                  ],
              ),
              
              const SizedBox(height: 32),
              
              Row(
                  children: [
                      Expanded(child: OutlinedButton(onPressed: () => setState(() => isGrading = false), child: const Text("CLOSE LAB"))),
                      const SizedBox(width: 16),
                      Expanded(child: ElevatedButton(
                          onPressed: _syncToNeuralMemory, 
                          style: ElevatedButton.styleFrom(backgroundColor: ARGTheme.harmonyTeal),
                          child: const Text("SYNC & RETRAIN AI", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                      )),
                  ],
              ),
          ],
      );
  }

  Widget _buildValidationForm(String label, Color color) {
      return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
              Text(label, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 10, color: color)),
              const SizedBox(height: 12),
              _buildSmallField("PLATE", plateController),
              const SizedBox(height: 8),
              _buildSmallField("MODEL", modelController),
              const SizedBox(height: 8),
              _buildSmallField("BRAND", brandController),
          ],
      );
  }

  Widget _buildSmallField(String hint, TextEditingController controller) {
      return Container(
          decoration: BoxDecoration(color: Colors.white.withOpacity(0.02), borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.white10)),
          child: TextField(
              controller: controller,
              style: const TextStyle(fontSize: 12),
              decoration: InputDecoration(
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  hintText: hint,
                  border: InputBorder.none,
              ),
          ),
      );
  }

  Widget _buildStabilityMonitor() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Theme.of(context).cardTheme.color,
        borderRadius: BorderRadius.circular(32),
        border: Border.all(color: ARGTheme.harmonyTeal.withOpacity(0.3), width: 2),
      ),
      child: Column(
        children: [
            Row(
                children: [
                    const Icon(Icons.balance_rounded, color: ARGTheme.harmonyTeal, size: 20),
                    const SizedBox(width: 12),
                    Text('SOCIAL STABILITY INDEX', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontSize: 12, letterSpacing: 2)),
                ],
            ),
            const SizedBox(height: 16),
            Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                    Text("${stabilityIndex}%", style: TextStyle(fontSize: 48, fontWeight: FontWeight.w900, color: ARGTheme.harmonyTeal)),
                    const Text("EQUITY STABLE", style: TextStyle(color: ARGTheme.ghpGreen, fontWeight: FontWeight.bold, fontSize: 10)),
                ],
            ),
        ],
      ),
    ).animate().fadeIn();
  }

  Widget _buildMainAnnotationLoop() {
      return Column(
          children: [
              _buildDispatchCard(),
              const SizedBox(height: 16),
              _buildGradingWorkCard(),
          ],
      ).animate().fadeIn();
  }

  Widget _buildDispatchCard() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(color: Theme.of(context).cardTheme.color, borderRadius: BorderRadius.circular(24), border: Border.all(color: ARGTheme.electricBlue.withOpacity(0.2))),
      child: Column(
        children: [
          const Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text("BATCH DISPATCH", style: TextStyle(fontWeight: FontWeight.bold)),
              Icon(Icons.cloud_upload_rounded, color: ARGTheme.electricBlue),
          ]),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () {},
            child: const Text("PUSH DATA BATCH TO CITIZENS"),
          ),
        ],
      ),
    );
  }

  Widget _buildGradingWorkCard() {
     return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(color: Theme.of(context).cardTheme.color, borderRadius: BorderRadius.circular(24), border: Border.all(color: ARGTheme.meritGold.withOpacity(0.2))),
      child: Column(
        children: [
          const Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text("GRADING WORKSPACE", style: TextStyle(fontWeight: FontWeight.bold)),
              Icon(Icons.edit_note_rounded, color: ARGTheme.meritGold),
          ]),
          const SizedBox(height: 12),
          const Text("Images awaiting accountability cross-check.", style: TextStyle(fontSize: 10, color: Colors.grey)),
          const SizedBox(height: 16),
          OutlinedButton(
            onPressed: () => setState(() => isGrading = true),
            style: OutlinedButton.styleFrom(side: const BorderSide(color: ARGTheme.meritGold)),
            child: const Text("OPEN AI ACCOUNTABILITY LAB", style: TextStyle(color: ARGTheme.meritGold)),
          ),
        ],
      ),
    );
  }

  Widget _buildSystemInfrastructure() {
      return Row(
          children: [
              Expanded(child: _buildSmallInfo("Teacher Precision", "99.9%", ARGTheme.harmonyTeal)),
              const SizedBox(width: 12),
              Expanded(child: _buildSmallInfo("Auto-Retrain Status", "Ready", ARGTheme.primaryBlue)),
          ],
      ).animate().fadeIn();
  }

  Widget _buildSmallInfo(String label, String value, Color color) {
      return Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: Theme.of(context).cardTheme.color, borderRadius: BorderRadius.circular(20)),
          child: Column(
              children: [
                  Text(label, style: const TextStyle(fontSize: 10, color: Colors.grey)),
                  Text(value, style: TextStyle(fontWeight: FontWeight.bold, color: color)),
              ],
          ),
      );
  }
}
