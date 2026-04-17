import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:image_picker/image_picker.dart';
import '../core/theme.dart';
import '../core/api_service.dart';

class VaultScreen extends StatefulWidget {
  const VaultScreen({super.key});

  @override
  State<VaultScreen> createState() => _VaultScreenState();
}

class _VaultScreenState extends State<VaultScreen> {
  bool _isUploading = false;

  void _addDocument() async {
    final picker = ImagePicker();
    final XFile? image = await picker.pickImage(source: ImageSource.gallery);
    
    if (image != null) {
      setState(() => _isUploading = true);
      
      // Simulate upload for specific contact (mock)
      final success = await APIService.uploadDoc(
        contact: "9876543210", 
        type: "NEW_DOC",
        bytes: await image.readAsBytes(),
      );
      
      setState(() => _isUploading = false);
      
      if (success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(backgroundColor: ARGTheme.ghpGreen, content: Text("Document safely encrypted and stored in vault."))
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Document Vault')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          _buildVaultHeader(),
          const SizedBox(height: 32),
          _buildDocumentCard(
            title: 'Registration Certificate (RC)',
            id: 'OR-01-A-1234',
            expiry: 'Expires: 12 July 2030',
            status: 'VALID',
            statusColor: ARGTheme.successGreen,
            icon: Icons.description_rounded,
          ).animate().fadeIn(delay: 200.ms).slideX(),
          
          const SizedBox(height: 16),
          
          _buildDocumentCard(
            title: 'Insurance Policy',
            id: 'ICICI-LOM-82123',
            expiry: 'Expires: 15 Oct 2026',
            status: 'VALID',
            statusColor: ARGTheme.successGreen,
            icon: Icons.verified_user_rounded,
          ).animate().fadeIn(delay: 400.ms).slideX(),
          
          const SizedBox(height: 16),
          
          _buildDocumentCard(
            title: 'PUC Certificate',
            id: 'PUC-91221',
            expiry: 'Expires in 12 days',
            status: 'EXPIRING SOON',
            statusColor: ARGTheme.accentAmber,
            icon: Icons.eco_rounded,
          ).animate().fadeIn(delay: 600.ms).slideX(),
          
          const SizedBox(height: 40),
          
          OutlinedButton.icon(
            onPressed: _isUploading ? null : _addDocument,
            icon: _isUploading ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.add_rounded),
            label: Text(_isUploading ? 'ENCRYPTING...' : 'ADD NEW DOCUMENT'),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size(double.infinity, 56),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              side: BorderSide(color: Colors.white.withOpacity(0.1)),
            ),
          ).animate().fadeIn(delay: 800.ms),
        ],
      ),
    );
  }

  Widget _buildVaultHeader() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Digital Document Vault', style: TextStyle(fontSize: 14, color: Colors.white38)),
        const SizedBox(height: 4),
        const Text('Verified & Legal Ready', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(color: ARGTheme.primaryBlue.withOpacity(0.1), borderRadius: BorderRadius.circular(12)),
          child: const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.lock_rounded, size: 14, color: ARGTheme.primaryBlue),
              SizedBox(width: 6),
              Text('END-TO-END ENCRYPTED', style: TextStyle(fontSize: 10, color: ARGTheme.primaryBlue, fontWeight: FontWeight.bold)),
            ],
          ),
        ),
      ],
    ).animate().fadeIn();
  }

  Widget _buildDocumentCard({
    required String title,
    required String id,
    required String expiry,
    required String status,
    required Color statusColor,
    required IconData icon,
  }) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: ARGTheme.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: Colors.white.withOpacity(0.05), borderRadius: BorderRadius.circular(16)),
            child: Icon(icon, color: Colors.white70, size: 24),
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                const SizedBox(height: 4),
                Text(id, style: const TextStyle(color: Colors.white38, fontSize: 12)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Text(expiry, style: const TextStyle(fontSize: 10, color: Colors.white54)),
                    const Spacer(),
                    Text(status, style: TextStyle(color: statusColor, fontSize: 10, fontWeight: FontWeight.bold)),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
