import sys
from pathlib import Path
root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path: sys.path.append(str(root_path))
"""
ARG_Heirarchical_Detection.py
"""

import argparse
import csv
import os
import sys
import time
import random
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from ultralytics import YOLO

try:
    from src.pipeline.auto_growth import save_plate_crop_for_pipeline, PLATE_CONF_GATE as _PLATE_GATE
    _GROWTH_PIPELINE_ENABLED = True
except ImportError:
    _GROWTH_PIPELINE_ENABLED = False
    _PLATE_GATE = 0.70

try:
    import torch
    from PIL import Image
    from groundingdino.util.inference import load_model as load_gdino_model, predict as gdino_predict
    import groundingdino.datasets.transforms as T
    _GDINO_AVAILABLE = True
except ImportError:
    _GDINO_AVAILABLE = False

VEHICLE_COCO_IDS = {0: "Car", 1: "Motorcycle", 2: "Bus", 3: "Truck"}




SUBCOMP_CLASSES = {
    0: "license_plate",
    1: "vehicle_logo",
    2: "grille",
    3: "headlamp",
    4: "taillamp",
}

LUXURY_BRANDS = {
    "mercedes", "bmw", "audi", "porsche", "lexus",
    "jaguar", "landrover", "bentley", "rolls-royce", "ferrari",
    "lamborghini", "maserati", "volvo", "genesis", "bugatti",
    "alfa romeo", "ktm", "ducati", "harley_davidson", "triumph"
}

CLASS_COLORS = {
    0: (0,   255, 255),
    1: (255, 128,   0),
    2: (0,   200, 100),
    3: (255, 255,   0),
    4: (100, 100, 255),
}

VEHICLE_BOX_COLOR  = (0, 220, 0)
TRACKING_ID_COLOR  = (255, 255, 255)
WEALTH_ALERT_COLOR = (0,  50, 255)

VEHICLE_CONF  = 0.10
VEHICLE_IOU   = 0.50
SUBCOMP_CONF  = 0.20
ANALYSIS_CONF = 0.25
SUBCOMP_IOU   = 0.45

ROI_PAD = 10
GDINO_CACHE_TTL = 30   # Reuse GDINO results for N frames per tracked vehicle
MAX_GDINO_PER_FRAME = 5  # Max vehicles to run GDINO on per frame

DEFAULT_VEHICLE_MODEL = r"best_new.pt"
DEFAULT_SUBCOMP_MODEL = r"models/stage2_subcomp/non_existent.pt"





DEFAULT_CSV           = r"data_csv\cars_details_data.csv"

GDINO_CONFIG  = r"C:\Users\laksh\Desktop\image\models\gdino\GroundingDINO_SwinT_OGC.py"
GDINO_WEIGHTS = r"C:\Users\laksh\Desktop\image\models\gdino\groundingdino_swint_ogc.pth"
GDINO_CAPTION = "license plate . vehicle brand name text . brand emblem . radiator grille . headlight . taillight"

@dataclass
class SubComponent:
    cls_id:  int
    cls_name: str
    conf:    float
    xyxy:    np.ndarray
    cx:      float = 0.0
    cy:      float = 0.0

    def __post_init__(self):
        x1, y1, x2, y2 = self.xyxy
        self.cx = (x1 + x2) / 2
        self.cy = (y1 + y2) / 2


@dataclass
class VehicleRecord:
    track_id:      int
    coco_class:    str
    coco_id:       int
    vehicle_xyxy:  np.ndarray
    subcomponents: list  = field(default_factory=list)
    orientation:   str   = "unknown"
    make_hint:     str   = "unknown"
    logo_conf:     float = 0.0
    wealth_mult:   float = 1.0
    plate_text:    str   = ""


class WealthDatabase:
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
                    price = float(str(lrow.get(price_col, "0")).replace(",", "").strip() or 0)
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
        make_lower = make_hint.lower().strip()
        if self._loaded and make_lower:
            best_price = 0.0
            for rec in self._records:
                if make_lower in rec["make"] or rec["make"] in make_lower:
                    best_price = max(best_price, rec["price"])
            if best_price > 0:
                mult = round(min(10.0, max(1.0, best_price / 500_000)), 2)
                return mult, f"{make_hint} (CSV ₹{best_price:,.0f})"
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


class SpatialAnalyser:

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
        # FIX 1: Added shape gate BEFORE colour analysis to reject bottles,
        # thin objects, and other false positives that happen to be red.
        corrected_headlmps = []
        corrected_taillmps = []
        all_lights = [(sc, "head") for sc in headlmps] + [(sc, "tail") for sc in taillmps]

        vehicle_area = max((vx2 - vx1) * (vy2 - vy1), 1)

        for sc, original_label in all_lights:
            lx1, ly1, lx2, ly2 = sc.xyxy
            lw_px = max(lx2 - lx1, 1)
            lh_px = max(ly2 - ly1, 1)
            lamp_aspect   = lw_px / lh_px          # real lamps are wider than tall
            lamp_rel_size = (lw_px * lh_px) / vehicle_area

            # SHAPE GATE ──────────────────────────────────────────────────── #
            # Bottles are taller than wide → aspect < 0.35                   #
            # Tiny speck noise           → rel_size < 0.004                  #
            # Implausibly large blob     → rel_size > 0.30                   #
            # In all these cases skip colour reclassification entirely and    #
            # trust the model's original label.                               #
            if lamp_aspect < 0.35 or lamp_rel_size < 0.004 or lamp_rel_size > 0.30:
                if original_label == "head":
                    corrected_headlmps.append(sc)
                else:
                    corrected_taillmps.append(sc)
                continue

            if frame is not None:
                roi_lamp = frame[max(0, ly1):max(0, ly2), max(0, lx1):max(0, lx2)]
                if roi_lamp.size > 0:
                    hsv = cv2.cvtColor(roi_lamp, cv2.COLOR_BGR2HSV)
                    total_px = max(roi_lamp.shape[0] * roi_lamp.shape[1], 1)
                    
                    # Red masks for Taillamps
                    red_lo = cv2.inRange(hsv, np.array([0,   80,  80]), np.array([12,  255, 255]))
                    red_hi = cv2.inRange(hsv, np.array([165, 80,  80]), np.array([180, 255, 255]))
                    red_ratio = (cv2.countNonZero(red_lo) + cv2.countNonZero(red_hi)) / total_px
                    
                    # White/Yellow masks for Headlamps (detecting active or bright reflectors)
                    white_mask  = cv2.inRange(hsv, np.array([0, 0, 180]), np.array([180, 40, 255]))
                    yellow_mask = cv2.inRange(hsv, np.array([20, 50, 150]), np.array([35, 255, 255]))
                    bright_ratio = (cv2.countNonZero(white_mask) + cv2.countNonZero(yellow_mask)) / total_px

                    # RECLASSIFICATION LOGIC
                    # 1. If strongly red and NOT bright/white → Taillamp
                    if red_ratio > 0.28 and bright_ratio < 0.15:
                        corrected = SubComponent(cls_id=4, cls_name="taillamp",
                                                 conf=sc.conf, xyxy=sc.xyxy)
                        corrected_taillmps.append(corrected)
                        continue
                    # 2. If strongly bright/white → Headlamp
                    elif bright_ratio > 0.35:
                        corrected = SubComponent(cls_id=3, cls_name="headlamp",
                                                 conf=sc.conf, xyxy=sc.xyxy)
                        corrected_headlmps.append(corrected)
                        continue
        headlmps = corrected_headlmps
        taillmps = corrected_taillmps

        # ── Orientation ─────────────────────────────────────────────── #
        has_grille   = len(grilles)  > 0
        has_headlamp = len(headlmps) > 0
        has_taillamp = len(taillmps) > 0
        has_plate    = len(plates)   > 0

        # --- Orientation Decision Matrix (V3 - Hard Structural Constraints) ---
        f_score = 0.0
        r_score = 0.0

        is_bike = vehicle.coco_class == "Motorcycle"
        has_grille_front = any(sc.cls_id == 2 for sc in comps)
        
        # RULE: GRILLE ALWAYS ABOVE PLATE for front
        if has_grille_front and has_plate:
            best_p = max(plates, key=lambda s: s.conf)
            best_g = max([sc for sc in comps if sc.cls_id == 2], key=lambda s: s.conf)
            if best_g.cy < best_p.cy: # Grille is higher
                f_score += 2.0
            else:
                # Impossible structure for car front → penalize
                f_score -= 1.0

        if any(sc.cls_id == 1 for sc in comps): f_score += 1.0
        
        # Lamp scores with structural logic
        # Headlamp Logic
        if len(headlmps) >= 2:
            f_score += 1.5
            h1, h2 = sorted(headlmps, key=lambda s: s.cx)[:2]
            # Symmetrically mirroring each other on edges
            is_mirror = abs(h1.cy - h2.cy) / vh < 0.12
            is_edge = h1.cx / vw < 0.4 and h2.cx / vw > 0.6
            if is_mirror and is_edge: f_score += 1.0
        elif len(headlmps) == 1:
            if is_bike:
                # RULE: Motorcycles have EXACT CENTER lamp
                lx_norm = (headlmps[0].cx - vx1) / vw
                if 0.40 < lx_norm < 0.60: f_score += 2.0
            else:
                f_score += 0.4

        # Taillamp Logic
        if len(taillmps) >= 2:
            r_score += 1.5
            t1, t2 = sorted(taillmps, key=lambda s: s.cx)[:2]
            is_mirror = abs(t1.cy - t2.cy) / vh < 0.12
            is_edge = t1.cx / vw < 0.4 and t2.cx / vw > 0.6
            if is_mirror and is_edge: r_score += 1.0
        elif len(taillmps) == 1:
            r_score += 0.3

        # RULE: REAR HAS NO GRILLE (Veto)
        if has_grille_front:
            r_score = 0.0 # Veto rear if a grille is detected and passed stacking

        # Final decision
        if f_score > r_score:
            orientation = "front"
        elif r_score > f_score:
            orientation = "rear"
        elif f_score == r_score and f_score > 0:
            orientation = "front" if has_grille_front else "side"
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

            brand_name = "unknown"
            if frame is not None:
                lx1, ly1, lx2, ly2 = map(int, best_logo.xyxy)
                logo_roi = frame[max(0, ly1):max(0, ly2), max(0, lx1):max(0, lx2)]
                brand_name, heuristic_conf = classify_logo_crop(logo_roi, vehicle_type=vehicle.coco_class)
                if brand_name != "unknown":
                    vehicle.logo_conf = max(vehicle.logo_conf, heuristic_conf)

            position_tag = []
            if brand_name != "unknown":
                position_tag.append(brand_name.upper())

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

        # ── Vehicle Specific Signatures ────────────────────────── #
        if vehicle.coco_class == "Motorcycle" and frame is not None:
            vx1, vy1, vx2, vy2 = map(int, vehicle.vehicle_xyxy)
            bike_roi = frame[max(0, vy1):max(0, vy2), max(0, vx1):max(0, vx2)]
            bike_sig, bike_conf = classify_bike_signature(bike_roi, headlmps)
            if bike_sig != "unknown":
                vehicle.make_hint = f"{bike_sig.upper()} | {bike_sig} bike signature"
                vehicle.logo_conf = max(vehicle.logo_conf, bike_conf)

        elif grilles and orientation == "front":
            best_grille = max(grilles, key=lambda s: s.conf)
            if frame is not None:
                gx1, gy1, gx2, gy2 = map(int, best_grille.xyxy)
                grille_roi = frame[max(0, gy1):max(0, gy2), max(0, gx1):max(0, gx2)]
                sig_name, sig_conf = classify_grille_crop(grille_roi)
                if sig_name != "unknown":
                    vehicle.make_hint = f"{sig_name.upper()} | {sig_name} face signature"
                    vehicle.logo_conf = max(vehicle.logo_conf, sig_conf)
            if "unknown" in vehicle.make_hint:
                vehicle.make_hint = "logo not visible (grille only)"

        if headlmps and frame is not None:
            for hl in headlmps:
                hx1, hy1, hx2, hy2 = map(int, hl.xyxy)
                hl_roi = frame[max(0, hy1):max(0, hy2), max(0, hx1):max(0, hx2)]
                if classify_lighting_signature(hl_roi) == "volvo":
                    vehicle.make_hint = "VOLVO | Thor's Hammer light signature"
                    vehicle.logo_conf = max(vehicle.logo_conf, 0.70)
                    break

        elif orientation == "rear":
            vehicle.make_hint = "rear view (boot)"
        else:
            vehicle.make_hint = "no logo detected"

        return vehicle


class HierarchicalDetector:

    def __init__(
        self,
        vehicle_model_path: str = DEFAULT_VEHICLE_MODEL,
        subcomp_model_path: str = DEFAULT_SUBCOMP_MODEL,
        csv_path:           Optional[str] = DEFAULT_CSV,
        vehicle_conf:       float = VEHICLE_CONF,
        subcomp_conf:       float = SUBCOMP_CONF,
        use_gdino:          bool = False,
    ):
        self.use_gdino = use_gdino
        device = "cuda"
        if not torch.cuda.is_available():
            raise RuntimeError("CRITICAL ERROR: GPU requested but CUDA is not available! Pipeline halting to prevent CPU execution.")
        
        self.device = torch.device(device)

        
        if use_gdino:
            if not _GDINO_AVAILABLE:
                raise ImportError("groundingdino-py not installed but requested.")
            print(f"[ARG] Loading Stage-2 GroundingDINO (Zero-Shot) on {device.upper()} …")
            self.subcomp_model = load_gdino_model(GDINO_CONFIG, GDINO_WEIGHTS, device=device)
            self.subcomp_model = self.subcomp_model.to(self.device)
            
            # Cache Transforms (V14 Sonic Overdrive)
            self.front_transform = T.Compose([
                T.RandomResize([448], max_size=800),
                T.ToTensor(),
                T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ])
            self.side_transform = T.Compose([
                T.RandomResize([320], max_size=640),
                T.ToTensor(),
                T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ])
            self.zoom_transform = T.Compose([
                T.RandomResize([800], max_size=1333),
                T.ToTensor(),
                T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ])
        else:
            print(f"[ARG] Loading Stage-2 sub-component model on {device.upper()} …")
            self.subcomp_model = YOLO(subcomp_model_path).to(self.device)

        print(f"[ARG] Loading Stage-1 vehicle model on {device.upper()} …")
        self.vehicle_model = YOLO(vehicle_model_path).to(self.device)

        self.vehicle_conf = vehicle_conf

        self.subcomp_conf = subcomp_conf
        self.wealth_db    = WealthDatabase(csv_path)
        self._track_history: dict = {}
        self._gdino_cache:   dict = {}  # tid -> (frame_idx, results)
        self._frame_idx           = 0
        print(f"[ARG] Pipeline ready (GPU Accelerated).")

        
        # Verify GPU visibility
        if device == "cuda":
            current_device = next(self.vehicle_model.parameters()).device
            print(f"[GPU_VERIFY] Primary Model Device: {current_device}")
            if self.use_gdino:
                g_device = next(self.subcomp_model.parameters()).device
                print(f"[GPU_VERIFY] GDino Model Device: {g_device}")

        print("[ARG] Pipeline ready (GPU Accelerated).\n")

    def _run_gdino_on_roi(self, roi: np.ndarray, vehicle_type: str = "Car", is_side_hint: bool = False) -> list:
        # --- SONIC TURBO (V14) ---
        if is_side_hint:
            active_caption = "brand emblem . brand name text"
            image_transformed, _ = self.side_transform(Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)), None)
        else:
            active_caption = GDINO_CAPTION
            image_transformed, _ = self.front_transform(Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)), None)

        # Explicit model device sync
        model_device = next(self.subcomp_model.parameters()).device

        boxes, logits, phrases = gdino_predict(
            model=self.subcomp_model,
            image=image_transformed,
            caption=active_caption,
            box_threshold=0.35,
            text_threshold=0.25,
            device=str(model_device)
        )
        
        results = []
        class_map = {"plate": 0, "logo": 1, "grille": 2, "headlight": 3, "taillight": 4}
        
        raw_detections = []
        for box, phrase, logit in zip(boxes, phrases, logits):
            p = phrase.lower()
            bcx, bcy, bw, bh = box.tolist()
            cls_id = -1
            for k, v in class_map.items():
                if k in p: cls_id = v; break
            
            # --- PLATE TO LOGO RE-CLASSIFICATION (EICHER/BRAND TEXT GUARD) ---
            if cls_id == 0 or "text" in p or "brand" in p:
                is_mostly_text = "text" in p or "name" in p
                aspect = bw / max(bh, 1e-6)
                
                # Rule: Real plates are in the bottom 55% and are WIDE
                if bcy < 0.45 or is_mostly_text or aspect < 1.4:
                    # Likely a brand logo/text high up (like EICHER)
                    cls_id = 1 
                elif cls_id == 0:
                    # Valid Plate Candidate
                    pass

            if cls_id != -1:
                if is_side_hint and vehicle_type.lower() != "motorcycle":
                    if cls_id in [1, 2]: continue
                raw_detections.append({"cls": cls_id, "box": box.tolist(), "conf": float(logit)})

        if vehicle_type.lower() == "motorcycle":
            raw_detections = [d for d in raw_detections if d["cls"] not in [1, 2]]

        grilles = [d for d in raw_detections if d["cls"] == 2]
        logos   = [d for d in raw_detections if d["cls"] == 1]
        
        # 1. GRILLE/LOGO ZOOM SHORT-CIRCUIT
        # Only zoom if no high-confidence logo was found in the primary pass
        best_primary_logo_conf = max([d["conf"] for d in logos], default=0.0)
        
        if grilles and best_primary_logo_conf < 0.65 and vehicle_type.lower() != "motorcycle":
            for g in grilles:
                gcx, gcy, gw, gh = g["box"]
                gx1, gy1 = max(0, gcx - gw/2 - 0.08), max(0, gcy - gh/2 - 0.15)
                gx2, gy2 = min(1, gcx + gw/2 + 0.08), min(1, gcy + gh/2 + 0.08)
                h_roi, w_roi = roi.shape[:2]
                g_roi_img = roi[int(gy1*h_roi):int(gy2*h_roi), int(gx1*w_roi):int(gx2*w_roi)]
                if g_roi_img.size > 0:
                    g_transformed, _ = self.zoom_transform(Image.fromarray(cv2.cvtColor(g_roi_img, cv2.COLOR_BGR2RGB)), None)
                    bg_boxes, bg_logits, bg_phrases = gdino_predict(
                        model=self.subcomp_model,
                        image=g_transformed,
                        caption="brand emblem . manufacturer logo . car badge",
                        box_threshold=0.20, text_threshold=0.18,
                        device=str(next(self.subcomp_model.parameters()).device)
                    )
                    for bbox, blogit in zip(bg_boxes, bg_logits):
                        bcx_l, bcy_l, bw_l, bh_l = bbox.tolist()
                        real_gw, real_gh = (gx2 - gx1), (gy2 - gy1)
                        raw_detections.append({
                            "cls": 1, "box": [gx1 + bcx_l*real_gw, gy1 + bcy_l*real_gh, bw_l*real_gw, bh_l*real_gh],
                            "conf": float(blogit)
                        })
                if any(d["cls"] == 1 for d in raw_detections): break

        # 2. BOOT TAG SEARCH SHORT-CIRCUIT
        # Skip if a high-confidence grille or logo is already found (likely front view)
        best_primary_grille_conf = max([d["conf"] for d in grilles], default=0.0)
        
        if not grilles and best_primary_logo_conf < 0.60 and vehicle_type.lower() != "motorcycle":
            # Search area: Center 50% width, 30%-60% height
            bx1, by1, bx2, by2 = 0.25, 0.30, 0.75, 0.60
            h_roi, w_roi = roi.shape[:2]
            boot_roi = roi[int(by1*h_roi):int(by2*h_roi), int(bx1*w_roi):int(bx2*w_roi)]
            if boot_roi.size > 0:
                b_transformed, _ = self.zoom_transform(Image.fromarray(cv2.cvtColor(boot_roi, cv2.COLOR_BGR2RGB)), None)
                bb_boxes, bb_logits, bb_phrases = gdino_predict(
                    model=self.subcomp_model, image=b_transformed,
                    caption="rear brand emblem . boot badge",
                    box_threshold=0.20, text_threshold=0.18,
                    device=str(next(self.subcomp_model.parameters()).device)
                )
                for bbox, blogit in zip(bb_boxes, bb_logits):
                    bcx_l, bcy_l, bw_l, bh_l = bbox.tolist()
                    raw_detections.append({
                        "cls": 1, "box": [bx1 + bcx_l*0.5, by1 + bcy_l*0.3, bw_l*0.5, bh_l*0.3],
                        "conf": float(blogit)
                    })

        if vehicle_type.lower() == "motorcycle" and not logos:
            tx1, ty1, tx2, ty2 = 0.2, 0.2, 0.8, 0.7
            h_roi, w_roi = roi.shape[:2]
            tank_roi = roi[int(ty1*h_roi):int(ty2*h_roi), int(tx1*w_roi):int(tx2*w_roi)]
            if tank_roi.size > 0:
                t_transformed, _ = self.zoom_transform(Image.fromarray(cv2.cvtColor(tank_roi, cv2.COLOR_BGR2RGB)), None)
                bt_boxes, bt_logits, bt_phrases = gdino_predict(
                    model=self.subcomp_model,
                    image=t_transformed,
                    caption="motorcycle brand logo . tank emblem",
                    box_threshold=0.20, text_threshold=0.18,
                    device=str(next(self.subcomp_model.parameters()).device)
                )
                for bbox, blogit in zip(bt_boxes, bt_logits):
                    bcx_l, bcy_l, bw_l, bh_l = bbox.tolist()
                    raw_detections.append({
                        "cls": 1, "box": [tx1 + bcx_l*0.6, ty1 + bcy_l*0.5, bw_l*0.6, bh_l*0.5],
                        "conf": float(blogit)
                    })

        # ──── GEOMETRIC VALIDATION (v9 - Precision Sharpness) ──── #
        validated = []
        is_bike = vehicle_type.lower() == "motorcycle"

        # 1. Plates — Aspect Ratio & Vertical Centering (Kills Decals)
        all_plates = sorted([d for d in raw_detections if d["cls"] == 0], key=lambda x: x["conf"], reverse=True)
        primary_plate = None
        for p in all_plates:
            pcx, pcy, pw, ph = p["box"]
            p_aspect = pw / max(ph, 0.001)
            # Indian Plates: 3.2 to 6.8 Aspect | Decals like "Lithium" are outside this range
            if not (3.2 < p_aspect < 6.8): continue
            if not (0.40 < pcy < 0.90): continue  # Must be in the typical plate zone
            if pw > 0.40 or ph > 0.20: continue   # Not too large relative to vehicle
            
            validated.append(p)
            if primary_plate is None:
                primary_plate = p
        
        tp_y1 = primary_plate["box"][1] if primary_plate else 1.0

        # 2. Logos — Anchored above the plate
        valid_logos = sorted([d for d in raw_detections if d["cls"] == 1], key=lambda x: x["conf"], reverse=True)
        for logo in valid_logos:
            lcx, lcy, lw, lh = logo["box"]
            # RECOVERY: If found above the plate, it is highly likely a real logo
            if lcy < tp_y1 and lw < 0.20:
                validated.append(logo)
                break

        # 3. Grilles — Forbidden if Taillamps are present
        raw_heads = sorted([d for d in raw_detections if d["cls"] == 3], key=lambda x: x["conf"], reverse=True)
        raw_tails = sorted([d for d in raw_detections if d["cls"] == 4], key=lambda x: x["conf"], reverse=True)
        
        h_conf = sum([d["conf"] for d in raw_heads[:2]])
        t_conf = sum([d["conf"] for d in raw_tails[:2]])
        is_rear = t_conf > h_conf
        
        if not is_rear:
            valid_grilles = sorted([d for d in raw_detections if d["cls"] == 2], key=lambda x: x["conf"], reverse=True)
            for g in valid_grilles:
                if g["box"][2] * g["box"][3] > 0.08: continue
                validated.append(g)
                break

        # 4. Lamps — Red = Tail Lock
        chosen_lamps = raw_heads[:2] if not is_rear else raw_tails[:2]
        for lamp in chosen_lamps:
            validated.append(lamp)

        return validated

    def process_frame(self, frame: np.ndarray, persist: bool = True) -> tuple:
        records: list[VehicleRecord] = []

        track_results = self.vehicle_model.track(
            frame,
            persist=persist,
            conf=self.vehicle_conf,
            iou=VEHICLE_IOU,
            classes=list(VEHICLE_COCO_IDS.keys()),
            verbose=False,
            agnostic_nms=True,  # Prevents double-boxing same vehicle as car+truck
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

        for box, cls_id, tid in zip(boxes, cls_ids, track_ids):
            if cls_id not in VEHICLE_COCO_IDS:
                continue

            x1, y1, x2, y2 = map(int, box)
            rx1 = max(0,       x1 - ROI_PAD)
            ry1 = max(0,       y1 - ROI_PAD)
            rx2 = min(w_frame, x2 + ROI_PAD)
            ry2 = min(h_frame, y2 + ROI_PAD)
            rw, rh = max(rx2 - rx1, 1), max(ry2 - ry1, 1)
            roi = frame[ry1:ry2, rx1:rx2]

            if roi.size == 0:
                continue

            if self.use_gdino:
                cls_name = VEHICLE_COCO_IDS[cls_id]
                aspect = rw / max(rh, 1)
                is_side = (aspect > 1.6 and cls_name != "Motorcycle") or (aspect > 2.2 and cls_name in ["Truck", "Bus"])

                # ──── SMART CACHE (V14 Turbo) ────
                # Only re-run GDINO every 12 frames for the same track ID
                cache_key = int(tid)
                cached = self._gdino_cache.get(cache_key)
                if cached and (self._frame_idx - cached[0] < GDINO_CACHE_TTL):
                    gd_results = cached[1]
                else:
                    gd_results = self._run_gdino_on_roi(roi, vehicle_type=cls_name, is_side_hint=is_side)
                    self._gdino_cache[cache_key] = (self._frame_idx, gd_results)


                subcomps: list[SubComponent] = []
                for res in gd_results:
                    cx_c, cy_c, bw_c, bh_c = res["box"]
                    sc = SubComponent(
                        cls_id   = res["cls"],
                        cls_name = SUBCOMP_CLASSES.get(res["cls"], f"cls_{res['cls']}"),
                        conf     = res["conf"],
                        xyxy     = np.array([
                            int((cx_c - bw_c/2) * rw) + rx1,
                            int((cy_c - bh_c/2) * rh) + ry1,
                            int((cx_c + bw_c/2) * rw) + rx1,
                            int((cy_c + bh_c/2) * rh) + ry1,
                        ]),
                    )
                    subcomps.append(sc)
            else:
                sub_results = self.subcomp_model.predict(
                    roi, conf=self.subcomp_conf, iou=SUBCOMP_IOU, verbose=False,
                )
                subcomps: list[SubComponent] = []
                if sub_results and sub_results[0].boxes is not None:
                    for sbox, scls, sconf in zip(
                        sub_results[0].boxes.xyxy.cpu().numpy(),
                        sub_results[0].boxes.cls.cpu().numpy().astype(int),
                        sub_results[0].boxes.conf.cpu().numpy(),
                    ):
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

            record = VehicleRecord(
                track_id      = int(tid),
                coco_class    = VEHICLE_COCO_IDS[cls_id],
                coco_id       = int(cls_id),
                vehicle_xyxy  = np.array([x1, y1, x2, y2]),
                subcomponents = subcomps,
            )
            reliable_subcomps = [sc for sc in subcomps if sc.conf >= ANALYSIS_CONF]
            record_for_analysis = VehicleRecord(
                track_id      = record.track_id,
                coco_class    = record.coco_class,
                coco_id       = record.coco_id,
                vehicle_xyxy  = record.vehicle_xyxy,
                subcomponents = reliable_subcomps,
            )
            record_for_analysis = SpatialAnalyser.analyse(record_for_analysis, frame=frame)

            record.orientation = record_for_analysis.orientation
            record.make_hint   = record_for_analysis.make_hint
            record.logo_conf   = record_for_analysis.logo_conf

            if record.logo_conf >= 0.60:
                detected_brand = "unknown"
                for brand in LUXURY_BRANDS:
                    if brand in record.make_hint.lower():
                        detected_brand = brand
                        break
                if detected_brand != "unknown" or record.logo_conf > 0.70:
                    mult, _ = self.wealth_db.lookup(detected_brand, record.logo_conf)
                    record.wealth_mult = mult

            is_yellow_plate      = False
            is_green_private     = False
            is_green_ev_taxi     = False

            for sc in record.subcomponents:
                if sc.cls_id == 0 and sc.conf > 0.45:
                    px1, py1, px2, py2 = sc.xyxy
                    pw, ph = px2 - px1, py2 - py1
                    if pw > 40 and ph > 12 and (pw / max(ph, 1)) > 1.5:
                        plate_roi = frame[py1:py2, px1:px2]
                        color_result = _detect_plate_color(plate_roi)
                        if _GROWTH_PIPELINE_ENABLED and sc.conf >= _PLATE_GATE:
                            try:
                                save_plate_crop_for_pipeline(
                                    frame, list(sc.xyxy), record.coco_class, float(sc.conf)
                                )
                            except Exception:
                                pass
                        if color_result == "yellow":
                            is_yellow_plate = True
                        elif color_result == "green_private":
                            is_green_private = True
                        elif color_result == "green_ev_taxi":
                            is_green_ev_taxi = True
                        break

            box_area   = (x2 - x1) * (y2 - y1)
            frame_area = w_frame * h_frame
            rel_size   = box_area / max(frame_area, 1)
            bbox_aspect = (x2 - x1) / max(y2 - y1, 1)

            # ── Plate color → Vehicle reclassification (Indian rules) ──
            if is_yellow_plate:
                if record.coco_class == "Car":
                    record.coco_class = "Taxi"
                elif record.coco_class in ["Truck", "Bus"]:
                    record.coco_class = "Commercial"
            elif is_green_ev_taxi:
                if record.coco_class == "Car":
                    record.coco_class = "EV Taxi"
            elif is_green_private:
                if record.coco_class == "Car":
                    record.coco_class = "EV (Private)"

            # ── Bus/Truck heuristic ──
            # Buses tend to be wider and taller than trucks
            if record.coco_class == "Truck":
                if bbox_aspect > 1.4 and (y2 - y1) > h_frame * 0.3:
                    record.coco_class = "Bus"
                elif rel_size > 0.15 and bbox_aspect > 1.2:
                    record.coco_class = "Bus"

            if record.coco_class in ["Truck", "Bus", "Commercial"]:
                if rel_size < 0.10:
                    if bbox_aspect > 1.3:
                        record.coco_class = "3-Wheeler"
                    else:
                        record.coco_class = "Small Commercial"
                else:
                    if not is_yellow_plate:
                        record.coco_class = "Heavy Commercial"

            self._track_history[int(tid)] = record
            records.append(record)

        if self._frame_idx % 100 == 0:
            print(f"[ARG] Progress: {self._frame_idx} frames processed...")
        self._frame_idx += 1

        return self._render(frame.copy(), records), records


    def _render(self, frame: np.ndarray, records: list) -> np.ndarray:
        for rec in records:
            vx1, vy1, vx2, vy2 = rec.vehicle_xyxy
            box_color = WEALTH_ALERT_COLOR if rec.wealth_mult > 2.0 else VEHICLE_BOX_COLOR
            thickness = 3 if rec.wealth_mult > 2.0 else 2
            cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), box_color, thickness)
            banner = (
                f"ID:{rec.track_id}  {rec.coco_class}  "
                f"[{rec.orientation}]  WM:{rec.wealth_mult:.1f}x"
            )
            _put_text_bg(frame, banner, (vx1, vy1 - 8), box_color)
            if rec.make_hint not in ("no logo detected", "unknown"):
                _put_text_bg(
                    frame, f"Hint: {rec.make_hint[:55]}",
                    (vx1, vy2 + 16), (30, 30, 30), font_scale=0.40,
                )
            for sc in rec.subcomponents:
                sx1, sy1, sx2, sy2 = sc.xyxy
                color = CLASS_COLORS.get(sc.cls_id, (180, 180, 180))
                cv2.rectangle(frame, (sx1, sy1), (sx2, sy2), color, 1)
                cv2.putText(
                    frame, f"{sc.cls_name} {sc.conf:.2f}",
                    (sx1, sy1 - 4), cv2.FONT_HERSHEY_SIMPLEX,
                    0.38, color, 1, cv2.LINE_AA,
                )
        _draw_hud(frame, records)
        return frame

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
        if show:
            cv2.imshow("ARG — Result", annotated)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    def run_video(self, source, output_path: Optional[str] = None, show: bool = True) -> None:
        cap = cv2.VideoCapture(source if isinstance(source, int) else str(source))
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
                live_fps = frame_idx / max(time.time() - t0, 1e-6)
                cv2.putText(
                    annotated, f"FPS: {live_fps:.1f}", (W - 115, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA,
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
                try: cv2.destroyAllWindows()
                except: pass
            elapsed = time.time() - t0
            print(f"[ARG] Processed {frame_idx} frames in {elapsed:.1f}s  "
                  f"(avg {frame_idx/max(elapsed,1e-6):.1f} FPS)")

    def run_batch(self, input_dir: str, size: int, offset: int, save_labels: bool = True, shuffle: bool = False):
        img_dir = Path(input_dir)
        # --- RECURSIVE SEARCH (V13) ---
        all_imgs = sorted([f for f in img_dir.rglob("*") if f.suffix.lower() in {".jpg", ".jpeg", ".png"}])
        
        if shuffle:
            random.shuffle(all_imgs)
        
        batch = all_imgs[offset : offset + size]
        print(f"\n[BATCH] Targeted {len(batch)} images (offset={offset}) ...")
        
        verify_dir = Path("label_verification_stage2")
        verify_dir.mkdir(exist_ok=True)
        
        # Output label directories
        label_dir_s2 = Path(r"data\labeled\stage2_dataset\labels")
        label_dir_s1 = Path(r"data\labeled\stage1_dataset\labels")
        label_dir_s2.mkdir(parents=True, exist_ok=True)
        label_dir_s1.mkdir(parents=True, exist_ok=True)

        # Mapping for Stage 1 (Vehicles) Retraining
        # COCO [2, 3, 5, 7] -> Stage1 [0, 1, 2, 3]
        s1_map = {2: 0, 3: 1, 5: 2, 7: 3}

        for idx, img_path in enumerate(batch):
            # --- AUTO-RESUME SKIP (V13) ---
            txt_name = img_path.stem + ".txt"
            if (label_dir_s2 / txt_name).exists():
                if idx % 50 == 0: print(f"  [SKIP] Already processed: {img_path.name}")
                continue

            frame = cv2.imread(str(img_path))
            if frame is None: continue
            ih, iw = frame.shape[:2]
            
            # --- FLASH-STUDIO BYPASS (V11) ---
            # If it's a studio image, we skip Stage 1 (YOLO) entirely
            if img_path.name.startswith("Studio_"):
                # Mock a vehicle record for the entire frame
                # Classes: Car=2, Motorcycle=3, Bus=5, Truck=7. 
                # Studio names usually start with "Studio_Car_" or "Studio_2wheeler_"
                if "2wheeler" in img_path.name.lower(): coco_id = 3
                elif "heavy" in img_path.name.lower(): coco_id = 7
                elif "3wheeler" in img_path.name.lower(): coco_id = 5
                else: coco_id = 2 # Default to car
                
                # Aspect Ratio for side-hint
                aspect = iw / max(ih, 1)
                is_side = (aspect > 1.5)
                
                # Direct Stage 2
                gd_results = self._run_gdino_on_roi(frame, vehicle_type="Vehicle", is_side_hint=is_side)
                subcomps = []
                for res in gd_results:
                    cx_c, cy_c, bw_c, bh_c = res["box"]
                    subcomps.append(SubComponent(
                        cls_id=res["cls"], cls_name=SUBCOMP_CLASSES.get(res["cls"], "part"),
                        conf=res["conf"], xyxy=np.array([
                            int((cx_c - bw_c/2)*iw), int((cy_c - bh_c/2)*ih),
                            int((cx_c + bw_c/2)*iw), int((cy_c + bh_c/2)*ih)
                        ])
                    ))
                records = [VehicleRecord(
                    track_id=0, coco_class="Vehicle", coco_id=coco_id,
                    vehicle_xyxy=np.array([0, 0, iw, ih]), subcomponents=subcomps
                )]
                # ATOMIC SPEED: Skip Rendering and Analysis for Studio mode
                annotated_frame = frame.copy() 
            else:
                annotated_frame, records = self.process_frame(frame, persist=False)
            
            if save_labels:
                # TURBO: Sample verification images (1 in 25) to save Disk IO
                if idx % 25 == 0 or idx < 5:
                    cv2.imwrite(str(verify_dir / img_path.name), annotated_frame)
                ih, iw = frame.shape[:2]
                
                # ── SAVE STAGE 2 (Components) ──
                lbl_path_s2 = label_dir_s2 / (img_path.stem + ".txt")
                with open(lbl_path_s2, "w") as f2:
                    for rec in records:
                        for sc in rec.subcomponents:
                            x1, y1, x2, y2 = sc.xyxy
                            bw = (x2 - x1) / iw
                            bh = (y2 - y1) / ih
                            cx = (x1 + x2) / (2 * iw)
                            cy = (y1 + y2) / (2 * ih)
                            f2.write(f"{sc.cls_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

                # ── SAVE STAGE 1 (Vehicles) ──
                lbl_path_s1 = label_dir_s1 / (img_path.stem + ".txt")
                with open(lbl_path_s1, "w") as f1:
                    for rec in records:
                        # Map COCO ID back to Stage 1 Training ID
                        s1_cls = s1_map.get(rec.coco_id, 0)
                        rx1, ry1, rx2, ry2 = rec.vehicle_xyxy
                        bw = (rx2 - rx1) / iw
                        bh = (ry2 - ry1) / ih
                        cx = (rx1 + rx2) / (2 * iw)
                        cy = (ry1 + ry2) / (2 * ih)
                        f1.write(f"{s1_cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

            print(f"\r  [{idx+1}/{len(batch)}] {img_path.name} processed", end="", flush=True)
        print(f"\n[DONE] Batch finished. Check: {verify_dir}")


def classify_logo_crop(logo_roi: np.ndarray, vehicle_type: str = "Car") -> tuple:
    if logo_roi is None or logo_roi.size == 0:
        return "unknown", 0.0
    h, w = logo_roi.shape[:2]
    if h < 10 or w < 10:
        return "unknown", 0.0
    aspect = w / max(h, 1)
    total_px = max(h * w, 1)
    hsv = cv2.cvtColor(logo_roi, cv2.COLOR_BGR2HSV)
    blue_mask = cv2.inRange(hsv, np.array([100, 80, 60]), np.array([130, 255, 255]))
    blue_ratio = cv2.countNonZero(blue_mask) / total_px
    orange_mask = cv2.inRange(hsv, np.array([5, 150, 100]), np.array([20, 255, 255]))
    orange_ratio = cv2.countNonZero(orange_mask) / total_px
    white_mask = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 30, 255]))
    white_ratio = cv2.countNonZero(white_mask) / total_px
    green_mask = cv2.inRange(hsv, np.array([40, 50, 20]), np.array([85, 255, 150]))
    green_ratio = cv2.countNonZero(green_mask) / total_px
    bright_green_mask = cv2.inRange(hsv, np.array([40, 80, 100]), np.array([85, 255, 255]))
    bright_green_ratio = cv2.countNonZero(bright_green_mask) / total_px
    gold_mask = cv2.inRange(hsv, np.array([15, 100, 100]), np.array([35, 255, 255]))
    gold_ratio = cv2.countNonZero(gold_mask) / total_px
    navy_mask = cv2.inRange(hsv, np.array([100, 60, 30]), np.array([130, 255, 120]))
    navy_ratio = cv2.countNonZero(navy_mask) / total_px
    red_mask1 = cv2.inRange(hsv, np.array([0, 120, 100]), np.array([10, 255, 255]))
    red_mask2 = cv2.inRange(hsv, np.array([165, 120, 100]), np.array([180, 255, 255]))
    red_ratio = (cv2.countNonZero(red_mask1) + cv2.countNonZero(red_mask2)) / total_px
    chrome_mask = cv2.inRange(hsv, np.array([0, 0, 80]), np.array([180, 30, 220]))
    chrome_ratio = cv2.countNonZero(chrome_mask) / total_px
    black_mask = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 255, 50]))
    black_ratio = cv2.countNonZero(black_mask) / total_px
    dark_ratio = (cv2.countNonZero(black_mask) +
                  cv2.countNonZero(cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 255, 80])))) / total_px
    gray     = cv2.cvtColor(logo_roi, cv2.COLOR_BGR2GRAY)
    clahe    = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)
    edges    = cv2.Canny(enhanced, 40, 120)
    edge_density = cv2.countNonZero(edges) / total_px
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    circular_blobs = 0
    for cnt in contours:
        area  = cv2.contourArea(cnt)
        perim = cv2.arcLength(cnt, True)
        if perim == 0: continue
        if (4 * np.pi * area / perim ** 2) > 0.55 and area > 30:
            circular_blobs += 1
    top_half   = edges[:h//2,  :]
    bot_half   = edges[h//2:,  :]
    left_half  = edges[:, :w//2]
    right_half = edges[:, w//2:]
    top_edge_ratio   = cv2.countNonZero(top_half)  / max(top_half.size,   1)
    bot_edge_ratio   = cv2.countNonZero(bot_half)  / max(bot_half.size,   1)
    left_edge_ratio  = cv2.countNonZero(left_half) / max(left_half.size,  1)
    right_edge_ratio = cv2.countNonZero(right_half)/ max(right_half.size, 1)
    symmetry = 1.0 - abs(left_edge_ratio - right_edge_ratio) / max(
        left_edge_ratio + right_edge_ratio, 1e-5)
    center_region = edges[h//4:3*h//4, w//4:3*w//4]
    center_density = cv2.countNonZero(center_region) / max(center_region.size, 1)
    mid_col_start = w//2 - w//10
    mid_col_end   = w//2 + w//10
    mid_strip     = edges[:, max(0, mid_col_start):min(w, mid_col_end)]
    mid_gap_ratio = cv2.countNonZero(mid_strip) / max(mid_strip.size, 1)

    if vehicle_type == "Motorcycle":
        if orange_ratio > 0.20: return "ktm", 0.92
        left_hsv  = hsv[:, :w//2]
        right_hsv = hsv[:, w//2:]
        left_blue = cv2.countNonZero(cv2.inRange(left_hsv, np.array([100, 80, 60]), np.array([130, 255, 255]))) / max(left_hsv.size, 1)
        right_red = (cv2.countNonZero(cv2.inRange(right_hsv, np.array([0, 120, 100]), np.array([10, 255, 255]))) +
                     cv2.countNonZero(cv2.inRange(right_hsv, np.array([165, 120, 100]), np.array([180, 255, 255])))) / max(right_hsv.size, 1)
        if (left_blue > 0.15 and right_red > 0.10 and aspect > 1.5) or (blue_ratio > 0.10 and red_ratio > 0.08):
            return "tvs", 0.85
        if circular_blobs >= 1 and dark_ratio > 0.45 and 0.85 < aspect < 1.15 and edge_density > 0.30:
            return "kawasaki", 0.78
        if aspect > 2.5 and white_ratio > 0.25 and circular_blobs == 0:
            return "kawasaki", 0.80
        if white_ratio > 0.20 and aspect > 1.3 and top_edge_ratio > bot_edge_ratio * 1.2 and circular_blobs == 0:
            return "honda", 0.80
        if red_ratio > 0.35 and circular_blobs >= 1 and aspect < 1.1:
            return "ducati", 0.88
        
        # ROYAL ENFIELD: Stricter check. 
        # RE badges are circular, but we now require higher chrome + dark ring symmetry
        if circular_blobs >= 1 and chrome_ratio > 0.45 and 0.9 < aspect < 1.1:
            # Reject if it looks like a vertical bottle (high vertical orientation)
            if top_edge_ratio < 0.05 and bot_edge_ratio < 0.05: # empty-ish logo often isn't a badge
                return "unknown", 0.0
            return "royal_enfield", 0.78
        
        if circular_blobs >= 1 and top_edge_ratio > bot_edge_ratio * 1.5 and chrome_ratio > 0.35:
            return "yamaha", 0.72
        mid_row = edges[h//2 - h//8 : h//2 + h//8, :]
        if cv2.countNonZero(mid_row) / max(mid_row.size, 1) > 0.25 and circular_blobs == 0:
            return "hero", 0.68
        if dark_ratio > 0.30 and 0.8 < aspect < 1.6 and circular_blobs == 0 and edge_density > 0.22:
            return "bajaj", 0.62
        if aspect < 0.95 and symmetry < 0.65 and chrome_ratio > 0.25:
            return "suzuki", 0.65
        if aspect < 0.90 and dark_ratio > 0.20 and chrome_ratio > 0.20 and top_edge_ratio > bot_edge_ratio * 1.2:
            return "harley_davidson", 0.65
        if 0.8 < aspect < 1.4 and chrome_ratio > 0.35 and circular_blobs == 0 and top_edge_ratio > bot_edge_ratio * 1.3:
            return "triumph", 0.62
        if circular_blobs >= 1 and chrome_ratio > 0.30 and 1.3 < aspect < 2.2:
            return "jawa", 0.58
    else:
        if bright_green_ratio > 0.30: return "landrover", 0.88
        if green_ratio > 0.10 and dark_ratio > 0.20 and circular_blobs >= 1: return "skoda", 0.84
        if dark_ratio > 0.35 and gold_ratio > 0.12: return "lamborghini", 0.85
        if red_ratio > 0.15 and gold_ratio > 0.08: return "porsche", 0.83
        if blue_ratio > 0.15 and white_ratio > 0.15 and circular_blobs >= 1: return "bmw", 0.85
        if navy_ratio > 0.25 and circular_blobs >= 1 and blue_ratio < 0.10: return "volkswagen", 0.78
        if aspect > 2.5 and circular_blobs >= 3: return "audi", 0.82
        if (circular_blobs >= 1 and edge_density > 0.20 and 0.85 < aspect < 1.15): return "mercedes", 0.75
        if red_ratio > 0.20 and circular_blobs >= 1: return "kia", 0.70
        if 1.2 < aspect < 2.0 and 2 <= circular_blobs <= 4 and chrome_ratio > 0.25: return "toyota", 0.60
        if aspect < 0.95 and symmetry < 0.65 and (chrome_ratio > 0.25 or black_ratio > 0.25): return "maruti", 0.45
        if top_edge_ratio > bot_edge_ratio * 1.5 and aspect < 1.2 and chrome_ratio > 0.20: return "tata", 0.42

    return "unknown", 0.20


def classify_grille_crop(grille_roi: np.ndarray) -> tuple:
    if grille_roi is None or grille_roi.size == 0:
        return "unknown", 0.0
    h, w = grille_roi.shape[:2]
    if w < 20 or h < 10: return "unknown", 0.0
    gray = cv2.cvtColor(grille_roi, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    aspect = w / max(h, 1)
    mid_y = h // 2
    top_w = cv2.countNonZero(edges[:h//4, :])
    mid_w = cv2.countNonZero(edges[mid_y-h//8:mid_y+h//8, :])
    bot_w = cv2.countNonZero(edges[3*h//4:, :])
    if top_w > mid_w * 1.5 and bot_w > mid_w * 1.5:
        return "lexus", 0.75
    v_proj = np.sum(edges, axis=0)
    peaks = 0
    in_peak = False
    for val in v_proj:
        if val > np.mean(v_proj) * 1.2:
            if not in_peak:
                peaks += 1
                in_peak = True
        else:
            in_peak = False
    if 12 <= peaks <= 16: return "jeep", 0.80
    if 10 <= peaks <= 11: return "mahindra", 0.70
    if aspect < 1.4 and np.mean(gray) > 160:
        return "rolls-royce", 0.85
    if aspect < 1.3 and cv2.countNonZero(edges[:h//2, :]) > cv2.countNonZero(edges[h//2:, :]) * 1.8:
        return "alfa romeo", 0.70
    if 0.5 < aspect < 1.2:
        center_strip = edges[:, w//3:2*w//3]
        if cv2.countNonZero(center_strip) > cv2.countNonZero(edges) * 0.6:
            return "bugatti", 0.90
    if aspect > 1.8:
        mid_top = edges[:h//4, w//3:2*w//3]
        mid_bot = edges[3*h//4:, w//3:2*w//3]
        if cv2.countNonZero(mid_top) < 5 and cv2.countNonZero(mid_bot) < 5:
            return "kia", 0.65
    return "unknown", 0.0


def classify_lighting_signature(hl_roi: np.ndarray) -> str:
    if hl_roi is None or hl_roi.size == 0: return "unknown"
    gray = cv2.cvtColor(hl_roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    h, w = thresh.shape[:2]
    top_bar  = cv2.countNonZero(thresh[:h//3, :])
    mid_stem = cv2.countNonZero(thresh[:, w//3:2*w//3])
    if top_bar > (h*w)*0.10 and mid_stem > (h*w)*0.10:
        return "volvo"
    return "unknown"


def classify_bike_signature(bike_roi: np.ndarray, headlmps: list) -> tuple:
    """Detects KTM (Orange), Kawasaki (Green) by dominant body colour.
    Royal Enfield round-lamp check requires pre-cropped lamp ROIs and is
    deferred to a future refactor — the old placeholder that returned
    'royal enfield?' for ANY bike with detected headlamps has been removed.
    """
    if bike_roi is None or bike_roi.size == 0: return "unknown", 0.0

    hsv = cv2.cvtColor(bike_roi, cv2.COLOR_BGR2HSV)
    total_px = max(bike_roi.shape[0] * bike_roi.shape[1], 1)

    # 1. KTM ORANGE
    ktm_mask = cv2.inRange(hsv, np.array([5, 150, 100]), np.array([20, 255, 255]))
    if cv2.countNonZero(ktm_mask) / total_px > 0.12:
        return "ktm", 0.85

    # 2. KAWASAKI GREEN
    kawa_mask = cv2.inRange(hsv, np.array([35, 100, 100]), np.array([75, 255, 255]))
    if cv2.countNonZero(kawa_mask) / total_px > 0.15:
        return "kawasaki", 0.82

    # 3. ROYAL ENFIELD — needs properly cropped headlamp ROI for roundness
    # check; skip until classify_bike_signature receives pre-cropped ROIs.

    return "unknown", 0.0


def _detect_plate_color(plate_roi: np.ndarray) -> str:
    if plate_roi.size == 0:
        return "unknown"
    hsv = cv2.cvtColor(plate_roi, cv2.COLOR_BGR2HSV)
    yellow_mask = cv2.inRange(hsv, np.array([18, 120, 120]), np.array([35, 255, 255]))
    green_mask  = cv2.inRange(hsv, np.array([40, 60,  60]),  np.array([85, 255, 255]))
    total_px = max(plate_roi.shape[0] * plate_roi.shape[1], 1)
    yellow_ratio = cv2.countNonZero(yellow_mask) / total_px
    green_ratio  = cv2.countNonZero(green_mask)  / total_px
    if green_ratio > 0.25:
        if yellow_ratio > 0.05:
            return "green_ev_taxi"
        else:
            return "green_private"
    elif yellow_ratio > 0.30:
        return "yellow"
    else:
        return "white"


def _is_yellow_plate(plate_roi: np.ndarray) -> bool:
    return _detect_plate_color(plate_roi) == "yellow"


def _put_text_bg(img, text, origin, bg_color=(0,0,0), font_scale=0.45, thickness=1):
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = origin
    cv2.rectangle(img, (x, y - th - baseline - 2), (x + tw + 4, y + 2), bg_color, cv2.FILLED)
    cv2.putText(img, text, (x + 2, y - baseline), font, font_scale, (255,255,255), thickness, cv2.LINE_AA)


def _draw_hud(frame: np.ndarray, records: list) -> None:
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
    cv2.rectangle(overlay, (4, 4), (330, 4 + len(lines) * lh + 8), (10,10,10), cv2.FILLED)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)
    for i, line in enumerate(lines):
        color = (0, 255, 180) if i == 0 else (200, 200, 200)
        cv2.putText(frame, line, (x0, y0 + i * lh), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)


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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="ARG Hierarchical Multi-Object Detection System",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--source", required=True)
    p.add_argument("--vehicle-model", default=DEFAULT_VEHICLE_MODEL)
    p.add_argument("--subcomp-model", default=DEFAULT_SUBCOMP_MODEL)
    p.add_argument("--csv", default=DEFAULT_CSV)
    p.add_argument("--output", default=None)
    p.add_argument("--vehicle-conf", type=float, default=VEHICLE_CONF)
    p.add_argument("--subcomp-conf", type=float, default=SUBCOMP_CONF)
    p.add_argument("--no-show", action="store_true")
    p.add_argument("--duration", type=int, default=0)
    p.add_argument("--annotate", action="store_true")
    p.add_argument("--size", type=int, default=10)
    p.add_argument("--offset", type=int, default=0, help="Start processing from this index")
    p.add_argument("--shuffle", action="store_true", help="Shuffle images before batching")
    p.add_argument("--auto-label", action="store_true")
    return p


def main():
    args = build_parser().parse_args()
    detector = HierarchicalDetector(
        vehicle_model_path = args.vehicle_model,
        subcomp_model_path = args.subcomp_model,
        csv_path           = args.csv,
        vehicle_conf       = args.vehicle_conf,
        subcomp_conf       = args.subcomp_conf,
        use_gdino          = True   # Force GDINO for sub-components
    )

    detector.duration = args.duration

    if args.annotate:
        source_dir = args.source if os.path.isdir(args.source) else r"data\labeled\vehicle_dataset\train\images"
        detector.run_batch(input_dir=source_dir, size=args.size, offset=args.offset, shuffle=args.shuffle)
        return

    source = args.source
    try:
        source   = int(source)
        is_video = True
    except ValueError:
        is_video = Path(source).suffix.lower() not in {
            ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"
        }

    if is_video:
        detector.run_video(source=source, output_path=args.output, show=not args.no_show)
    else:
        detector.run_image(image_path=source, output_path=args.output, show=not args.no_show)


if __name__ == "__main__":
    main()
