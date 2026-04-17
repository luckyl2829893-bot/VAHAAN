import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:go_router/go_router.dart';
import '../core/theme.dart';
import '../core/api_service.dart';

class CitizenPortal extends StatefulWidget {
  const CitizenPortal({super.key});

  @override
  State<CitizenPortal> createState() => _CitizenPortalState();
}

class _CitizenPortalState extends State<CitizenPortal> {
  bool isTakingTest = false;
  bool testSubmitted = false;
  Map<String, dynamic>? currentTask;
  bool? isPlateReadable;
  int questionsAnswered = 0;
  int totalExamQuestions = 5; 
  Map<String, dynamic> currentAnswers = {};

  void _startTest() async {
    final task = await APIService.getGradingTask();
    if (task != null) {
      setState(() {
        currentTask = task;
        isTakingTest = true;
        isPlateReadable = null;
        questionsAnswered = 0;
      });
    }
  }

  void _submitTest() async {
    if (currentTask == null) return;
    
    await APIService.syncGrading(
      filename: currentTask!['filename'],
      humanInput: {
          "research_results": currentAnswers,
          "source": "Citizen (Mobile)",
          "timestamp": DateTime.now().toIso8601String(),
      },
      aiPrediction: currentTask!['ai_prediction'],
    );
    
    currentAnswers = {}; 

    if (questionsAnswered + 1 < totalExamQuestions) {
       // Load next question
       final nextTask = await APIService.getGradingTask();
       setState(() {
          currentTask = nextTask;
          questionsAnswered++;
          isPlateReadable = null;
       });
    } else {
       // End of exam
       setState(() {
         isTakingTest = false;
         testSubmitted = true;
         currentTask = null;
       });
       await Future.delayed(const Duration(seconds: 4));
       if(mounted) setState(() => testSubmitted = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text('VAHAAN CITIZEN PORTAL', style: Theme.of(context).textTheme.titleLarge?.copyWith(letterSpacing: 2)),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildGoodHumanMeter(context),
            const SizedBox(height: 32),
            
            // --- THE ACTIVE EXAMINATION HALL ---
            if (isTakingTest) 
               _buildExaminationHall() 
            else if (testSubmitted) 
               _buildSubmissionStatus()
            else 
               _buildQualificationTasks(context),
            
            const SizedBox(height: 32),
            _buildCitizenActions(context),
            const SizedBox(height: 32),
            _buildRecentActivity(context),
          ],
        ),
      ),
    );
  }

  Widget _buildQualificationTasks(BuildContext context) {
      return Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
              gradient: LinearGradient(colors: [ARGTheme.primaryBlue.withOpacity(0.1), Colors.transparent]),
              borderRadius: BorderRadius.circular(28),
              border: Border.all(color: ARGTheme.primaryBlue.withOpacity(0.2)),
          ),
          child: Column(
              children: [
                  const Row(
                      children: [
                          Icon(Icons.assignment_rounded, color: ARGTheme.primaryBlue, size: 20),
                          SizedBox(width: 12),
                          Text("ACTIVE QUALIFICATION TESTS", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, letterSpacing: 1)),
                      ],
                  ),
                  const SizedBox(height: 16),
                  const Text("New images pushed from Sentinel Mind. Take the test to earn +50 GHP and Rewards.", style: TextStyle(fontSize: 11, color: Colors.grey)),
                  const SizedBox(height: 20),
                  ElevatedButton(
                      onPressed: _startTest,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: ARGTheme.primaryBlue,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 20),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      ),
                      child: const Center(child: Text("START QUALIFICATION TEST", style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 1.5))),
                  ),
              ],
          ),
      ).animate().fadeIn();
  }

  Widget _buildExaminationHall() {
      return Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
              color: Theme.of(context).cardTheme.color,
              borderRadius: BorderRadius.circular(32),
              border: Border.all(color: ARGTheme.meritGold, width: 2),
          ),
          child: Column(
              children: [
                   Text("QUESTION ${questionsAnswered + 1} OF $totalExamQuestions", style: const TextStyle(fontWeight: FontWeight.w900, color: ARGTheme.meritGold, fontSize: 10)),
                  const SizedBox(height: 16),
                  Container(
                      height: 220,
                      width: double.infinity,
                      decoration: BoxDecoration(
                          color: Colors.black12,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: Colors.white.withOpacity(0.05)),
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(16),
                        child: currentTask == null 
                          ? const Center(child: CircularProgressIndicator()) 
                          : Image.network(
                              '${APIService.baseUrl.replaceAll("/api", "")}${currentTask?['image_url']}',
                              fit: BoxFit.contain,
                              errorBuilder: (context, error, stackTrace) => const Center(child: Text("Image stream pending...")),
                            ),
                      ),
                  ),
                  const SizedBox(height: 16),
                  if (currentTask != null && (currentTask!['questions'] as List? ?? []).isEmpty)
                    _buildResearchQuestion({"id": "qc", "type": "binary", "text": "Is the vehicle data captured above accurate?"})
                  else
                    ... (currentTask?['questions'] as List? ?? []).map((q) => _buildResearchQuestion(q)),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () async {
                              await APIService.skipTask();
                              final task = await APIService.getGradingTask();
                              if (task != null) {
                                  setState(() => currentTask = task);
                              }
                          },
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(color: Colors.white24),
                            padding: const EdgeInsets.symmetric(vertical: 20),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                          ),
                          child: const Text("SKIP", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        flex: 2,
                        child: ElevatedButton(
                            onPressed: _submitTest,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: ARGTheme.meritGold, 
                              foregroundColor: Colors.black, 
                              padding: const EdgeInsets.symmetric(vertical: 20),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                              elevation: 8,
                            ),
                            child: Text(
                              questionsAnswered + 1 == totalExamQuestions ? "SUBMIT BATCH" : "NEXT VERIFICATION", 
                              style: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: 1.5, color: Colors.black, fontSize: 10),
                            ),
                        ),
                      ),
                    ],
                  ),
              ],
          ),
      ).animate().slideX(begin: 1).fadeIn();
  }

  Widget _buildResearchQuestion(Map<String, dynamic> q) {
    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: Colors.white.withOpacity(0.03), borderRadius: BorderRadius.circular(20), border: Border.all(color: Colors.white10)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(q['text'], style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: ARGTheme.meritGold)),
          const SizedBox(height: 12),
          if (q['type'] == 'binary') 
             Row(children: [
               _buildChoiceChip(q['id'], "Yes"),
               const SizedBox(width: 8),
               _buildChoiceChip(q['id'], "No"),
             ])
          else 
             Wrap(spacing: 8, runSpacing: 8, children: (q['options'] as List).map((opt) => _buildChoiceChip(q['id'], opt.toString())).toList()),
        ],
      ),
    );
  }

  Widget _buildChoiceChip(String qId, String value) {
    bool isSelected = currentAnswers[qId] == value;
    return InkWell(
      onTap: () => setState(() => currentAnswers[qId] = value),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? ARGTheme.meritGold : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: isSelected ? ARGTheme.meritGold : Colors.white24),
        ),
        child: Text(value, style: TextStyle(color: isSelected ? Colors.black : Colors.white70, fontSize: 10, fontWeight: FontWeight.bold)),
      ),
    );
  }

  Widget _buildSubmissionStatus() {
      return Container(
          padding: const EdgeInsets.all(40),
          width: double.infinity,
          decoration: BoxDecoration(color: ARGTheme.ghpGreen.withOpacity(0.1), borderRadius: BorderRadius.circular(32)),
          child: const Column(
              children: [
                  Icon(Icons.auto_awesome_rounded, color: ARGTheme.ghpGreen, size: 40),
                  SizedBox(height: 16),
                  Text("EXAM SUBMITTED", style: TextStyle(fontWeight: FontWeight.bold, color: ARGTheme.ghpGreen)),
                  Text("Sentinel Mind is now grading your work.", style: TextStyle(fontSize: 10, color: Colors.grey)),
              ],
          ),
      ).animate().shake();
  }

  Widget _buildGoodHumanMeter(BuildContext context) {
    final bool isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Theme.of(context).cardTheme.color,
        borderRadius: BorderRadius.circular(32),
        border: Border.all(color: ARGTheme.ghpGreen.withOpacity(isDark ? 0.1 : 0.3), width: 2),
      ),
      child: Row(
        children: [
          SizedBox(
            height: 100, width: 100,
            child: PieChart(PieChartData(sectionsSpace: 0, centerSpaceRadius: 35, sections: [
              PieChartSectionData(color: ARGTheme.ghpGreen, value: 925, radius: 10, showTitle: false),
              PieChartSectionData(color: Colors.grey.withOpacity(0.1), value: 75, radius: 10, showTitle: false),
            ])),
          ),
          const SizedBox(width: 24),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('GOOD HUMAN POINTS', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 10)),
                Text('925', style: Theme.of(context).textTheme.displayLarge?.copyWith(color: ARGTheme.ghpGreen, fontSize: 40)),
                const Text('LEGENDARY TIER', style: TextStyle(color: ARGTheme.ghpGreen, fontSize: 10, fontWeight: FontWeight.bold)),
              ],
            ),
          ),
        ],
      ),
    ).animate().fadeIn();
  }

  Widget _buildCitizenActions(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
                Text('QUICK ACCESS', style: Theme.of(context).textTheme.titleLarge),
                IconButton(onPressed: () => context.push('/vault'), icon: const Icon(Icons.folder_shared_rounded, color: ARGTheme.primaryBlue)),
            ],
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(child: _ActionCard(title: 'Claim\nReward', icon: Icons.stars_rounded, color: ARGTheme.meritGold, onTap: () => context.push('/bounties'))),
            const SizedBox(width: 16),
            Expanded(child: _ActionCard(title: 'Report\nViolation', icon: Icons.add_moderator_rounded, color: ARGTheme.redCard, onTap: () => context.push('/report'))),
          ],
        ),
      ],
    ).animate().fadeIn(delay: 200.ms);
  }

  Widget _buildRecentActivity(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('RECENT ACTIVITY', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 16),
        _HistoryItem(title: 'Speeding Challan Paid', subtitle: 'DL-8CAD-1234 • -₹1,250', icon: Icons.payment_rounded, color: ARGTheme.ghpGreen, secondary: 'PAID'),
        _HistoryItem(title: 'Bounty Credited', subtitle: 'Violation #8212 • +₹250', icon: Icons.currency_rupee_rounded, color: ARGTheme.primaryBlue, secondary: 'SUCCESS'),
        _HistoryItem(title: 'E-Challan Pending', subtitle: 'Illegal Parking • ₹500', icon: Icons.warning_amber_rounded, color: ARGTheme.meritGold, secondary: 'DUE NOW'),
      ],
    ).animate().fadeIn(delay: 400.ms);
  }
}

class _ActionCard extends StatelessWidget {
  final String title; final IconData icon; final Color color; final VoidCallback onTap;
  const _ActionCard({required this.title, required this.icon, required this.color, required this.onTap});
  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap, borderRadius: BorderRadius.circular(24),
      child: Container(
        height: 110, padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: Theme.of(context).cardTheme.color, borderRadius: BorderRadius.circular(24), border: Border.all(color: color.withOpacity(0.2))),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(icon, color: color, size: 28), const SizedBox(height: 10), Text(title, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12))]),
      ),
    );
  }
}

class _HistoryItem extends StatelessWidget {
  final String title; final String subtitle; final IconData icon; final Color color; final String secondary;
  const _HistoryItem({required this.title, required this.subtitle, required this.icon, required this.color, required this.secondary});
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12), padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: Theme.of(context).cardTheme.color?.withOpacity(0.5), borderRadius: BorderRadius.circular(20), border: Border.all(color: Colors.white.withOpacity(0.05))),
      child: Row(children: [
        Container(padding: const EdgeInsets.all(10), decoration: BoxDecoration(color: color.withOpacity(0.1), shape: BoxShape.circle), child: Icon(icon, color: color, size: 20)),
        const SizedBox(width: 16),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)), Text(subtitle, style: const TextStyle(fontSize: 11, color: Colors.grey))])),
        Text(secondary, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 10)),
      ]),
    );
  }
}
