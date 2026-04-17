import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'dart:io';
import 'dart:typed_data';
import '../core/theme.dart';
import '../core/api_service.dart';
import '../models/user.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _nameController = TextEditingController();
  final _contactController = TextEditingController();
  final _profIdController = TextEditingController();
  
  CameraController? _cameraController;
  List<CameraDescription>? _cameras;
  File? _faceImage;
  Uint8List? _webImageBytes;
  bool _isLoading = false;
  bool _isCameraReady = false;

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    try {
      _cameras = await availableCameras();
      if (_cameras != null && _cameras!.isNotEmpty) {
        // Find front camera if possible
        final frontCamera = _cameras!.firstWhere(
          (c) => c.lensDirection == CameraLensDirection.front,
          orElse: () => _cameras!.first,
        );
        
        _cameraController = CameraController(
          frontCamera,
          ResolutionPreset.medium,
          enableAudio: false,
        );
        
        await _cameraController!.initialize();
        if (mounted) setState(() => _isCameraReady = true);
      }
    } catch (e) {
      print("Camera Error: $e");
    }
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    super.dispose();
  }

  Future<void> _captureFace() async {
    if (!_isCameraReady || _cameraController == null) return;
    
    try {
      final image = await _cameraController!.takePicture();
      final bytes = await image.readAsBytes();
      
      setState(() {
        _webImageBytes = bytes;
        _faceImage = File(image.path);
      });
    } catch (e) {
      print("Capture Error: $e");
    }
  }

  void _handleLogin() async {
    if (_faceImage == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Face scan is required')),
      );
      return;
    }

    setState(() => _isLoading = true);
    
    try {
      User? user;

      // 1. If fields are empty, try Face-Only identification
      if (_nameController.text.isEmpty && _contactController.text.isEmpty) {
        user = await APIService.loginByFace(
          bytes: _webImageBytes,
          imagePath: _faceImage?.path,
        );
      } 
      // 2. Otherwise try Registration/Normal Login
      else {
        // Try to register first (idempotent)
        await APIService.register(
          name: _nameController.text,
          contact: _contactController.text,
          profId: _profIdController.text,
          bytes: _webImageBytes,
          imagePath: _faceImage?.path,
        );
        user = await APIService.loginByFace(
          bytes: _webImageBytes,
          imagePath: _faceImage?.path,
        );
      }
      
      setState(() => _isLoading = false);

      if (user != null && mounted) {
        context.go('/home');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Identity not recognized. Please fill in details to register.')),
        );
      }
    } catch (e) {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ARGTheme.darkBg,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 40),
              const Icon(Icons.shield_rounded, color: ARGTheme.primaryBlue, size: 80)
                  .animate()
                  .scale(duration: 600.ms, curve: Curves.bounceOut),
              const SizedBox(height: 24),
              Text(
                'VAHAAN',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
              ),
              const Text(
                'Identity & Security Portal',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white60),
              ),
              const SizedBox(height: 60),
              _buildTextField('Full Name', _nameController, Icons.person_rounded),
              const SizedBox(height: 20),
              _buildTextField('Contact Number', _contactController, Icons.phone_android_rounded),
              const SizedBox(height: 20),
              _buildTextField('Professional ID (Optional)', _profIdController, Icons.badge_rounded),
              const SizedBox(height: 40),
              const Text(
                '🔒 LIVE SCANNER (SCAN YOUR FACE)',
                style: TextStyle(color: ARGTheme.primaryBlue, fontWeight: FontWeight.bold, fontSize: 12),
              ),
              const SizedBox(height: 16),
              GestureDetector(
                onTap: _captureFace,
                child: Container(
                  height: 400, // Increased height for vertical orientation
                  decoration: BoxDecoration(
                    color: Colors.black,
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(color: ARGTheme.primaryBlue.withOpacity(0.5), width: 2),
                    boxShadow: [
                      BoxShadow(color: ARGTheme.primaryBlue.withOpacity(0.2), blurRadius: 20, spreadRadius: 2),
                    ],
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(22),
                    child: _faceImage != null
                        ? kIsWeb 
                            ? Image.memory(_webImageBytes!, fit: BoxFit.cover)
                            : Image.file(_faceImage!, fit: BoxFit.cover)
                        : _isCameraReady 
                            ? Stack(
                                fit: StackFit.expand,
                                children: [
                                  // Use AspectRatio to prevent stretching
                                  Center(
                                    child: AspectRatio(
                                      aspectRatio: _cameraController!.value.aspectRatio,
                                      child: CameraPreview(_cameraController!),
                                    ),
                                  ),
                                  // Scanning UI overlays...
                                  Center(
                                    child: Container(
                                      width: 250,
                                      height: 320,
                                      decoration: BoxDecoration(
                                        border: Border.all(color: ARGTheme.primaryBlue.withOpacity(0.5), width: 1),
                                        borderRadius: BorderRadius.circular(20),
                                      ),
                                    ),
                                  ),
                                  Center(
                                    child: const Icon(Icons.face_retouching_natural, color: Colors.white12, size: 80),
                                  ),
                                  Positioned(
                                    bottom: 20,
                                    left: 0, right: 0,
                                    child: Center(
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                        decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(20)),
                                        child: const Text('TAP TO SCAN', style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)),
                                      ),
                                    ),
                                  ),
                                ],
                              )
                            : const Center(child: CircularProgressIndicator(color: ARGTheme.primaryBlue)),
                  ),
                ),
              ),
              const SizedBox(height: 40),
              ElevatedButton(
                onPressed: _isLoading ? null : _handleLogin,
                style: ElevatedButton.styleFrom(
                  backgroundColor: ARGTheme.primaryBlue,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 18),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                ),
                child: _isLoading
                    ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : const Text('PROCEED TO APP', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTextField(String label, TextEditingController controller, IconData icon) {
    return TextField(
      controller: controller,
      style: const TextStyle(color: Colors.white),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: const TextStyle(color: Colors.white60),
        prefixIcon: Icon(icon, color: ARGTheme.primaryBlue),
        filled: true,
        fillColor: Colors.white.withOpacity(0.05),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(20), borderSide: BorderSide.none),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(20), borderSide: const BorderSide(color: ARGTheme.primaryBlue)),
      ),
    );
  }
}
