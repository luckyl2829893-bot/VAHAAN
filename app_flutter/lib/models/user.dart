class User {
  final int? id;
  final String name;
  final String contactNo;
  final String? professionalId;
  final String role; // 'Citizen', 'Scout', 'Sentinel'
  final String? profileImage;
  
  User({
    this.id,
    required this.name,
    required this.contactNo,
    this.professionalId,
    required this.role,
    this.profileImage,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['user_id'],
      name: json['full_name'] ?? 'Unknown',
      contactNo: json['contact_no'] ?? '',
      professionalId: json['professional_id'],
      role: json['role'] ?? 'Citizen',
      profileImage: json['profile_image'],
    );
  }
}
