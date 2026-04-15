import 'package:flutter/material.dart';
import '../core/theme.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // Mock user data - in real app, fetch from session/provider
    const userName = "Slasher";
    const userRole = "Sentinel (Highest Admin)";
    const clearance = "Level 5 - Overlord";
    const contact = "+91 99999 99999";
    const profId = "ARG-SENTINEL-001";

    return Scaffold(
      backgroundColor: ARGTheme.darkBg,
      appBar: AppBar(
        title: const Text('Admin Command Profile'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          Container(
            margin: const EdgeInsets.only(right: 16),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.red.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.red.withOpacity(0.5)),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.gpp_maybe_rounded, color: Colors.redAccent, size: 14),
                SizedBox(width: 4),
                Text('SENSITIVE ACCESS', style: TextStyle(color: Colors.redAccent, fontSize: 10, fontWeight: FontWeight.bold)),
              ],
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          children: [
            Stack(
              alignment: Alignment.bottomRight,
              children: [
                const CircleAvatar(
                  radius: 60,
                  backgroundColor: ARGTheme.primaryBlue,
                  child: Icon(Icons.security_rounded, size: 70, color: Colors.white),
                ),
                Container(
                  padding: const EdgeInsets.all(4),
                  decoration: const BoxDecoration(color: ARGTheme.successGreen, shape: BoxShape.circle),
                  child: const Icon(Icons.verified_user_rounded, color: Colors.white, size: 20),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Text(userName, style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white)),
            Text(userRole, style: const TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              decoration: BoxDecoration(color: Colors.white.withOpacity(0.05), borderRadius: BorderRadius.circular(20)),
              child: Text(clearance, style: const TextStyle(color: Colors.white70, fontSize: 12)),
            ),
            const SizedBox(height: 40),
            
            _buildInfoCard(context, 'Contact', contact, Icons.phone_rounded),
            _buildInfoCard(context, 'Professional ID', profId, Icons.badge_rounded),
            
            const SizedBox(height: 40),
            const Align(
              alignment: Alignment.centerLeft,
              child: Text('MY CERTIFICATES', style: TextStyle(color: Colors.white60, fontWeight: FontWeight.bold, fontSize: 12)),
            ),
            const SizedBox(height: 16),
            
            _buildCertificateCard(
              context, 
              'Road Safety Expert', 
              'MLP Bootcamp • 2026', 
              'assets/certificate.jpg' // Assuming the image is synced to assets
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoCard(BuildContext context, String label, String value, IconData icon) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white10),
      ),
      child: Row(
        children: [
          Icon(icon, color: ARGTheme.primaryBlue),
          const SizedBox(width: 20),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: const TextStyle(color: Colors.white54, fontSize: 12)),
              Text(value, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildCertificateCard(BuildContext context, String title, String issuer, String imagePath) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [ARGTheme.primaryBlue.withOpacity(0.2), Colors.transparent]),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: ARGTheme.primaryBlue.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.verified_rounded, color: ARGTheme.primaryBlue, size: 20),
              const SizedBox(width: 8),
              Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white)),
            ],
          ),
          const SizedBox(height: 4),
          Text(issuer, style: const TextStyle(color: Colors.white54, fontSize: 12)),
          const SizedBox(height: 16),
          // Certificate Preview Simulation
          Container(
            height: 120,
            width: double.infinity,
            decoration: BoxDecoration(
              color: Colors.black26,
              borderRadius: BorderRadius.circular(12),
              image: const DecorationImage(
                image: NetworkImage('https://images.unsplash.com/photo-1546410531-bb4caa6b424d?auto=format&fit=crop&q=80&w=2071&ixlib=rb-4.0.3'),
                fit: BoxFit.cover,
                opacity: 0.5,
              ),
            ),
            child: const Center(child: Icon(Icons.remove_red_eye_rounded, color: Colors.white70)),
          ),
        ],
      ),
    );
  }
}
