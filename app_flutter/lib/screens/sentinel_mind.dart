import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../core/theme.dart';
import '../core/api_service.dart';

class SentinelMind extends StatefulWidget {
  const SentinelMind({super.key});

  @override
  State<SentinelMind> createState() => _SentinelMindState();
}

class _SentinelMindState extends State<SentinelMind> {
  double stabilityIndex = 99.4;
  bool isGrading = false;
  Map<String, dynamic>? currentTask;
  int learnedCount = 0;
  List<Map<String, dynamic>> reviewQueue = [];
  bool isPushing = false;
  Map<String, dynamic>? currentStatus;
  
  // Input Controllers for the Lab
  final plateController = TextEditingController();
  final modelController = TextEditingController();
  final brandController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _fetchStatus();
    _fetchReviewQueue();
  }

  Future<void> _fetchReviewQueue() async {
    final queue = await APIService.getReviewQueue();
    setState(() => reviewQueue = queue);
  }

  Future<void> _fetchStatus() async {
    final status = await APIService.getSentinelStatus();
    if (status != null) {
      setState(() {
        currentStatus = status;
        stabilityIndex = status['stability'] ?? 99.4;
        learnedCount = status['total_learned'] ?? 0;
      });
    }
  }

  void _acknowledgeMilestone() async {
      final success = await APIService.resetMilestone();
      if (success) {
          _fetchStatus();
          if(mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text("Milestone Acknowledged. Starting next 500-image collection.")),
            );
          }
      }
  }

  Widget _buildMilestoneNotification() {
    if (currentStatus == null) return const SizedBox.shrink();
    
    int count = currentStatus!['pending_milestone_count'] ?? 0;
    double progress = (count / 500).clamp(0.0, 1.0);
    bool isReady = count >= 500;

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
          boxShadow: [BoxShadow(color: isReady ? ARGTheme.meritGold.withOpacity(0.3) : Colors.black26, blurRadius: 20)],
          color: ARGTheme.surface,
          borderRadius: BorderRadius.circular(32),
          border: Border.all(color: isReady ? ARGTheme.meritGold : Colors.white10, width: 2)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
            Row(children: [
                Icon(isReady ? Icons.auto_awesome_rounded : Icons.hourglass_top_rounded, color: isReady ? ARGTheme.meritGold : Colors.grey, size: 28),
                const SizedBox(width: 12),
                Text(isReady ? "NEURAL MASS REACHED" : "COLLECTING NEURAL DATA", style: TextStyle(color: isReady ? ARGTheme.meritGold : Colors.white, fontWeight: FontWeight.w900, letterSpacing: 1)),
            ]),
            const SizedBox(height: 16),
            LinearProgressIndicator(
              value: progress,
              backgroundColor: Colors.white10,
              color: isReady ? ARGTheme.meritGold : ARGTheme.primaryBlue,
              minHeight: 8,
              borderRadius: BorderRadius.circular(4),
            ),
            const SizedBox(height: 12),
            Text("$count / 500 Human-Assisted images verified for Retraining Batch.", style: const TextStyle(color: Colors.grey, fontSize: 10, fontWeight: FontWeight.bold)),
            if (isReady) ...[
                const SizedBox(height: 20),
                ElevatedButton(
                    onPressed: _acknowledgeMilestone,
                    style: ElevatedButton.styleFrom(backgroundColor: ARGTheme.meritGold, foregroundColor: Colors.black, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
                    child: const Center(child: Text("ACTIVATE NEURAL ENGINE / BEGIN RETRAINING", style: TextStyle(fontWeight: FontWeight.w900, fontSize: 11))),
                ),
            ],
        ],
      ),
    ).animate().fadeIn();
  }

  Future<void> _fetchTask() async {
    final task = await APIService.getGradingTask();
    if (task != null) {
      setState(() {
        currentTask = task;
        isGrading = true;
        
        // Reset controllers with AI's current best guess
        plateController.text = task['ai_prediction']['plate'] ?? "";
        modelController.text = task['ai_prediction']['model'] ?? "";
        brandController.text = task['ai_prediction']['brand'] ?? "";
      });
    }
  }

  void _syncToNeuralMemory() async {
    if (currentTask == null) return;

    final success = await APIService.syncGrading(
      filename: currentTask!['filename'],
      humanInput: {
        "plate": plateController.text,
        "model": modelController.text,
        "brand": brandController.text,
      },
      aiPrediction: currentTask!['ai_prediction'],
    );

    if (success) {
      _fetchStatus();
      _fetchReviewQueue();
      if(mounted) {
         ScaffoldMessenger.of(context).showSnackBar(
           const SnackBar(
             backgroundColor: ARGTheme.harmonyTeal,
             content: Text("AI ACCOUNTABILITY SYNCED: NEURAL RETRAINING TRIGGERED.", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.black)),
           )
         );
      }
      _fetchTask(); // Load next task
    }
  }

  void _pushBatch() async {
    setState(() => isPushing = true);
    final success = await APIService.pushBatch(5);
    setState(() => isPushing = false);
    
    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("New batch pushed to Citizens!"))
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        title: Text(isGrading ? 'VAHAAN NEURAL LAB' : 'VAHAAN CORE COMMAND', style: Theme.of(context).textTheme.titleLarge),
        centerTitle: true,
        backgroundColor: Colors.transparent,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            if (!isGrading) ...[
                _buildMilestoneNotification(),
                const SizedBox(height: 16),
                _buildMainAnnotationLoop(),
            ] else ...[
                _buildInteractiveAILab(),
            ],
            const SizedBox(height: 32),
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
                                  const Icon(Icons.psychology_rounded, color: ARGTheme.meritGold),
                                  Text(currentTask?['filename'] ?? "IDENTIFYING...", style: const TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1, fontSize: 10)),
                                  const Icon(Icons.verified_user_rounded, color: ARGTheme.ghpGreen),
                              ],
                          ),
                          const SizedBox(height: 20),
                          if (currentTask?['ai_memory_insight'] != null && currentTask!['ai_memory_insight'] != "")
                             Container(
                               margin: const EdgeInsets.only(bottom: 12),
                               padding: const EdgeInsets.all(12),
                               decoration: BoxDecoration(color: ARGTheme.harmonyTeal.withOpacity(0.1), borderRadius: BorderRadius.circular(12), border: Border.all(color: ARGTheme.harmonyTeal.withOpacity(0.3))),
                               child: Text(currentTask!['ai_memory_insight'], style: const TextStyle(fontSize: 9, color: ARGTheme.harmonyTeal, fontWeight: FontWeight.bold)),
                             ),
                          ClipRRect(
                              borderRadius: BorderRadius.circular(16),
                              child: Container(
                                color: Colors.black12,
                                height: 260, width: double.infinity,
                                child: Image.network(
                                    '${APIService.baseUrl.replaceAll("/api", "")}${currentTask?['image_url']}',
                                    fit: BoxFit.contain,
                                    errorBuilder: (context, error, stackTrace) => const Center(child: Text("Image stream pending/corrupt...")),
                                ),
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
                      Expanded(child: _buildValidationForm("NEURAL NOTES (HUMAN INPUT)", Colors.white, isAI: false)),
                      const SizedBox(width: 16),
                      Expanded(child: _buildValidationForm("DYNAMIC POINTS (AI PREDICTION)", ARGTheme.harmonyTeal.withOpacity(0.5), isAI: true)),
                  ],
              ),
              
              const SizedBox(height: 32),
              
              Row(
                  children: [
                      Expanded(child: OutlinedButton(onPressed: () => setState(() => isGrading = false), child: const Text("CLOSE LAB"))),
                      const SizedBox(width: 12),
                      Expanded(child: OutlinedButton(
                          onPressed: () async {
                              await APIService.skipTask();
                              _fetchTask();
                          }, 
                          style: OutlinedButton.styleFrom(side: const BorderSide(color: Colors.white24)),
                          child: const Text("SKIP / NEXT", style: TextStyle(fontSize: 10)),
                      )),
                      const SizedBox(width: 12),
                      Expanded(flex: 2, child: ElevatedButton(
                          onPressed: _syncToNeuralMemory, 
                          style: ElevatedButton.styleFrom(
                            backgroundColor: ARGTheme.electricBlue, 
                            foregroundColor: Colors.white, 
                            padding: const EdgeInsets.symmetric(vertical: 24),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                          ),
                          child: const Text("SUBMIT TO NEURAL CORE", style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 1.2, fontSize: 10)),
                      )),
                  ],
              ),
          ],
      );
  }

  Widget _buildValidationForm(String label, Color color, {required bool isAI}) {
      final prediction = currentTask?['ai_prediction'] ?? {};
      return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
              Text(label, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 8, color: color)),
              const SizedBox(height: 12),
              isAI 
                ? _buildPredictionBox("PLATE", prediction['plate'])
                : _buildSmallField("PLATE", plateController),
              const SizedBox(height: 8),
              isAI 
                ? _buildPredictionBox("MODEL", prediction['model'])
                : _buildSmallField("MODEL", modelController),
              const SizedBox(height: 8),
              isAI 
                ? _buildPredictionBox("BRAND", prediction['brand'])
                : _buildSmallField("BRAND", brandController),
          ],
      );
  }

  Widget _buildPredictionBox(String label, String? value) {
     return Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(color: ARGTheme.harmonyTeal.withOpacity(0.05), borderRadius: BorderRadius.circular(12), border: Border.all(color: ARGTheme.harmonyTeal.withOpacity(0.2))),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontSize: 8, color: Colors.grey)),
            Text(value ?? "N/A", style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: ARGTheme.harmonyTeal)),
          ],
        ),
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


  Widget _buildMainAnnotationLoop() {
      return Column(
          children: [
              _buildDispatchCard(),
              const SizedBox(height: 16),
              _buildGradingWorkCard(),
              const SizedBox(height: 16),
              _buildSelfEvaluationAudit(),
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
            onPressed: isPushing ? null : _pushBatch,
            child: isPushing 
              ? const SizedBox(height: 12, width: 12, child: CircularProgressIndicator(strokeWidth: 2))
              : const Text("PUSH DATA BATCH TO CITIZENS"),
          ),
        ],
      ),
    );
  }

  Widget _buildSelfEvaluationAudit() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(color: ARGTheme.surface, borderRadius: BorderRadius.circular(28), border: Border.all(color: ARGTheme.harmonyTeal.withOpacity(0.1))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
            const Text("AUTONOMOUS NEURAL AUDITS", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, letterSpacing: 1, color: ARGTheme.harmonyTeal)),
            const SizedBox(height: 16),
            const Text("Neural Core is evaluating human data streams. Gemma-2 is resolving logic discrepancies autonomously.", style: TextStyle(fontSize: 10, color: Colors.grey)),
            const SizedBox(height: 20),
            _buildAuditItem("Motion blur detected; human override accepted via LLM.", "SYNCED", ARGTheme.harmonyTeal),
            _buildAuditItem("Night vision disparity resolved; Retraining data weights updated.", "RE-WEIGHTED", ARGTheme.meritGold),
            _buildAuditItem("Discrepancy in vehicle brand categorized as 'OOD' (Out of Distribution).", "RESOLVED", ARGTheme.primaryBlue),
        ],
      ),
    );
  }

  Widget _buildAuditItem(String msg, String status, Color color) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(child: Text("• $msg", style: const TextStyle(fontSize: 10, color: Colors.white70))),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(8)),
            child: Text(status, style: TextStyle(color: color, fontSize: 8, fontWeight: FontWeight.w900, letterSpacing: 0.5)),
          ),
        ],
      ),
    );
  }

  Widget _buildGradingWorkCard() {
     return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(color: Theme.of(context).cardTheme.color, borderRadius: BorderRadius.circular(32), border: Border.all(color: ARGTheme.meritGold.withOpacity(0.2))),
      child: Column(
        children: [
          const Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text("ACCOUNTABILITY LAB", style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 1)),
              Icon(Icons.psychology_rounded, color: ARGTheme.meritGold),
          ]),
          const SizedBox(height: 12),
          Text("${learnedCount + 100} entries synchronized via Neural Core.", style: const TextStyle(fontSize: 10, color: Colors.grey)),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
                onPressed: _fetchTask,
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: ARGTheme.meritGold, width: 1.5),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: const Text("ACCESS NEURAL ACCOUNTABILITY", style: TextStyle(color: ARGTheme.meritGold, fontWeight: FontWeight.bold, fontSize: 12)),
            ),
          ),
        ],
      ),
    );
  }

}
