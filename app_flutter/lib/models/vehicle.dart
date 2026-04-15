class Vehicle {
  final String plateNumber;
  final String vehicleClass;
  final String make;
  final String model;
  final String color;
  final String fuelType;
  final double invoicePrice;
  final String ownerName;
  final String insuranceCompany;
  final DateTime insuranceExpiry;
  final double wealthMultiplier;
  final double walletBalance;

  Vehicle({
    required this.plateNumber,
    required this.vehicleClass,
    required this.make,
    required this.model,
    required this.color,
    required this.fuelType,
    required this.invoicePrice,
    required this.ownerName,
    required this.insuranceCompany,
    required this.insuranceExpiry,
    required this.wealthMultiplier,
    required this.walletBalance,
  });

  factory Vehicle.fromJson(Map<String, dynamic> json) {
    return Vehicle(
      plateNumber: json['plate_number'] ?? '',
      vehicleClass: json['vehicle_class'] ?? '',
      make: json['make'] ?? '',
      model: json['model'] ?? '',
      color: json['color'] ?? '',
      fuelType: json['fuel_type'] ?? '',
      invoicePrice: (json['invoice_price'] ?? 0).toDouble(),
      ownerName: json['full_name'] ?? 'Unknown Owner',
      insuranceCompany: json['insurance_company'] ?? '',
      insuranceExpiry: DateTime.tryParse(json['insurance_expiry'] ?? '') ?? DateTime.now(),
      wealthMultiplier: (json['wealth_multiplier'] ?? 1.0).toDouble(),
      walletBalance: (json['wallet_balance'] ?? 0).toDouble(),
    );
  }
}
