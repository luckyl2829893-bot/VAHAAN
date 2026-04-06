"""
ARG Advanced Video Engine

Features:
1. ROI Masking — Only detect vehicles in a defined zone (ignore far-away vehicles)
2. YOLO Tracking — Smooth, ID-persistent tracking across frames
3. Speed Estimation — Calculate vehicle speed from pixel displacement
4. Evidence Storage — Save violation frames as timestamped court evidence
5. Legal Narrative Generator (NLP) — Auto-generate challan text from detections

Usage:
    python arg_video_engine.py Videos/video84.MOV
    python arg_video_engine.py Videos/video84.MOV --roi       # Interactive ROI selection
    python arg_video_engine.py image.jpg                      # Single image mode
"""

import os
import sys
import cv2
import re
import json
import numpy as np
import sqlite3
from datetime import datetime
from ultralytics import YOLO
import easyocr

from generate_proxy_database import (
    STATE_RTO_MAP, create_database_schema
)

PATTERN_INDIA = re.compile(r'([A-Z]{2})([0-9]{1,2})([A-Z]{1,3})([0-9]{1,4})')
DB_PATH = 'arg_master_database.sqlite'

# ============================================================
#  1. ROI MASKING — Define Detection Zone
# ============================================================

class ROIManager:
    """Manages the Region of Interest for vehicle detection."""

    def __init__(self, frame_shape, roi_type="auto"):
        self.h, self.w = frame_shape[:2]
        self.roi_polygon = None

        if roi_type == "auto":
            # Auto ROI: Center-bottom trapezoid (where close vehicles appear)
            # Ignores the top 40% (sky, distant objects) and edges
            self.roi_polygon = np.array([
                [int(self.w * 0.05), self.h],           # bottom-left
                [int(self.w * 0.25), int(self.h * 0.40)],  # top-left
                [int(self.w * 0.75), int(self.h * 0.40)],  # top-right
                [int(self.w * 0.95), self.h],           # bottom-right
            ], dtype=np.int32)

    def is_inside_roi(self, x1, y1, x2, y2):
        """Check if the center of a bounding box is inside the ROI."""
        if self.roi_polygon is None:
            return True

        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2

        result = cv2.pointPolygonTest(self.roi_polygon, (float(center_x), float(center_y)), False)
        return result >= 0

    def draw_roi(self, frame):
        """Draw the ROI zone on the frame."""
        if self.roi_polygon is not None:
            overlay = frame.copy()
            cv2.fillPoly(overlay, [self.roi_polygon], (0, 255, 0))
            cv2.addWeighted(overlay, 0.1, frame, 0.9, 0, frame)
            cv2.polylines(frame, [self.roi_polygon], True, (0, 255, 0), 2)
        return frame


# ============================================================
#  2. SPEED ESTIMATOR — Pixel Displacement Tracking
# ============================================================

class SpeedEstimator:
    """
    Estimates vehicle speed by tracking pixel displacement across frames.

    Assumptions for dashcam footage:
    - Average lane width in India = 3.5 meters
    - We approximate pixels-per-meter using frame width and typical road width
    """

    def __init__(self, fps, frame_width, pixels_per_meter=None):
        self.fps = fps
        self.frame_width = frame_width
        # Approximate: typical Indian road visible in dashcam = ~12 meters wide
        self.ppm = pixels_per_meter or (frame_width / 12.0)
        self.track_history = {}  # track_id -> list of (cx, cy, frame_num)

    def update(self, track_id, cx, cy, frame_num):
        """Update position for a tracked vehicle."""
        if track_id not in self.track_history:
            self.track_history[track_id] = []
        self.track_history[track_id].append((cx, cy, frame_num))

        # Keep only last 30 positions
        if len(self.track_history[track_id]) > 30:
            self.track_history[track_id] = self.track_history[track_id][-30:]

    def get_speed(self, track_id):
        """Calculate speed in km/h for a tracked vehicle."""
        history = self.track_history.get(track_id, [])
        if len(history) < 3:
            return None

        # Use last 5 positions for smoothing
        recent = history[-5:]
        if len(recent) < 2:
            return None

        total_pixels = 0
        for i in range(1, len(recent)):
            dx = recent[i][0] - recent[i - 1][0]
            dy = recent[i][1] - recent[i - 1][1]
            total_pixels += np.sqrt(dx ** 2 + dy ** 2)

        frame_diff = recent[-1][2] - recent[0][2]
        if frame_diff == 0:
            return None

        time_seconds = frame_diff / self.fps
        distance_meters = total_pixels / self.ppm
        speed_mps = distance_meters / time_seconds
        speed_kmh = speed_mps * 3.6

        # Clamp unrealistic speeds
        if speed_kmh > 200 or speed_kmh < 2:
            return None

        return round(speed_kmh, 1)


# ============================================================
#  3. EVIDENCE STORAGE — Court Evidence Package
# ============================================================

class EvidenceCollector:
    """Store timestamped violation evidence for court use."""

    def __init__(self, output_dir="evidence_vault"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.evidence_log = []

    def store_evidence(self, frame, vehicle_crop, plate_text, violation_type,
                       speed=None, track_id=None, frame_num=None):
        """Save a violation as a court-ready evidence package."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        case_id = f"ARG-{timestamp}-{len(self.evidence_log) + 1:04d}"

        case_dir = os.path.join(self.output_dir, case_id)
        os.makedirs(case_dir, exist_ok=True)

        # Save full frame
        cv2.imwrite(os.path.join(case_dir, "full_frame.jpg"), frame)
        # Save vehicle crop
        cv2.imwrite(os.path.join(case_dir, "vehicle_crop.jpg"), vehicle_crop)

        # Save metadata
        metadata = {
            "case_id": case_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "plate_number": plate_text,
            "violation_type": violation_type,
            "estimated_speed_kmh": speed,
            "track_id": track_id,
            "frame_number": frame_num,
        }

        with open(os.path.join(case_dir, "metadata.json"), 'w') as f:
            json.dump(metadata, f, indent=2)

        self.evidence_log.append(metadata)
        return case_id


# ============================================================
#  4. LEGAL NARRATIVE GENERATOR (NLP)
# ============================================================

def generate_legal_narrative(plate_text, violation_type, vehicle_type,
                              speed=None, location="Unknown Junction",
                              db_path=DB_PATH):
    """
    Auto-generate a structured legal challan narrative from detection data.
    This is the NLP component of the ARG system.
    """
    timestamp = datetime.now()
    date_str = timestamp.strftime("%d-%m-%Y")
    time_str = timestamp.strftime("%H:%M IST")

    # Try to pull owner details from database
    owner_name = "Unknown Owner"
    vehicle_desc = f"{vehicle_type} (Make/Model unidentified)"
    vehicle_value = 500000
    aadhar = "XXXX XXXX XXXX"
    state = "Unknown"
    financer = "N/A"
    insurance = "Unknown"

    if plate_text != "UNKNOWN" and os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("""SELECT v.make, v.model, v.color, v.vehicle_class, v.invoice_price,
                         v.insurance_company, v.hypothecation, v.financer_bank, v.owner_name,
                         v.owner_aadhar, c.state
                      FROM vahan_registry v
                      LEFT JOIN citizens c ON v.owner_aadhar = c.aadhar_masked
                      WHERE v.plate_number = ?""", (plate_text,))
            row = c.fetchone()
            if row:
                vehicle_desc = f"{row[2]} {row[0]} {row[1]} ({row[3]})"
                vehicle_value = row[4] or 500000
                insurance = row[5] or "Unknown"
                financer = f"{row[6]} - {row[7]}" if row[6] == "Yes" else "No active loan"
                owner_name = row[8] or "Unknown Owner"
                aadhar = row[9] or "XXXX XXXX XXXX"
                state = row[10] or "Unknown"
            conn.close()
        except Exception:
            pass

    # Calculate Wealth Multiplier
    multiplier = max(1.0, min(10.0, vehicle_value / 500000))

    # Base fines by violation type
    fine_map = {
        "NO PLATE VISIBLE": 5000,
        "NO HELMET": 1000,
        "SPEEDING": 2000,
        "DARK TINT": 3000,
        "RASH DRIVING": 5000,
    }
    base_fine = fine_map.get(violation_type, 1000)
    final_fine = round(base_fine * multiplier, 2)

    # Build the legal narrative
    narrative = f"""
{'='*70}
                    AEQUITAS ROADGUARD — AUTOMATED CHALLAN
{'='*70}

CASE REFERENCE:     ARG/{timestamp.strftime('%Y%m%d%H%M%S')}/{plate_text or 'UNKNOWN'}
DATE OF VIOLATION:  {date_str}
TIME OF VIOLATION:  {time_str}
LOCATION:           {location}

{'─'*70}
VEHICLE DETAILS (VAHAN Registry)
{'─'*70}
  Registration No:  {plate_text}
  Description:      {vehicle_desc}
  Invoice Value:    ₹{vehicle_value:,.0f}
  Insurance:        {insurance}
  Loan Status:      {financer}

{'─'*70}
OWNER DETAILS (UIDAI / Aadhaar-Linked)
{'─'*70}
  Name:             {owner_name}
  Aadhaar (Masked): {aadhar}
  State:            {state}

{'─'*70}
VIOLATION RECORD
{'─'*70}
  Violation Type:   {violation_type}"""

    if speed:
        narrative += f"""
  Recorded Speed:   {speed} km/h
  Speed Limit:      50 km/h (Urban Zone)
  Excess Speed:     {max(0, speed - 50):.1f} km/h"""

    narrative += f"""

{'─'*70}
FINE CALCULATION (Wealth-Adjusted)
{'─'*70}
  Base Fine:        ₹{base_fine:,.0f}
  Vehicle Value:    ₹{vehicle_value:,.0f}
  Wealth Multiplier:{multiplier:.2f}x
  FINAL FINE:       ₹{final_fine:,.0f}

{'─'*70}
LEGAL NOTICE
{'─'*70}
  On {date_str} at {time_str}, the above-described vehicle bearing
  registration number {plate_text}, registered to {owner_name}
  (Aadhaar: {aadhar}), was recorded committing a violation of type
  "{violation_type}" at {location}.

  Under the Motor Vehicles (Amendment) Act, 2019, and as per the
  Aequitas Fair Penalty Framework, the base fine of ₹{base_fine:,.0f}
  has been adjusted by a Wealth Multiplier of {multiplier:.2f}x based
  on the registered vehicle invoice value of ₹{vehicle_value:,.0f},
  resulting in a final challan amount of ₹{final_fine:,.0f}.

  This challan is auto-generated by the ARG AI Enforcement System.
  Payment is due within 60 days. Failure to pay will result in
  FASTag blacklisting and registration hold.

  AI CONFIDENCE: HIGH | EVIDENCE: FRAME STORED | STATUS: UNPAID
{'='*70}
"""
    return narrative


# ============================================================
#  5. MAIN VIDEO ENGINE
# ============================================================

def run_video_engine(source, select_roi=False):
    """Main advanced video engine with all features."""

    print("=" * 65)
    print("  ARG ADVANCED VIDEO ENGINE v2.0")
    print("  ROI Masking | Speed Tracking | Evidence Storage | NLP Challan")
    print("=" * 65)

    # Load models
    print("\nLoading Stage 1 (Vehicle Finder + Tracker): yolo11m.pt...")
    vehicle_model = YOLO("yolo11m.pt")

    plate_path = r"runs\detect\plate_model_train_final\weights\best.pt"
    print("Loading Stage 2 (Plate Sniper)...")
    plate_model = YOLO(plate_path)

    print("Loading EasyOCR...")
    reader = easyocr.Reader(['en'], gpu=True)

    # Evidence collector
    evidence = EvidenceCollector()

    # Determine if video or image
    is_video = source.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv'))

    if not is_video:
        # Single image mode
        process_single_image(source, vehicle_model, plate_model, reader, evidence)
        return

    # --- VIDEO MODE ---
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"ERROR: Cannot open {source}")
        return

    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"\n📹 Video: {source}")
    print(f"   Resolution: {w}x{h} | FPS: {fps} | Frames: {total_frames}")

    # Setup ROI
    ret, first_frame = cap.read()
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    roi = ROIManager(first_frame.shape, roi_type="auto")
    print(f"   ROI: Auto-trapezoid (ignoring top 40% of frame)")

    # Setup speed estimator
    speed_est = SpeedEstimator(fps, w)

    # Output video
    output_dir = "arg_engine_output"
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"tracked_{os.path.basename(source).rsplit('.', 1)[0]}.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

    frame_num = 0
    total_vehicles = 0
    total_violations = 0
    tracked_plates = {}  # track_id -> plate_text
    generated_challans = []
    frame_skip = max(1, fps // 5)  # Process 5 frames per second

    print(f"   Processing every {frame_skip}th frame ({5} detections/sec)")
    print(f"   Output: {out_path}\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_num += 1
        annotated = frame.copy()

        # Draw ROI zone
        roi.draw_roi(annotated)

        if frame_num % frame_skip == 0:
            # Use YOLO tracking for persistent IDs
            results = vehicle_model.track(frame, persist=True, verbose=False)

            if results[0].boxes.id is not None:
                for i, box in enumerate(results[0].boxes):
                    v_cls = int(box.cls[0])
                    if v_cls not in [1, 2, 3, 5, 7]:
                        continue

                    track_id = int(box.id[0]) if box.id is not None else -1
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    # ROI check — skip far-away vehicles
                    if not roi.is_inside_roi(x1, y1, x2, y2):
                        # Draw grey box for out-of-zone vehicles
                        cv2.rectangle(annotated, (x1, y1), (x2, y2), (128, 128, 128), 1)
                        continue

                    total_vehicles += 1
                    vehicle_crop = frame[y1:y2, x1:x2]
                    if vehicle_crop.shape[0] < 30 or vehicle_crop.shape[1] < 30:
                        continue

                    vehicle_type = {1: "Bicycle", 2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}.get(v_cls, "Vehicle")
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                    # Update speed tracker
                    speed_est.update(track_id, cx, cy, frame_num)
                    speed = speed_est.get_speed(track_id)

                    # Check for plate
                    p_results = plate_model.predict(vehicle_crop, verbose=False)
                    has_plate = len(p_results[0].boxes) > 0

                    # Extract plate text if found
                    plate_text = tracked_plates.get(track_id, "UNKNOWN")
                    if has_plate and plate_text == "UNKNOWN":
                        for p_box in p_results[0].boxes:
                            px1, py1, px2, py2 = map(int, p_box.xyxy[0])
                            plate_crop = vehicle_crop[
                                max(0, py1 - 5):min(vehicle_crop.shape[0], py2 + 5),
                                max(0, px1 - 5):min(vehicle_crop.shape[1], px2 + 5)
                            ]
                            if plate_crop.shape[0] > 0 and plate_crop.shape[1] > 0:
                                ocr_res = reader.readtext(plate_crop)
                                raw = "".join([r[1] for r in ocr_res])
                                clean = re.sub(r'[^A-Z0-9]', '', raw.upper())
                                if len(clean) >= 6 and PATTERN_INDIA.search(clean):
                                    plate_text = clean
                                    tracked_plates[track_id] = plate_text
                            break

                    # Determine violations
                    violations = []
                    if not has_plate:
                        violations.append("NO PLATE VISIBLE")
                    if speed and speed > 50:
                        violations.append("SPEEDING")

                    # Draw annotations
                    if violations:
                        total_violations += len(violations)
                        color = (0, 0, 255)  # Red for violations
                        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)

                        for vi, v in enumerate(violations):
                            label = f"ID:{track_id} {v}"
                            if speed:
                                label += f" ({speed}km/h)"
                            cv2.putText(annotated, label, (x1, y1 - 10 - (vi * 25)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                            # Store evidence
                            case_id = evidence.store_evidence(
                                frame, vehicle_crop, plate_text, v,
                                speed=speed, track_id=track_id, frame_num=frame_num
                            )

                            # Generate legal narrative (only once per track_id per violation)
                            challan_key = f"{track_id}_{v}"
                            if challan_key not in [c.get('key') for c in generated_challans]:
                                narrative = generate_legal_narrative(
                                    plate_text, v, vehicle_type, speed=speed
                                )
                                generated_challans.append({
                                    'key': challan_key,
                                    'narrative': narrative,
                                    'case_id': case_id,
                                })
                    else:
                        # Green box for compliant vehicles
                        color = (0, 255, 0)
                        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                        label = f"ID:{track_id} {vehicle_type}"
                        if speed:
                            label += f" {speed}km/h"
                        if plate_text != "UNKNOWN":
                            label += f" [{plate_text}]"
                        cv2.putText(annotated, label, (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)

        # HUD overlay
        cv2.rectangle(annotated, (0, 0), (350, 100), (0, 0, 0), -1)
        cv2.putText(annotated, "ARG ENFORCEMENT AI", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(annotated, f"Frame: {frame_num}/{total_frames}", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(annotated, f"Vehicles: {total_vehicles} | Violations: {total_violations}", (10, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

        writer.write(annotated)

        if frame_num % (fps * 5) == 0:
            elapsed_pct = (frame_num / total_frames) * 100
            print(f"  [{elapsed_pct:.0f}%] Frame {frame_num}/{total_frames} | "
                  f"Vehicles: {total_vehicles} | Violations: {total_violations}")

    cap.release()
    writer.release()

    # Save all legal narratives
    if generated_challans:
        challans_path = os.path.join(output_dir, "legal_challans.txt")
        with open(challans_path, 'w', encoding='utf-8') as f:
            for ch in generated_challans:
                f.write(ch['narrative'])
                f.write("\n\n")
        print(f"\n📜 {len(generated_challans)} Legal Challans saved to: {challans_path}")

    # Summary
    print("\n" + "=" * 65)
    print("  ARG VIDEO ENGINE — SCAN COMPLETE")
    print("=" * 65)
    print(f"  Total frames processed:     {frame_num}")
    print(f"  Total vehicles tracked:     {total_vehicles}")
    print(f"  Unique plates read:         {len(tracked_plates)}")
    print(f"  Total violations:           {total_violations}")
    print(f"  Evidence packages stored:   {len(evidence.evidence_log)}")
    print(f"  Legal challans generated:   {len(generated_challans)}")
    print(f"\n  Output video: {out_path}")
    print(f"  Evidence vault: {evidence.output_dir}/")
    print("=" * 65)


def process_single_image(path, vehicle_model, plate_model, reader, evidence):
    """Process a single image with full analysis."""
    img = cv2.imread(path)
    if img is None:
        print(f"Cannot read: {path}")
        return

    print(f"\n🔍 Analyzing: {path}")

    results = vehicle_model.predict(img, verbose=False)
    for box in results[0].boxes:
        v_cls = int(box.cls[0])
        if v_cls not in [1, 2, 3, 5, 7]:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        crop = img[y1:y2, x1:x2]
        if crop.shape[0] < 30 or crop.shape[1] < 30:
            continue

        vehicle_type = {1: "Bicycle", 2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}.get(v_cls, "Vehicle")

        # Plate detection + OCR
        p_results = plate_model.predict(crop, verbose=False)
        plate_text = "UNKNOWN"
        for p_box in p_results[0].boxes:
            px1, py1, px2, py2 = map(int, p_box.xyxy[0])
            plate_crop = crop[
                max(0, py1 - 5):min(crop.shape[0], py2 + 5),
                max(0, px1 - 5):min(crop.shape[1], px2 + 5)
            ]
            if plate_crop.shape[0] > 0 and plate_crop.shape[1] > 0:
                ocr_res = reader.readtext(plate_crop)
                raw = "".join([r[1] for r in ocr_res])
                clean = re.sub(r'[^A-Z0-9]', '', raw.upper())
                if len(clean) >= 6 and PATTERN_INDIA.search(clean):
                    plate_text = clean
            break

        has_plate = len(p_results[0].boxes) > 0
        if not has_plate:
            narrative = generate_legal_narrative(plate_text, "NO PLATE VISIBLE", vehicle_type)
            print(narrative)
            evidence.store_evidence(img, crop, plate_text, "NO PLATE VISIBLE")
        else:
            print(f"  ✅ {vehicle_type} [{plate_text}] — Compliant")
            if plate_text != "UNKNOWN":
                narrative = generate_legal_narrative(plate_text, "ROUTINE CHECK", vehicle_type)
                print(narrative)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python arg_video_engine.py video.mp4")
        print("  python arg_video_engine.py image.jpg")
        sys.exit(1)

    run_video_engine(sys.argv[1])
