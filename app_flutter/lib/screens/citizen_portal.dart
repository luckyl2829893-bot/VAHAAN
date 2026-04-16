import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:go_router/go_router.dart';
import '../core/theme.dart';

class CitizenPortal extends StatefulWidget {
  const CitizenPortal({super.key});

  @override
  State<CitizenPortal> createState() => _CitizenPortalState();
}

class _CitizenPortalState extends State<CitizenPortal> {
  bool isTakingTest = false;
  bool testSubmitted = false;

  void _startTest() => setState(() => isTakingTest = true);
  void _submitTest() async {
    setState(() => isTakingTest = false);
    setState(() => testSubmitted = true);
    await Future.delayed(2.seconds);
    setState(() => testSubmitted = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text('CITIZEN PORTAL', style: Theme.of(context).textTheme.titleLarge?.copyWith(letterSpacing: 2)),
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
                      style: ElevatedButton.styleFrom(backgroundColor: ARGTheme.primaryBlue),
                      child: const Center(child: Text("START QUALIFICATION TEST")),
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
                  const Text("EXAMINATION HALL", style: TextStyle(fontWeight: FontWeight.w900, color: ARGTheme.meritGold)),
                  const SizedBox(height: 16),
                  Container(
                      height: 140,
                      width: double.infinity,
                      decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(16),
                          image: const DecorationImage(
                              image: NetworkImage('https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&q=80&w=2070'),
                              fit: BoxFit.cover,
                          ),
                      ),
                  ),
                  const SizedBox(height: 16),
                  const Text("Is the License Plate visible and readable?", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                  Row(
                      children: [
                          Expanded(child: RadioListTile(value: true, groupValue: true, onChanged: (v){}, title: const Text("YES", style: TextStyle(fontSize: 10)))),
                          Expanded(child: RadioListTile(value: false, groupValue: true, onChanged: (v){}, title: const Text("NO", style: TextStyle(fontSize: 10)))),
                      ],
                  ),
                  ElevatedButton(
                      onPressed: _submitTest,
                      style: ElevatedButton.styleFrom(backgroundColor: ARGTheme.ghpGreen),
                      child: const Text("SUBMIT PAPER FOR GRADING", style: TextStyle(color: Colors.white)),
                  ),
              ],
          ),
      ).animate().slideX(begin: 1).fadeIn();
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
