"""
ARG_Heirarchical_Detection.py
==============================
Aequitas RoadGuard (ARG) — Hierarchical Multi-Object Detection System
======================================================================

Pipeline overview
-----------------
Frame / Image
  └─ Stage 1 │ YOLOv11m  (COCO)   → track Vehicles  [car, motorcycle, truck, bus]
       │
       └─ Stage 2 │ Custom model  → detect Sub-Components per vehicle ROI
                        ├── 0: license_plate
                        ├── 1: vehicle_logo
                        ├── 2: grille
                        ├── 3: headlamp
                        └── 4: taillamp
                        │
                        ├── Spatial analyser  → infer vehicle orientation + make/model hint
                        └── Wealth linker     → CSV lookup → Wealth Multiplier

Dataset facts (from labels.cache)
----------------------------------
  Training images : 1 651
  Class IDs       : [0, 1, 2, 3, 4]   (5 sub-component classes)
  Instance counts : plate=1 969  headlamp=3 874  taillamp=3 219
                    logo=2 767   grille=2 782

Usage (minimum command after this fix)
---------------------------------------
  # Single image
  python ARG_Heirarchical_Detection.py --source images\car\cars\test.jpg

  # Video
  python ARG_Heirarchical_Detection.py --source videos_structured\Videos\feed.mp4

  # Webcam
  python ARG_Heirarchical_Detection.py --source 0

  # With output saved
  python ARG_Heirarchical_Detection.py --source videos_structured\Videos\feed.mp4 --output test_images_outputs\result.mp4

  # Headless (no window)
  python ARG_Heirarchical_Detection.py --source images\car\cars\test.jpg --no-show
"""

import argparse
import csv
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from ultralytics import YOLO

# Auto-growth pipeline hook (optional — runs silently if script not found)
try:
    from ARG_Auto_Growth_Pipeline import save_plate_crop_for_pipeline, PLATE_CONF_GATE as _PLATE_GATE
    _GROWTH_PIPELINE_ENABLED = True
except ImportError:
    _GROWTH_PIPELINE_ENABLED = False
    _PLATE_GATE = 0.70


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

# ── Stage-1: COCO vehicle classes we care about ───────────────────────────── #
VEHICLE_COCO_IDS = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}

# ── Stage-2: sub-component class map (matches labels.cache ordering) ──────── #
SUBCOMP_CLASSES = {
    0: "license_plate",
    1: "vehicle_logo",
    2: "grille",
    3: "headlamp",
    4: "taillamp",
}

# ── Luxury / premium logo keywords → CSV lookup is triggered ─────────────── #
LUXURY_BRANDS = {
    "mercedes", "bmw", "audi", "porsche", "lexus",
    "jaguar", "landrover", "bentley", "rolls", "ferrari",
    "lamborghini", "maserati", "volvo", "genesis",
}

# ── Colours per sub-component class (BGR) ────────────────────────────────── #
CLASS_COLORS = {
    0: (0,   255, 255),   # license_plate  – cyan
    1: (255, 128,   0),   # vehicle_logo   – orange
    2: (0,   200, 100),   # grille         – green
    3: (255, 255,   0),   # headlamp       – yellow
    4: (100, 100, 255),   # taillamp       – purple
}

VEHICLE_BOX_COLOR  = (0, 220, 0)     # green
TRACKING_ID_COLOR  = (255, 255, 255) # white
WEALTH_ALERT_COLOR = (0,  50, 255)   # red-orange

# ── Detection thresholds ─────────────────────────────────────────────────── #
VEHICLE_CONF  = 0.40
SUBCOMP_CONF  = 0.30   # Minimum conf to DRAW a sub-component box on screen
ANALYSIS_CONF = 0.50   # Minimum conf to USE a sub-component for orientation/logo analysis
SUBCOMP_IOU   = 0.45

# ── ROI padding (pixels) around vehicle box before passing to Stage-2 ─────  #
ROI_PAD = 10

# ── Default model + CSV paths  (relative to project root) ────────────────── #
DEFAULT_VEHICLE_MODEL = r"yolo11m.pt"
DEFAULT_SUBCOMP_MODEL = r"runs\detect\arg_combined_model\weights\best.pt"
DEFAULT_CSV           = r"data_csv\cars_details_data.csv"


# ══════════════════════════════════════════════════════════════════════════════
#  DATA CLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SubComponent:
    cls_id:  int
    cls_name: str
    conf:    float
    xyxy:    np.ndarray   # absolute coords in original frame
    cx:      float = 0.0  # centre-x
    cy:      float = 0.0  # centre-y

    def __post_init__(self):
        x1, y1, x2, y2 = self.xyxy
        self.cx = (x1 + x2) / 2
        self.cy = (y1 + y2) / 2


@dataclass
class VehicleRecord:
    track_id:      int
    coco_class:    str
    vehicle_xyxy:  np.ndarray
    subcomponents: list  = field(default_factory=list)
    orientation:   str   = "unknown"  # "front" | "rear" | "side" | "unknown"
    make_hint:     str   = "unknown"
    logo_conf:     float = 0.0
    wealth_mult:   float = 1.0
    plate_text:    str   = ""         # filled by OCR module if available


# ══════════════════════════════════════════════════════════════════════════════
#  WEALTH CSV LOADER
# ══════════════════════════════════════════════════════════════════════════════

class WealthDatabase:
    """
    Loads data_csv/cars_details_data.csv and exposes a lookup by vehicle make.

    Expected CSV columns (case-insensitive):
        make, model, ex_showroom_price   (or any column containing 'price')

    Wealth Multiplier formula:
        multiplier = clamp(ex_showroom_price / 5_00_000,  1.0,  10.0)
    """

    def __init__(self, csv_path: Optional[str] = None):
        self._records: list[dict] = []
        self._loaded = False

        if csv_path and os.path.exists(csv_path):
            self._load(csv_path)
        else:
            print(f"[WealthDB] CSV not found at '{csv_path}' — multiplier defaults to 1.0")

    def _load(self, path: str) -> None:
        with open(path, newline="", encoding="utf-8") as f:
            reader  = csv.DictReader(f)
            headers = [h.lower().strip() for h in (reader.fieldnames or [])]

            price_col = next((h for h in headers if "on-road" in h or "price" in h), None)
            make_col  = next((h for h in headers if "car name" in h or "make" in h or "vehicle name" in h), None)
            model_col = next((h for h in headers if "model" in h), None)

            if not all([price_col, make_col]):
                print(f"[WealthDB] Required columns not found. Headers: {headers}")
                return

            for row in reader:
                lrow = {k.lower().strip(): v for k, v in row.items()}
                try:
                    price = float(
                        str(lrow.get(price_col, "0")).replace(",", "").strip() or 0
                    )
                except ValueError:
                    price = 0.0
                self._records.append({
                    "make":  lrow.get(make_col,  "").strip().lower(),
                    "model": lrow.get(model_col, "").strip().lower() if model_col else "",
                    "price": price,
                })

        self._loaded = True
        print(f"[WealthDB] Loaded {len(self._records)} records from '{path}'")

    def lookup(self, make_hint: str, logo_conf: float) -> tuple:
        """Return (wealth_multiplier, matched_label)."""
        make_lower = make_hint.lower().strip()

        # ── 1. Try CSV ────────────────────────────────────────────────── #
        if self._loaded and make_lower:
            best_price = 0.0
            for rec in self._records:
                if make_lower in rec["make"] or rec["make"] in make_lower:
                    best_price = max(best_price, rec["price"])
            if best_price > 0:
                mult = round(min(10.0, max(1.0, best_price / 500_000)), 2)
                return mult, f"{make_hint} (CSV ₹{best_price:,.0f})"

        # ── 2. Hard-coded luxury tiers ────────────────────────────────── #
        luxury_tiers = {
            "rolls":       10.0, "bentley":    10.0, "ferrari":    10.0,
            "lamborghini": 10.0, "bugatti":    10.0, "maserati":    8.0,
            "porsche":      7.0, "bmw":         5.0, "mercedes":    5.0,
            "audi":         4.5, "lexus":       4.0, "jaguar":      4.0,
            "landrover":    4.0, "volvo":       3.0, "genesis":     3.0,
        }
        for brand, mult in luxury_tiers.items():
            if brand in make_lower:
                return mult, f"{make_hint} (tier fallback)"

        return 1.0, "standard"


# ══════════════════════════════════════════════════════════════════════════════
#  SPATIAL ANALYSER
# ══════════════════════════════════════════════════════════════════════════════

class SpatialAnalyser:
    """
    Uses relative positions of sub-components to determine:
      1. Vehicle orientation  (front / rear / side / unknown)
      2. Make/model hint from logo position

    Spatial rules
    -------------
    FRONT : headlamps + grille present, no taillamps
    REAR  : taillamps present, no headlamps
    SIDE  : single headlamp OR taillamp, no grille
    """

    @staticmethod
    def analyse(vehicle: VehicleRecord, frame: np.ndarray = None) -> VehicleRecord:
        comps = vehicle.subcomponents
        if not comps:
            return vehicle

        vx1, vy1, vx2, vy2 = vehicle.vehicle_xyxy
        vw = max(vx2 - vx1, 1)
        vh = max(vy2 - vy1, 1)

        by_class: dict = defaultdict(list)
        for sc in comps:
            by_class[sc.cls_id].append(sc)

        logos    = by_class[1]
        grilles  = by_class[2]
        headlmps = by_class[3]
        taillmps = by_class[4]
        plates   = by_class[0]

        # ── Spatial Sanity: Fix swapped headlamp/taillamp using LIGHT COLOR ─ #
        # Headlamps glow WHITE/YELLOW, Taillamps glow RED.
        # We read actual pixel colors from the frame ROI to correct mislabels.
        corrected_headlmps = []
        corrected_taillmps = []
        all_lights = [(sc, "head") for sc in headlmps] + [(sc, "tail") for sc in taillmps]
        for sc, original_label in all_lights:
            # Only do color check if we have a frame to sample from
            if frame is not None:
                lx1, ly1, lx2, ly2 = sc.xyxy
                roi = frame[max(0, ly1):max(0, ly2), max(0, lx1):max(0, lx2)]
                if roi.size > 0:
                    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    total_px = max(roi.shape[0] * roi.shape[1], 1)
                    red_lo = cv2.inRange(hsv, np.array([0,   80,  80]), np.array([12,  255, 255]))
                    red_hi = cv2.inRange(hsv, np.array([165, 80,  80]), np.array([180, 255, 255]))
                    red_ratio = (cv2.countNonZero(red_lo) + cv2.countNonZero(red_hi)) / total_px
                    if red_ratio > 0.20:
                        corrected = type(sc)(cls_id=4, cls_name="taillamp", conf=sc.conf, xyxy=sc.xyxy)
                        corrected_taillmps.append(corrected)
                        continue
            # No frame or no color match — keep original label
            if original_label == "head":
                corrected_headlmps.append(sc)
            else:
                corrected_taillmps.append(sc)
        headlmps = corrected_headlmps
        taillmps = corrected_taillmps


        # ── Orientation ─────────────────────────────────────────────── #
        has_grille   = len(grilles)  > 0
        has_headlamp = len(headlmps) > 0
        has_taillamp = len(taillmps) > 0
        has_plate    = len(plates)   > 0

        # RULE 1: Grille is physically ONLY on the front of any vehicle
        # If grille is detected, regardless of anything else, it\'s a front view.
        if has_grille:
            orientation = "front"
        elif has_taillamp and not has_headlamp:
            orientation = "rear"
        elif has_plate and not has_grille:
            # Plate in lower half without grille → likely rear view
            best_plate = max(plates, key=lambda s: s.conf)
            plate_norm_y = (best_plate.cy - vy1) / vh
            if plate_norm_y > 0.55:
                orientation = "rear"
            else:
                orientation = "front"
        elif has_headlamp and has_taillamp:
            orientation = "front" if len(headlmps) >= len(taillmps) else "rear"
        elif has_headlamp or has_taillamp:
            orientation = "side"
        else:
            orientation = "unknown"

        vehicle.orientation = orientation

        # ── Make/model hint from logo position ───────────────────────── #
        if logos:
            best_logo = max(logos, key=lambda s: s.conf)
            vehicle.logo_conf = best_logo.conf

            lx_norm = (best_logo.cx - vx1) / vw
            ly_norm = (best_logo.cy - vy1) / vh
            centred_h = abs(lx_norm - 0.5) < 0.20

            position_tag = []
            if orientation == "rear":
                position_tag.append("boot badge")
            elif centred_h and ly_norm < 0.50:
                position_tag.append("bonnet/nose badge")
            elif centred_h and ly_norm >= 0.50:
                position_tag.append("boot badge")
            else:
                position_tag.append("side badge")

            if len(headlmps) >= 2:
                sorted_hl  = sorted(headlmps, key=lambda s: s.cx)
                hl_spread  = (sorted_hl[-1].cx - sorted_hl[0].cx) / vw
                position_tag.append(
                    "wide front (SUV/Truck)" if hl_spread > 0.50
                    else "narrow front (Hatchback/Sedan)"
                )

            vehicle.make_hint = " | ".join(position_tag)

        elif grilles and orientation == "front":
            vehicle.make_hint = "logo not visible (grille only)"
        elif orientation == "rear":
            vehicle.make_hint = "rear view (boot)"
        else:
            vehicle.make_hint = "no logo detected"

        return vehicle


# ══════════════════════════════════════════════════════════════════════════════
#  HIERARCHICAL DETECTOR
# ══════════════════════════════════════════════════════════════════════════════

class HierarchicalDetector:

    def __init__(
        self,
        vehicle_model_path: str = DEFAULT_VEHICLE_MODEL,
        subcomp_model_path: str = DEFAULT_SUBCOMP_MODEL,
        csv_path:           Optional[str] = DEFAULT_CSV,
        vehicle_conf:       float = VEHICLE_CONF,
        subcomp_conf:       float = SUBCOMP_CONF,
    ):
        print("[ARG] Loading Stage-1 vehicle model …")
        self.vehicle_model = YOLO(vehicle_model_path)

        print("[ARG] Loading Stage-2 sub-component model …")
        self.subcomp_model = YOLO(subcomp_model_path)

        self.vehicle_conf = vehicle_conf
        self.subcomp_conf = subcomp_conf
        self.wealth_db    = WealthDatabase(csv_path)

        # track_id → last VehicleRecord (used for cross-frame persistence)
        self._track_history: dict = {}

        print("[ARG] Pipeline ready.\n")

    # ──────────────────────────────────────────────────────────────────────── #
    #  CORE FRAME PROCESSOR
    # ──────────────────────────────────────────────────────────────────────── #

    def process_frame(
        self, frame: np.ndarray
    ) -> tuple:
        """
        Run the full hierarchical pipeline on one BGR frame.
        Returns (annotated_frame, list[VehicleRecord]).
        """
        records: list[VehicleRecord] = []

        # ── Stage 1: track vehicles ───────────────────────────────────── #
        track_results = self.vehicle_model.track(
            frame,
            persist=True,
            conf=self.vehicle_conf,
            classes=list(VEHICLE_COCO_IDS.keys()),
            verbose=False,
        )

        if not track_results or track_results[0].boxes is None:
            return self._render(frame.copy(), records), records

        result   = track_results[0]
        boxes    = result.boxes.xyxy.cpu().numpy()
        cls_ids  = result.boxes.cls.cpu().numpy().astype(int)
        track_ids = (
            result.boxes.id.cpu().numpy().astype(int)
            if result.boxes.id is not None
            else np.arange(len(boxes))
        )

        h_frame, w_frame = frame.shape[:2]

        # ── Stage 2: sub-components per vehicle ROI ───────────────────── #
        for box, cls_id, tid in zip(boxes, cls_ids, track_ids):
            if cls_id not in VEHICLE_COCO_IDS:
                continue

            x1, y1, x2, y2 = map(int, box)

            # Padded ROI crop
            rx1 = max(0,       x1 - ROI_PAD)
            ry1 = max(0,       y1 - ROI_PAD)
            rx2 = min(w_frame, x2 + ROI_PAD)
            ry2 = min(h_frame, y2 + ROI_PAD)
            roi = frame[ry1:ry2, rx1:rx2]

            if roi.size == 0:
                continue

            sub_results = self.subcomp_model.predict(
                roi,
                conf=self.subcomp_conf,
                iou=SUBCOMP_IOU,
                verbose=False,
            )

            subcomps: list[SubComponent] = []
            if sub_results and sub_results[0].boxes is not None:
                for sbox, scls, sconf in zip(
                    sub_results[0].boxes.xyxy.cpu().numpy(),
                    sub_results[0].boxes.cls.cpu().numpy().astype(int),
                    sub_results[0].boxes.conf.cpu().numpy(),
                ):
                    # Translate ROI-local → frame-absolute coordinates
                    sc = SubComponent(
                        cls_id   = scls,
                        cls_name = SUBCOMP_CLASSES.get(scls, f"cls_{scls}"),
                        conf     = float(sconf),
                        xyxy     = np.array([
                            int(sbox[0]) + rx1,
                            int(sbox[1]) + ry1,
                            int(sbox[2]) + rx1,
                            int(sbox[3]) + ry1,
                        ]),
                    )
                    subcomps.append(sc)

            # Build record — ALL detected subcomps used for visual rendering
            record = VehicleRecord(
                track_id      = int(tid),
                coco_class    = VEHICLE_COCO_IDS[cls_id],
                vehicle_xyxy  = np.array([x1, y1, x2, y2]),
                subcomponents = subcomps,
            )

            # Only HIGH-CONFIDENCE sub-components feed the spatial analysis
            # This prevents 34-40% noise from corrupting orientation/logo decisions
            reliable_subcomps = [sc for sc in subcomps if sc.conf >= ANALYSIS_CONF]
            record_for_analysis = VehicleRecord(
                track_id      = record.track_id,
                coco_class    = record.coco_class,
                vehicle_xyxy  = record.vehicle_xyxy,
                subcomponents = reliable_subcomps,
            )
            record_for_analysis = SpatialAnalyser.analyse(record_for_analysis, frame=frame)

            # Copy the analysis results back to the main record (keep all subcomps for display)
            record.orientation = record_for_analysis.orientation
            record.make_hint   = record_for_analysis.make_hint
            record.logo_conf   = record_for_analysis.logo_conf

            # Wealth lookup only when logo is confidently detected (>=0.60)
            if record.logo_conf >= 0.60:
                detected_brand = "unknown"
                for brand in LUXURY_BRANDS:
                    if brand in record.make_hint.lower():
                        detected_brand = brand
                        break
                if detected_brand != "unknown" or record.logo_conf > 0.70:
                    mult, _ = self.wealth_db.lookup(detected_brand, record.logo_conf)
                    record.wealth_mult = mult

            # ── Custom Regional Taxonomy Overrides ────────────────────────── #
            # Plate color classification gates
            is_yellow_plate      = False  # Commercial Taxi (yellow bg)
            is_green_private     = False  # EV Private (white text on green)
            is_green_ev_taxi     = False  # EV Taxi (yellow text on green)

            for sc in record.subcomponents:
                if sc.cls_id == 0 and sc.conf > 0.45:
                    px1, py1, px2, py2 = sc.xyxy
                    pw, ph = px2 - px1, py2 - py1
                    if pw > 40 and ph > 12 and (pw / max(ph, 1)) > 1.5:
                        plate_roi = frame[py1:py2, px1:px2]
                        color_result = _detect_plate_color(plate_roi)

                        # ── Auto-Growth Pipeline: save high-conf plates for data growth
                        if _GROWTH_PIPELINE_ENABLED and sc.conf >= _PLATE_GATE:
                            try:
                                save_plate_crop_for_pipeline(
                                    frame, list(sc.xyxy),
                                    record.coco_class, float(sc.conf)
                                )
                            except Exception:
                                pass  # Never crash detection due to logging
                        if color_result == "yellow":
                            is_yellow_plate = True
                        elif color_result == "green_private":
                            is_green_private = True
                        elif color_result == "green_ev_taxi":
                            is_green_ev_taxi = True
                        break

            # Scale-based class refinement
            box_area   = (x2 - x1) * (y2 - y1)
            frame_area = w_frame * h_frame
            rel_size   = box_area / max(frame_area, 1)
            # Aspect ratio: width/height of the bounding box
            bbox_aspect = (x2 - x1) / max(y2 - y1, 1)

            # Apply plate-based classification (in priority order)
            if is_yellow_plate:
                if record.coco_class == "Car":
                    record.coco_class = "Commercial Taxi"
                elif record.coco_class in ["Truck", "Bus"]:
                    record.coco_class = "Commercial Vehicle"
                # Motorcycles NEVER reclassified by plate alone
            elif is_green_ev_taxi:
                if record.coco_class == "Car":
                    record.coco_class = "EV Taxi"
            elif is_green_private:
                if record.coco_class == "Car":
                    record.coco_class = "EV (Private)"

            # Fix YOLO Truck/Bus misclassification using size + aspect ratio
            if record.coco_class in ["Truck", "Bus", "Commercial Vehicle"]:
                if rel_size < 0.10:
                    # Small footprint: distinguish 3-wheeler (wide) vs small truck (tall-ish)
                    if bbox_aspect > 1.3:  # wide → auto-rickshaw style
                        record.coco_class = "3-Wheeler"
                    else:                  # taller narrow → mini-truck/tempo
                        record.coco_class = "Small Commercial"
                else:
                    # Large footprint stays heavy
                    if not is_yellow_plate:
                        record.coco_class = "Heavy Commercial"

            self._track_history[int(tid)] = record
            records.append(record)

        return self._render(frame.copy(), records), records

    # ──────────────────────────────────────────────────────────────────────── #
    #  RENDERER
    # ──────────────────────────────────────────────────────────────────────── #

    def _render(self, frame: np.ndarray, records: list) -> np.ndarray:
        for rec in records:
            vx1, vy1, vx2, vy2 = rec.vehicle_xyxy

            # Vehicle box — red-orange border if Wealth Multiplier > 2×
            box_color = WEALTH_ALERT_COLOR if rec.wealth_mult > 2.0 else VEHICLE_BOX_COLOR
            thickness = 3 if rec.wealth_mult > 2.0 else 2
            cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), box_color, thickness)

            # Track ID banner
            banner = (
                f"ID:{rec.track_id}  {rec.coco_class}  "
                f"[{rec.orientation}]  WM:{rec.wealth_mult:.1f}x"
            )
            _put_text_bg(frame, banner, (vx1, vy1 - 8), box_color)

            # Make/model hint below vehicle box
            if rec.make_hint not in ("no logo detected", "unknown"):
                _put_text_bg(
                    frame,
                    f"Hint: {rec.make_hint[:55]}",
                    (vx1, vy2 + 16),
                    (30, 30, 30),
                    font_scale=0.40,
                )

            # Sub-component boxes
            for sc in rec.subcomponents:
                sx1, sy1, sx2, sy2 = sc.xyxy
                color = CLASS_COLORS.get(sc.cls_id, (180, 180, 180))
                cv2.rectangle(frame, (sx1, sy1), (sx2, sy2), color, 1)
                cv2.putText(
                    frame,
                    f"{sc.cls_name} {sc.conf:.2f}",
                    (sx1, sy1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA,
                )

        _draw_hud(frame, records)
        return frame

    # ──────────────────────────────────────────────────────────────────────── #
    #  IMAGE MODE
    # ──────────────────────────────────────────────────────────────────────── #

    def run_image(self, image_path: str, output_path: Optional[str] = None, show: bool = True) -> None:
        frame = cv2.imread(image_path)
        if frame is None:
            print(f"[ERROR] Cannot read image: {image_path}")
            return

        annotated, records = self.process_frame(frame)
        _print_records(records)

        out = output_path or _default_output_path(image_path)
        cv2.imwrite(out, annotated)
        print(f"[ARG] Saved → {out}")

        # Show result window (press any key to close)
        if show:
            cv2.imshow("ARG — Result", annotated)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    # ──────────────────────────────────────────────────────────────────────── #
    #  VIDEO / WEBCAM MODE
    # ──────────────────────────────────────────────────────────────────────── #

    def run_video(
        self,
        source,
        output_path: Optional[str] = None,
        show: bool = True,
    ) -> None:
        cap = cv2.VideoCapture(
            source if isinstance(source, int) else str(source)
        )
        if not cap.isOpened():
            print(f"[ERROR] Cannot open source: {source}")
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        W   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        H   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        writer = None
        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_path, fourcc, fps, (W, H))
            print(f"[ARG] Writing output → {output_path}")

        frame_idx = 0
        t0        = time.time()
        
        # Max frames to process if a duration limit is set
        frames_limit = int(fps * self.duration) if getattr(self, 'duration', 0) else None

        try:
            while True:
                if frames_limit and frame_idx >= frames_limit:
                    print(f"[ARG] Duration limit reached ({getattr(self, 'duration')}s). Halting safely.")
                    break
                    
                ret, frame = cap.read()
                if not ret:
                    break

                annotated, _ = self.process_frame(frame)
                frame_idx   += 1

                # Live FPS counter (top-right corner)
                live_fps = frame_idx / max(time.time() - t0, 1e-6)
                cv2.putText(
                    annotated, f"FPS: {live_fps:.1f}",
                    (W - 115, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (200, 200, 200), 1, cv2.LINE_AA,
                )

                if writer:
                    writer.write(annotated)

                if show:
                    cv2.imshow("ARG — Hierarchical Detection", annotated)
                    if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                        print("[ARG] Quit key pressed.")
                        break

        finally:
            cap.release()
            if writer:
                writer.release()
            if show:
                try:
                    cv2.destroyAllWindows()
                except:
                    pass
            elapsed = time.time() - t0
            print(f"[ARG] Processed {frame_idx} frames in {elapsed:.1f}s  "
                  f"(avg {frame_idx/max(elapsed,1e-6):.1f} FPS)")


# ══════════════════════════════════════════════════════════════════════════════
#  RENDERING HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _detect_plate_color(plate_roi: np.ndarray) -> str:
    """
    Analyses a cropped plate ROI and returns a string indicating plate type:
      'yellow'         → Commercial taxi (yellow background)
      'green_private'  → Private EV (green bg, white text)
      'green_ev_taxi'  → EV Taxi (green bg, yellow text)
      'white'          → Standard private vehicle
      'unknown'
    """
    if plate_roi.size == 0:
        return "unknown"
    hsv = cv2.cvtColor(plate_roi, cv2.COLOR_BGR2HSV)

    # Yellow plate: H=18-35, high saturation & value
    yellow_mask = cv2.inRange(hsv, np.array([18, 120, 120]), np.array([35, 255, 255]))
    # Green plate background: H=40-80
    green_mask  = cv2.inRange(hsv, np.array([40, 60,  60]),  np.array([85, 255, 255]))
    # Yellow text ON green plate: same yellow hue but co-existing with green
    total_px = max(plate_roi.shape[0] * plate_roi.shape[1], 1)

    yellow_ratio = cv2.countNonZero(yellow_mask) / total_px
    green_ratio  = cv2.countNonZero(green_mask)  / total_px

    if green_ratio > 0.25:
        # It's a green plate — check if there's yellow text too
        if yellow_ratio > 0.05:   # yellow text present → EV Taxi
            return "green_ev_taxi"
        else:                     # pure green → Private EV
            return "green_private"
    elif yellow_ratio > 0.30:
        return "yellow"           # Commercial taxi
    else:
        return "white"            # Standard private


# Keep old helper for backwards compat
def _is_yellow_plate(plate_roi: np.ndarray) -> bool:
    return _detect_plate_color(plate_roi) == "yellow"

def _put_text_bg(
    img:        np.ndarray,
    text:       str,
    origin:     tuple,
    bg_color:   tuple = (0, 0, 0),
    font_scale: float = 0.45,
    thickness:  int   = 1,
) -> None:
    """Render text with a filled background rectangle for legibility."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = origin
    cv2.rectangle(
        img,
        (x, y - th - baseline - 2),
        (x + tw + 4, y + 2),
        bg_color, cv2.FILLED,
    )
    cv2.putText(img, text, (x + 2, y - baseline),
                font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)


def _draw_hud(frame: np.ndarray, records: list) -> None:
    """Semi-transparent HUD panel in the top-left corner."""
    lines = [
        f"ARG  |  Vehicles detected: {len(records)}",
        *[
            f"  ID {r.track_id}: {r.coco_class[:3]}  "
            f"{r.orientation[:3]}  WM={r.wealth_mult:.1f}x  "
            f"parts={len(r.subcomponents)}"
            for r in records[:8]
        ],
    ]
    x0, y0, lh = 8, 24, 18
    overlay = frame.copy()
    cv2.rectangle(overlay, (4, 4), (330, 4 + len(lines) * lh + 8),
                  (10, 10, 10), cv2.FILLED)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    for i, line in enumerate(lines):
        color = (0, 255, 180) if i == 0 else (200, 200, 200)
        cv2.putText(frame, line, (x0, y0 + i * lh),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)


def _print_records(records: list) -> None:
    print(f"\n{'─' * 68}")
    print(f"  Detected {len(records)} vehicle(s)")
    print(f"{'─' * 68}")
    for r in records:
        print(f"  Track {r.track_id:>3} │ {r.coco_class:<12} │ "
              f"{r.orientation:<8} │ WM {r.wealth_mult:.1f}x │ "
              f"{len(r.subcomponents)} sub-comps")
        for sc in r.subcomponents:
            print(f"             ↳ {sc.cls_name:<16} conf={sc.conf:.2f}")
        if r.make_hint not in ("no logo detected", "unknown"):
            print(f"           hint: {r.make_hint}")
    print(f"{'─' * 68}\n")


def _default_output_path(input_path: str) -> str:
    p = Path(input_path)
    out_dir = Path("test_images_outputs")
    out_dir.mkdir(exist_ok=True)
    return str(out_dir / f"{p.stem}_arg_out{p.suffix}")


# ══════════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="ARG Hierarchical Multi-Object Detection System",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--source", required=True,
        help="Image path, video path, or webcam index (0, 1, …)",
    )
    p.add_argument(
        "--vehicle-model", default=DEFAULT_VEHICLE_MODEL,
        help="Stage-1 COCO vehicle model weights",
    )
    p.add_argument(
        "--subcomp-model", default=DEFAULT_SUBCOMP_MODEL,
        help="Stage-2 sub-component model weights",
    )
    p.add_argument(
        "--csv", default=DEFAULT_CSV,
        help="CSV file for wealth multiplier lookup",
    )
    p.add_argument(
        "--output", default=None,
        help="Output file path (optional; auto-named if omitted)",
    )
    p.add_argument("--vehicle-conf", type=float, default=VEHICLE_CONF,
                   help="Confidence threshold for vehicle detection")
    p.add_argument("--subcomp-conf", type=float, default=SUBCOMP_CONF,
                   help="Confidence threshold for sub-component detection")
    p.add_argument("--no-show", action="store_true",
                   help="Disable live display window (headless / server mode)")
    p.add_argument("--duration", type=int, default=0,
                   help="Limit video processing to the first N seconds (0 for full)")
    return p


def main():
    args = build_parser().parse_args()

    detector = HierarchicalDetector(
        vehicle_model_path = args.vehicle_model,
        subcomp_model_path = args.subcomp_model,
        csv_path           = args.csv,
        vehicle_conf       = args.vehicle_conf,
        subcomp_conf       = args.subcomp_conf,
    )
    detector.duration = args.duration

    # Decide image vs video
    source = args.source
    try:
        source   = int(source)  # webcam index
        is_video = True
    except ValueError:
        is_video = Path(source).suffix.lower() not in {
            ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"
        }

    if is_video:
        detector.run_video(
            source      = source,
            output_path = args.output,
            show        = not args.no_show,
        )
    else:
        detector.run_image(
            image_path  = source,
            output_path = args.output,
            show        = not args.no_show,
        )


if __name__ == "__main__":
    main()