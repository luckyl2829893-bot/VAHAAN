import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:image_picker/image_picker.dart';
import '../core/theme.dart';
import '../core/api_service.dart';

class ReportScreen extends StatefulWidget {
  const ReportScreen({super.key});

  @override
  State<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends State<ReportScreen> {
  final _plateController = TextEditingController();
  final _summaryController = TextEditingController();
  String _violationType = 'Speeding';
  bool _isSubmitting = false;
  Uint8List? _evidenceBytes;
  String? _evidenceName;

  final List<String> _types = [
    'Speeding',
    'Red Light Jump',
    'Wrong Side',
    'No Helmet',
    'Pothole',
    'Illegal Parking',
    'Other',
  ];

  void _submit() async {
    if (_plateController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a plate number')),
      );
      return;
    }

    setState(() => _isSubmitting = true);
    
    final success = await APIService.reportViolation(
      plate: _plateController.text,
      type: _violationType,
      evidencePath: _evidenceName ?? 'video.mp4',
      lat: 28.6139,
      lng: 77.2090,
    );

    setState(() => _isSubmitting = false);

    if (success && mounted) {
      _showSuccessDialog();
    }
  }

  void _showSuccessDialog() {
    // In real app, pull from session
    const userName = "Rajesh"; 

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        backgroundColor: ARGTheme.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        title: const Text('✅ Report Logged'),
        content: Text('Thank you, $userName! We will look into it. Thank you.'),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context); // Close dialog
              Navigator.pop(context); // Go back to dashboard
            },
            child: const Text('CONTINUE', style: TextStyle(color: ARGTheme.primaryBlue, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Report Violation')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildCameraPreview(),
            const SizedBox(height: 32),
            _buildFieldLabel('LICENSE PLATE'),
            const SizedBox(height: 8),
            _buildPlateInput(),
            const SizedBox(height: 24),
            _buildFieldLabel('VIOLATION TYPE'),
            const SizedBox(height: 8),
            _buildTypeDropdown(),
            const SizedBox(height: 24),
            _buildFieldLabel('VIOLATION SUMMARY'),
            const SizedBox(height: 8),
            _buildSummaryInput(),
            const SizedBox(height: 40),
            _buildSubmitButton(),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryInput() {
    return TextField(
      controller: _summaryController,
      maxLines: 4,
      decoration: InputDecoration(
        filled: true,
        fillColor: ARGTheme.surface,
        hintText: _violationType == 'Other' ? 'Describe the violation in detail...' : 'Additional notes (optional)...',
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
      ),
    );
  }

  void _pickEvidence() async {
    final picker = ImagePicker();
    final XFile? image = await picker.pickImage(source: ImageSource.camera);
    if (image != null) {
      final bytes = await image.readAsBytes();
      setState(() {
        _evidenceBytes = bytes;
        _evidenceName = image.name;
      });
    }
  }

  Widget _buildCameraPreview() {
    return InkWell(
      onTap: _pickEvidence,
      borderRadius: BorderRadius.circular(24),
      child: Container(
        height: 200,
        width: double.infinity,
        decoration: BoxDecoration(
          color: Colors.black,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: Colors.white.withOpacity(0.1)),
          image: _evidenceBytes != null ? DecorationImage(image: MemoryImage(_evidenceBytes!), fit: BoxFit.contain) : null,
        ),
        child: Stack(
          alignment: Alignment.center,
          children: [
            if (_evidenceBytes == null)
               const Column(
                 mainAxisAlignment: MainAxisAlignment.center,
                 children: [
                   Icon(Icons.add_a_photo_rounded, size: 48, color: Colors.white24),
                   SizedBox(height: 12),
                   Text("TAP TO CAPTURE EVIDENCE", style: TextStyle(color: Colors.white24, fontWeight: FontWeight.bold, fontSize: 10)),
                 ],
               ),
            Positioned(
              bottom: 16,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(12)),
                child: const Row(
                  children: [
                    Icon(Icons.location_on_rounded, size: 14, color: ARGTheme.errorRed),
                    SizedBox(width: 4),
                    Text('GPS LOCKED (28.6139, 77.2090)', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    ).animate().fadeIn().scale();
  }

  Widget _buildFieldLabel(String label) {
    return Text(
      label,
      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.5, color: Colors.white38),
    );
  }

  Widget _buildPlateInput() {
    return TextField(
      controller: _plateController,
      textCapitalization: TextCapitalization.characters,
      decoration: InputDecoration(
        filled: true,
        fillColor: ARGTheme.surface,
        hintText: 'e.g. DL 03 CG 1234',
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
      ),
    );
  }

  Widget _buildTypeDropdown() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(color: ARGTheme.surface, borderRadius: BorderRadius.circular(16)),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: _violationType,
          isExpanded: true,
          onChanged: (val) => setState(() => _violationType = val!),
          items: _types.map((t) => DropdownMenuItem(value: t, child: Text(t))).toList(),
        ),
      ),
    );
  }

  Widget _buildSubmitButton() {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: _isSubmitting ? null : _submit,
        style: ElevatedButton.styleFrom(
          backgroundColor: ARGTheme.primaryBlue,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 20),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
        child: _isSubmitting 
          ? const SizedBox(height: 24, width: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
          : const Text('SUBMIT ENFORCEMENT EVIDENCE', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
    ).animate().fadeIn(delay: 400.ms);
  }
}
