// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:aequitas_roadguard/main.dart';

void main() {
  testWidgets('Aequitas RoadGuard Smoke Test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const MyApp());

    // Verify that the Aequitas Identity/System starts up.
    // We look for 'ROADGUARD' or 'AEQUITAS' which are in our Theme/Splash.
    expect(find.textContaining('AEQUITAS'), findsWidgets);
    
    // Verify that there is No '+' button (proving counter is gone)
    expect(find.byIcon(Icons.add), findsNothing);
  });
}
