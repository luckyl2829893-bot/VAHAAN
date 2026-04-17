import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/vehicle.dart';
import '../models/user.dart';

class APIService {
  // Configured for network access via 192.168.26.89
  static String get baseUrl {
    if (kIsWeb) return 'http://localhost:8000/api';
    if (Platform.isAndroid) return 'http://10.0.2.2:8000/api';
    return 'http://192.168.26.89:8000/api';
  }

  static Future<User?> loginByFace({String? imagePath, Uint8List? bytes}) async {
    try {
      final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/login-by-face'));
      
      if (kIsWeb && bytes != null) {
        request.files.add(http.MultipartFile.fromBytes('face_image', bytes, filename: 'face.png'));
      } else if (imagePath != null) {
        request.files.add(await http.MultipartFile.fromPath('face_image', imagePath));
      }

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return User.fromJson(data['user']);
      }
    } catch (e) {
      print('API Error: $e');
    }
    return null;
  }

  static Future<bool> register({
    required String name,
    required String contact,
    String? profId,
    String? imagePath,
    Uint8List? bytes,
  }) async {
    try {
      final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/register'));
      request.fields['full_name'] = name;
      request.fields['contact_no'] = contact;
      if (profId != null) request.fields['professional_id'] = profId;
      
      if (kIsWeb && bytes != null) {
        request.files.add(http.MultipartFile.fromBytes('face_image', bytes, filename: 'face.png'));
      } else if (imagePath != null) {
        request.files.add(await http.MultipartFile.fromPath('face_image', imagePath));
      }
      
      final streamedResponse = await request.send();
      return streamedResponse.statusCode == 200;
    } catch (e) {
      print('API Error: $e');
      return false;
    }
  }

  static Future<Vehicle?> lookupPlate(String plate) async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/vehicle/$plate'));
      
      if (response.statusCode == 200) {
        return Vehicle.fromJson(json.decode(response.body));
      }
    } catch (e) {
      print('API Error: $e');
    }
    return null;
  }

  static Future<bool> reportViolation({
    required String plate,
    required String type,
    required String evidencePath,
    required double lat,
    required double lng,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/report'),
        body: json.encode({
          'plate': plate,
          'type': type,
          'lat': lat,
          'lng': lng,
          'timestamp': DateTime.now().toIso8601String(),
        }),
        headers: {'Content-Type': 'application/json'},
      );
      return response.statusCode == 200;
    } catch (e) {
      print('API Error: $e');
      return false;
    }
  }

  static Future<List<Map<String, dynamic>>> getChallans(String plate) async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/challans/$plate'));
      
      if (response.statusCode == 200) {
        return List<Map<String, dynamic>>.from(json.decode(response.body));
      }
    } catch (e) {
      print('API Error: $e');
    }
    return [];
  }

  // --- Dual Grading & Sentinel Mind ---

  static Future<Map<String, dynamic>?> getGradingTask() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/grading/task'));
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
    } catch (e) {
      print('API Error: $e');
    }
    return null;
  }

  static Future<bool> skipTask() async {
    try {
      final response = await http.post(Uri.parse('$baseUrl/grading/skip'));
      return response.statusCode == 200;
    } catch (e) {
      print('API Error: $e');
      return false;
    }
  }

  static Future<bool> syncGrading({
    required String filename,
    required Map<String, dynamic> humanInput,
    required Map<String, dynamic> aiPrediction,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/grading/sync'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'filename': filename,
          'human_input': humanInput,
          'ai_prediction': aiPrediction,
        }),
      );
      return response.statusCode == 200;
    } catch (e) {
      print('API Error: $e');
      return false;
    }
  }

  static Future<bool> resetMilestone() async {
    try {
      final response = await http.post(Uri.parse('$baseUrl/sentinel/reset-milestone'));
      return response.statusCode == 200;
    } catch (e) {
      print('API Error: $e');
      return false;
    }
  }

  static Future<Map<String, dynamic>?> getSentinelStatus() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/sentinel/status'));
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
    } catch (e) {
      print('API Error: $e');
    }
    return null;
  }

  static Future<bool> pushBatch(int size) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/sentinel/push-batch'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'batch_size': size}),
      );
      return response.statusCode == 200;
    } catch (e) {
      print('API Error: $e');
      return false;
    }
  }

  static Future<List<Map<String, dynamic>>> getReviewQueue() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/sentinel/review-queue'));
      if (response.statusCode == 200) {
        return List<Map<String, dynamic>>.from(json.decode(response.body));
      }
    } catch (e) {
      print('API Error: $e');
    }
    return [];
  }

  static Future<bool> uploadDoc({
    required String contact,
    required String type,
    String? imagePath,
    Uint8List? bytes,
  }) async {
    try {
      final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/user/upload-doc'));
      request.fields['contact_no'] = contact;
      request.fields['doc_type'] = type;
      
      if (kIsWeb && bytes != null) {
        request.files.add(http.MultipartFile.fromBytes('file', bytes, filename: '$type.png'));
      } else if (imagePath != null) {
        request.files.add(await http.MultipartFile.fromPath('file', imagePath));
      }
      
      final streamedResponse = await request.send();
      return streamedResponse.statusCode == 200;
    } catch (e) {
      print('API Error: $e');
      return false;
    }
  }
}
