# Aequitas RoadGuard - Developer Implementation Log
**Date: 2026-04-15**

## 1. Biometric Engine Optimization
*   **Issue**: Face recognition was failing due to aggressive cropping and strict thresholds (88%).
*   **Root Cause**: The default `CenterCrop(224)` was cutting off faces in webcam streams, and cosine similarity with a generic ResNet-18 model required a more forgiving threshold for varied lighting.
*   **Fix**: 
    *   Updated `FaceEngine` to use `Resize((224, 224))` to maintain entire face visibility.
    *   Lowered global threshold to **0.70**.
    *   Added **Biometric Debug Logging** in the backend to print real-time confidence scores for precise tuning.

## 2. Flutter Web Compatibility Overhaul
*   **Issue 1: Platform Crash**: The app crashed with `Unsupported operation: Platform._operatingSystem`.
    *   **Fix**: Replaced direct `Platform` checks with `kIsWeb` flags from `package:flutter/foundation.dart`.
*   **Issue 2: Multipart Upload Crash**: Received `Unsupported operation: MultipartFile is only supported where dart:io is available`.
    *   **Fix**: Browsers cannot access local file paths. Rewrote `APIService` and `LoginScreen` to capture and transmit **Raw Binary Bytes** (`Uint8List`) using `http.MultipartFile.fromBytes`.

## 3. System Architecture: RoadGuard V2
*   **Role-Based Access**: Bypassed strict login gates to provide the creator with a "God View" Operations Hub.
*   **Enforcement Hub**:
    *   Implemented **Equity-Based Fine Logic**: `Base Fine x (Car Value Multiplier)`.
    *   Added **Patrol Intelligence**: Live violation heatmap and "Critical Wanted List" for officers.
    *   Added **AI Override**: Officers can manually correct car model detections before issuing challans.
*   **Sentinel Mind (Admin)**:
    *   **Annotation Engine**: Created a management console to push "Low Confidence" images to the citizen pool.
    *   **Economic Formula**: Added a slider for "Equity Sensitivity" to control wealth-based fine disparity.

## 4. Crowdsourced Intelligence (Bounty Hunter)
*   **Innovation**: Integrated a gamified "Bounty Hunter" mode for Citizens.
*   **Mechanism**: Citizens earn rewards (RoadGuard Coins) for accurately labeling car brands and models, providing a massive human-verified dataset for continuous AI retraining.

## 5. Cross-Platform Networking
*   **Setup**: Configured the ecosystem for local network deployment.
*   **Network Fix**: Updated `APIService` to use the laptop's local IP (`192.168.26.89`) and configured both Uvicorn and Flutter to listen on `0.0.0.0` for smartphone access.
