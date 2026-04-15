import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/vehicle.dart';
import '../models/user.dart';

class APIService {
  // Configured for network access via 192.168.26.89
  static String get baseUrl {
    if (!kIsWeb && Platform.isAndroid) return 'http://10.0.2.2:8000/api';
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
}
