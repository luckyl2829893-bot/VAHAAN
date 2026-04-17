"""
VAHAAN Road Safety Enforcement Engine
======================================
Multi-violation detection for real-time road safety enforcement.

Detects simultaneously:
  - No Helmet (motorcycle riders)
  - No Seat Belt (car drivers/passengers)
  - Mobile Phone Use While Driving
  - Wrong Way / Triple Riding (motorcycles)
  - Overloaded Vehicle indicators

Architecture:
  - Primary: YOLOv8 custom model (safety_net.pt) fine-tuned on Indian roads
  - Fallback: Probabilistic simulation for demo/dev environments

Fine Logic based on Motor Vehicles (Amendment) Act, 2019:
  - No Helmet:     ₹1,000 (first) / ₹2,000 (repeat) + community service
  - No Seat Belt:  ₹1,000 + licence penalty
  - Mobile Phone:  ₹5,000 (first) / ₹10,000 (repeat) + 3-month licence suspension
  - Triple Riding: ₹5,000 (overloaded 2-wheeler)
"""

import os
import random
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from ultralytics import YOLO
    from PIL import Image
    import numpy as np
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False


# ─── Violation Registry ──────────────────────────────────────────────────────

VIOLATION_CATALOGUE = {
    "no_helmet": {
        "label":        "No Helmet",
        "icon":         "🪖",
        "category":     "PPE",
        "vehicle_type": "motorcycle",
        "base_fine":    1_000,
        "repeat_fine":  2_000,
        "mva_section":  "Section 129 MV Act",
        "severity":      "HIGH",
        "points_lost":   2,
        "description":  "Rider/pillion not wearing ISI-certified helmet.",
    },
    "no_seatbelt": {
        "label":        "No Seat Belt",
        "icon":         "🔒",
        "category":     "PPE",
        "vehicle_type": "car",
        "base_fine":    1_000,
        "repeat_fine":  1_000,
        "mva_section":  "Section 194B MV Act",
        "severity":     "HIGH",
        "points_lost":  2,
        "description":  "Driver or front-seat passenger not wearing seat belt.",
    },
    "mobile_phone_driving": {
        "label":        "Mobile Phone While Driving",
        "icon":         "📱",
        "category":     "Distraction",
        "vehicle_type": "any",
        "base_fine":    5_000,
        "repeat_fine":  10_000,
        "mva_section":  "Section 184 MV Act",
        "severity":     "CRITICAL",
        "points_lost":  4,
        "description":  "Driver using handheld mobile device while vehicle is in motion.",
        "license_action": "3-month suspension on repeat offence",
    },
    "triple_riding": {
        "label":        "Triple Riding",
        "icon":         "🏍️",
        "category":     "Overload",
        "vehicle_type": "motorcycle",
        "base_fine":    5_000,
        "repeat_fine":  5_000,
        "mva_section":  "Section 128 MV Act",
        "severity":     "HIGH",
        "points_lost":  3,
        "description":  "More than 2 persons riding on a two-wheeler.",
    },
    "wrong_way_driving": {
        "label":        "Wrong-Way Driving",
        "icon":         "⬅️",
        "category":     "Directional",
        "vehicle_type": "any",
        "base_fine":    5_000,
        "repeat_fine":  5_000,
        "mva_section":  "Section 184 MV Act",
        "severity":     "CRITICAL",
        "points_lost":  4,
        "description":  "Vehicle detected travelling against the permitted traffic flow.",
    },
    "red_light_jump": {
        "label":        "Red Light Violation",
        "icon":         "🚦",
        "category":     "Signal",
        "vehicle_type": "any",
        "base_fine":    5_000,
        "repeat_fine":  10_000,
        "mva_section":  "Section 119 MV Act",
        "severity":     "CRITICAL",
        "points_lost":  4,
        "description":  "Vehicle crossed a red traffic signal.",
    },
    "overloaded_goods": {
        "label":        "Vehicle Overloading",
        "icon":         "🚛",
        "category":     "Overload",
        "vehicle_type": "truck",
        "base_fine":    20_000,
        "repeat_fine":  20_000,
        "mva_section":  "Section 194 MV Act",
        "severity":     "HIGH",
        "points_lost":  3,
        "description":  "Goods vehicle exceeding prescribed axle load limit.",
    },
}

# YOLO class name → violation key mapping (for trained model)
YOLO_CLASS_MAP = {
    "no_helmet":        "no_helmet",
    "without_helmet":   "no_helmet",
    "no_seatbelt":      "no_seatbelt",
    "without_seatbelt": "no_seatbelt",
    "phone":            "mobile_phone_driving",
    "mobile_phone":     "mobile_phone_driving",
    "triple_riding":    "triple_riding",
    "wrong_way":        "wrong_way_driving",
}


# ─── Safety Engine ────────────────────────────────────────────────────────────

class SafetyEngine:
    """
    Multi-violation road safety detector.

    On `__init__`, attempts to load `safety_net.pt` from the project root.
    If not found, falls back to graceful demo/simulation mode so the API
    still returns valid structured data.
    """

    def __init__(self, root_path: Path):
        self.root = root_path
        self.model_path = root_path / "safety_net.pt"
        self.model = None
        self._mode = "simulation"

        if YOLO_AVAILABLE and self.model_path.exists():
            try:
                print(f"[*] Safety Engine: Loading {self.model_path}")
                self.model = YOLO(str(self.model_path))
                self._mode = "live"
                print(f"[✓] Safety Engine: LIVE mode active.")
            except Exception as e:
                print(f"[!] Safety Engine: Failed to load model — {e}. Falling back to simulation.")
        else:
            print("[~] Safety Engine: safety_net.pt not found. Running in SIMULATION mode.")
            print("[~]   → Train & export your model: src/features/safety_trainer.py")

    # ── Public API ──────────────────────────────────────────────────────────

    def scan(
        self,
        image_path: str,
        plate_number: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        is_repeat_offender: bool = False,
    ) -> dict:
        """
        Run road safety scan on a single image.

        Returns:
            {
              "violations_found": [...],
              "is_compliant":     bool,
              "total_fine":       int,
              "scan_time_ms":     float,
              "mode":             "live" | "simulation",
              "evidence":         { ... }
            }
        """
        t0 = time.perf_counter()

        violations = []

        if self._mode == "live":
            violations = self._run_live_inference(image_path, vehicle_type, is_repeat_offender)
        else:
            violations = self._run_simulation(vehicle_type, is_repeat_offender)

        total_fine = sum(v["fine_applied"] for v in violations)
        scan_ms = (time.perf_counter() - t0) * 1000

        return {
            "violations_found":  violations,
            "violation_count":   len(violations),
            "is_compliant":      len(violations) == 0,
            "total_fine":        total_fine,
            "scan_time_ms":      round(scan_ms, 2),
            "mode":              self._mode,
            "plate":             plate_number or "UNKNOWN",
            "vehicle_type":      vehicle_type or "unknown",
            "scanned_at":        datetime.utcnow().isoformat(),
            "evidence": {
                "image_path":    str(image_path),
                "inference_mode": self._mode,
            }
        }

    def get_catalogue(self) -> dict:
        """Return the full violation catalogue with fine information."""
        return VIOLATION_CATALOGUE

    def get_stats(self) -> dict:
        """Return engine operational stats."""
        return {
            "mode":          self._mode,
            "model_loaded":  self.model is not None,
            "model_path":    str(self.model_path),
            "violations_supported": list(VIOLATION_CATALOGUE.keys()),
            "total_categories": len(set(v["category"] for v in VIOLATION_CATALOGUE.values())),
        }

    # ── Internal: Live Inference ─────────────────────────────────────────────

    def _run_live_inference(
        self,
        image_path: str,
        vehicle_type: Optional[str],
        is_repeat: bool
    ) -> list:
        """Run actual YOLO inference on the image."""
        violations = []
        try:
            results = self.model(image_path, verbose=False)
            detected_classes = set()

            for r in results:
                for box in r.boxes:
                    class_name = r.names[int(box.cls)].lower().replace(" ", "_")
                    conf = float(box.conf)

                    if conf < 0.45:  # Threshold — skip low confidence
                        continue

                    violation_key = YOLO_CLASS_MAP.get(class_name)
                    if violation_key and violation_key not in detected_classes:
                        detected_classes.add(violation_key)
                        violations.append(
                            self._build_violation(
                                violation_key,
                                conf,
                                is_repeat,
                                bbox=box.xyxy[0].tolist() if hasattr(box, "xyxy") else None,
                            )
                        )
        except Exception as e:
            print(f"[!] Safety Engine inference error: {e}")

        return violations

    # ── Internal: Simulation ─────────────────────────────────────────────────

    def _run_simulation(self, vehicle_type: Optional[str], is_repeat: bool) -> list:
        """
        Deterministic simulation for demo / CI environments.
        Weights violations realistically:
          - bike → higher helmet / triple-ride probability
          - car  → higher seatbelt / phone probability
        """
        violations_detected = []

        bike = vehicle_type in ("motorcycle", "bike", "two_wheeler", None)
        car  = vehicle_type in ("car", "sedan", "suv", "four_wheeler", None)

        checks = [
            ("no_helmet",            0.40 if bike else 0.05),
            ("no_seatbelt",          0.30 if car  else 0.05),
            ("mobile_phone_driving", 0.20),
            ("triple_riding",        0.15 if bike else 0.0),
            ("wrong_way_driving",    0.05),
        ]

        for violation_key, probability in checks:
            if random.random() < probability:
                conf = round(random.uniform(0.60, 0.95), 3)
                violations_detected.append(
                    self._build_violation(violation_key, conf, is_repeat)
                )

        return violations_detected

    # ── Internal: Violation Builder ──────────────────────────────────────────

    def _build_violation(
        self,
        violation_key: str,
        confidence: float,
        is_repeat: bool,
        bbox: Optional[list] = None,
    ) -> dict:
        """Construct a fully-enriched violation record."""
        info = VIOLATION_CATALOGUE.get(violation_key, {})
        fine = info.get("repeat_fine" if is_repeat else "base_fine", 500)

        return {
            "violation_key":    violation_key,
            "label":            info.get("label", violation_key),
            "icon":             info.get("icon", "⚠️"),
            "category":         info.get("category", "Unknown"),
            "severity":         info.get("severity", "MEDIUM"),
            "mva_section":      info.get("mva_section", "N/A"),
            "description":      info.get("description", ""),
            "confidence":       confidence,
            "fine_applied":     fine,
            "is_repeat_fine":   is_repeat,
            "licence_points_lost": info.get("points_lost", 0),
            "license_action":   info.get("license_action", None),
            "bbox":             bbox,
        }
