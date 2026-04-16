import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class ARGTheme {
  // --- Legacy Colors (Restored to fix UI) ---
  static const Color primaryBlue = Color(0xFF3B82F6);
  static const Color accentAmber = Color(0xFFF59E0B);
  static const Color successGreen = Color(0xFF10B981);
  static const Color errorRed = Color(0xFFEF4444);
  static const Color surface = Color(0xFF1E293B);

  // --- Core Colors ---
  static const Color electricBlue = Color(0xFF2563EB);
  static const Color darkBg = Color(0xFF0A1628);
  static const Color lightBg = Color(0xFFF8FAFC);

  // --- v12 Status Palette (Formalized) ---
  static const Color statusGreen = Color(0xFF22C55E);   // Elite / Healthy
  static const Color statusYellow = Color(0xFFFBBF24);  // Caution
  static const Color statusOrange = Color(0xFFF97316);  // Warning
  static const Color statusRed = Color(0xFFEF4444);     // Danger / Red Card

  // --- Merit Palette ---
  static const Color ghpGreen = Color(0xFF22C55E);      
  static const Color meritGold = Color(0xFFFBBF24);     
  static const Color harmonyTeal = Color(0xFF06B6D4);   
  static const Color redCard = Color(0xFFEF4444);       

  // --- DARK THEME (Glassmorphism) ---
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: darkBg,
      primaryColor: primaryBlue,
      colorScheme: ColorScheme.fromSeed(seedColor: primaryBlue, brightness: Brightness.dark, primary: primaryBlue, secondary: statusYellow, surface: surface),
      textTheme: GoogleFonts.outfitTextTheme(ThemeData.dark().textTheme),
      cardTheme: CardThemeData(
        color: surface.withOpacity(0.8),
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24), side: BorderSide(color: Colors.white.withOpacity(0.1))),
      ),
    );
  }

  // --- LIGHT THEME (Punchy & Colorful) ---
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: lightBg,
      primaryColor: electricBlue,
      colorScheme: ColorScheme.fromSeed(seedColor: electricBlue, brightness: Brightness.light, primary: electricBlue, secondary: const Color(0xFF8B5CF6), surface: Colors.white),
      textTheme: GoogleFonts.outfitTextTheme(ThemeData.light().textTheme).copyWith(
        displayLarge: GoogleFonts.outfit(fontSize: 32, fontWeight: FontWeight.w900, color: const Color(0xFF1E293B)),
        titleLarge: GoogleFonts.outfit(fontSize: 22, fontWeight: FontWeight.bold, color: const Color(0xFF1E293B)),
      ),
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 12,
        shadowColor: electricBlue.withOpacity(0.2),
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(24), 
            side: BorderSide(color: electricBlue.withOpacity(0.1), width: 2)
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: electricBlue,
          foregroundColor: Colors.white,
          elevation: 6,
          shadowColor: electricBlue.withOpacity(0.4),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          padding: const EdgeInsets.symmetric(vertical: 18),
        ),
      ),
    );
  }
}
