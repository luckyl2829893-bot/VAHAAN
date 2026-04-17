"""
annotate_batch.py
=================
VAHAAN — Batch annotation using YOLOv11m (COCO).

Switched from Grounded DINO to yolo11m.pt because DINO was:
- Labeling tractors/commercial trucks as motorcycle
- Confusing truck vs bus
- Missing detections on cars

yolo11m.pt is trained on COCO which includes all vehicle types natively.

COCO → ARG class mapping:
  COCO 1  (bicycle)    → ARG 1 (2wheeler)
  COCO 2  (car)        → ARG 0 (car)
  COCO 3  (motorcycle) → ARG 1 (2wheeler)
  COCO 5  (bus)        → ARG 3 (bus)
  COCO 7  (truck)      → ARG 4 (truck)
  COCO 0  (person)     → skip
  anything else        → skip

Usage:
  # Annotate 500 random images, check verification, then commit:
  python annotate_batch.py --size 500

  # Commit staged labels:
  python annotate_batch.py --size 500 --commit

  # Next batch:
  python annotate_batch.py --size 500 --offset 500
"""

import argparse
import random
import shutil
import cv2
import numpy as np
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
IMAGE_DIR   = Path(r"C:\Users\laksh\Desktop\image\data\labeled\vehicle_dataset\train\images")
LABEL_DIR   = Path(r"C:\Users\laksh\Desktop\image\data\labeled\vehicle_dataset\train\labels")
STAGING_DIR = Path(r"C:\Users\laksh\Desktop\image\annotation_staging")
VERIFY_DIR  = Path(r"C:\Users\laksh\Desktop\image\label_verification")
YOLO_MODEL  = Path(r"C:\Users\laksh\Desktop\image\yolo11m.pt")

# COCO → ARG class ID ──────────────────────────────────────────────────────────
# ARG: 0=car, 1=2wheeler, 2=ambulance, 3=bus, 4=truck, 5=3wheeler
COCO_TO_ARG = {
    1:  1,   # bicycle   → 2wheeler
    2:  0,   # car       → car
    3:  1,   # motorcycle→ 2wheeler
    5:  3,   # bus       → bus
    7:  4,   # truck     → truck
    # Note: COCO has no auto-rickshaw class; handled via filename rules
}
SKIP_CLASSES = {0, 4, 6}   # person, airplane, train etc. — ignore

# ── Per-class confidence thresholds ───────────────────────────────────────────
# Bus raised high because Indian trucks get misclassified as bus by COCO
CONF_PER_COCO_CLASS = {
    1:  0.28,   # bicycle   → catch distant ones
    2:  0.35,   # car
    3:  0.28,   # motorcycle→ catch distant ones
    5:  0.70,   # bus       → very high gate to prevent car/truck→bus
    7:  0.50,   # truck     → increased to 0.50 to reduce car→truck errors
}
CONF_DEFAULT = 0.35  # fallback for any other COCO class

# ── Names and colors for visualization ────────────────────────────────────────
CLASS_NAMES = {0: "car", 1: "2wheeler", 2: "ambulance", 3: "bus", 4: "truck", 5: "3wheeler"}
COLORS = {
    0: (0, 200, 80),    # green  - car
    1: (0, 120, 255),   # blue   - 2wheeler
    2: (0, 0, 255),     # red    - ambulance
    3: (255, 180, 0),   # orange - bus
    4: (180, 0, 255),   # purple - truck
    5: (0, 220, 220),   # cyan   - 3wheeler
}


def load_model():
    from ultralytics import YOLO
    print(f"Loading yolo11m.pt (COCO)...")
    model = YOLO(str(YOLO_MODEL))
    print("Model ready.\n")
    return model


# ── Filename → forced class (use YOLO only for box, not class) ─────────────────
# Priority order: first match wins
FILENAME_CLASS_RULES = [
    # Ambulances — must be before generic patterns
    ("ambulance",           2),
    ("Ambulance",           2),
    # Buses
    ("Generic_bus-",        3),
    # Truck-specific files
    ("Mitsubishi-Fuso",     4), ("mitsubishi-fuso", 4),
    ("shaktiman",           4), ("cutting-sticker-truck", 4),
    ("afrit-trailers",      4), ("Generic_LCV",      4),
    # 3-Wheelers (auto-rickshaw) — after bike brands but before generic car
    ("rickshaw",             5),
    ("auto-rickshaw",        5),
    ("auto-rikshaw",         5),
    ("3wheeler",             5),
    ("3-wheeler",            5),
    ("Datacluster Labs Auto", 5),
    ("auto",                5),
    ("tuk-tuk",             5),
    # Bike brands
    ("Generic_Bajaj_",      1), ("Generic_Hero_",    1),
    ("Generic_Honda_CB",    1), ("Generic_Honda_Shine", 1),
    ("Generic_Honda_SP",    1), ("Generic_Honda_Livo", 1),
    ("Generic_Honda_Unicorn", 1), ("Generic_KTM_",  1),
    ("Generic_Kawasaki_",   1), ("Generic_Royal_Enfield_", 1),
    ("Generic_Suzuki_Gixxer", 1), ("Generic_Triumph_", 1),
    ("Generic_Yamaha_",     1), ("Generic_Ola_",    1),
    ("Generic_Ather_",      1),
    ("bicycle",             1), ("two-wheeler",      1),
    ("2-wheeler",           1),
    ("Generic_Datacluster", 1),  # Defaulting Datacluster to 2wheeler if not 'Auto'
    # Car brands — always class 0
    ("Audi_",               0), ("Bmw_",             0),
    ("Honda_Honda_",        0), ("Hyundai_Hyundai_", 0),
    ("Kia_Kia_",            0), ("Lamborghini_",     0),
    ("Land-rover_",         0), ("Mahindra_Mahindra_", 0),
    ("Maruti_Maruti_",      0), ("Tata_Tata_",       0),
    ("Toyota_Toyota_",      0), ("Porsche_",         0),
    ("Skoda_",              0), ("Volkswagen_",      0),
    ("Generic_Mercedes",    0), ("Generic_Audi_",    0),
    ("Generic_BMW_",        0), ("Generic_car-wbs-", 0),
    ("Generic_car-ybs-",    0), ("Generic_angle_",   0),
]


def get_iou(boxA, boxB):
    # box = [cls, cx, cy, w, h] in normalized units
    wA, hA = boxA[3], boxA[4]
    wB, hB = boxB[3], boxB[4]
    xA1, yA1 = boxA[1] - wA/2, boxA[2] - hA/2
    xA2, yA2 = boxA[1] + wA/2, boxA[2] + hA/2
    xB1, yB1 = boxB[1] - wB/2, boxB[2] - hB/2
    xB2, yB2 = boxB[1] + wB/2, boxB[2] + hB/2
    
    x_inter1 = max(xA1, xB1)
    y_inter1 = max(yA1, yB1)
    x_inter2 = min(xA2, xB2)
    y_inter2 = min(yA2, yB2)
    
    interArea = max(0, x_inter2 - x_inter1) * max(0, y_inter2 - y_inter1)
    boxAArea = wA * hA
    boxBArea = wB * hB
    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou

def apply_nms(boxes):
    """Simple greedy NMS to remove overlapping boxes from different classes."""
    if not boxes: return []
    # Sort by 'area' as a proxy for confidence since we don't pass conf here, 
    # but actually we should just keep the first ones. 
    # Better: we keep the ones with higher class priority.
    # For now, let's just suppress high overlaps.
    boxes = sorted(boxes, key=lambda x: x[3]*x[4], reverse=True)
    keep = []
    for i in range(len(boxes)):
        discard = False
        for j in range(len(keep)):
            if get_iou(boxes[i], keep[j]) > 0.5:
                discard = True
                break
        if not discard:
            keep.append(boxes[i])
    return keep

def get_filename_class(fname: str):
    """Return forced class if filename clearly indicates vehicle type, else None."""
    fn = fname.lower()
    for keyword, cls_id in FILENAME_CLASS_RULES:
        if keyword.lower() in fn:
            return cls_id
    return None  # use YOLO prediction for generic/video frames


def annotate_one(model, img_path: Path) -> list:
    """Run YOLO on one image, return list of (arg_class, cx, cy, w, h)."""
    # Run with the lowest threshold, filter per-class below
    results = model(str(img_path), conf=min(CONF_PER_COCO_CLASS.values()), verbose=False)[0]
    ih, iw = results.orig_shape

    fname_lower = img_path.name.lower()
    forced_class = get_filename_class(img_path.name)
    is_ambulance = "ambulance" in fname_lower

    raw = []
    for box in results.boxes:
        coco_cls = int(box.cls.item())
        if coco_cls not in COCO_TO_ARG:
            continue
        # Per-class confidence gate
        conf = float(box.conf.item())
        required_conf = CONF_PER_COCO_CLASS.get(coco_cls, CONF_DEFAULT)
        if conf < required_conf:
            continue

        x1, y1, x2, y2 = box.xyxy[0].tolist()
        cx = ((x1 + x2) / 2) / iw
        cy = ((y1 + y2) / 2) / ih
        w  = (x2 - x1) / iw
        h  = (y2 - y1) / ih
        if w < 0.02 or h < 0.02:
            continue
        
        # Initial class from COCO
        cls = COCO_TO_ARG[coco_cls]
        
        # Heuristic: If it's a generic car folder or Audi/BMW, and YOLO says Truck/Bus 
        # with borderline confidence, it's probably just a big SUV/German car.
        if forced_class == 0 and cls in [3, 4] and conf < 0.7:
               cls = 0

        raw.append([cls, cx, cy, w, h])

    if not raw:
        if forced_class is not None:
            return [(forced_class, 0.5, 0.5, 0.85, 0.85)]
        return []

    # 1. Apply NMS to remove double-annotations (overlaps)
    raw = apply_nms(raw)

    # 2. Apply forced overrides for special image types (Ambulance/Brands)
    if is_ambulance:
        # For ambulances, only override the LARGEST detection
        largest_idx = max(range(len(raw)), key=lambda i: raw[i][3] * raw[i][4])
        for i in range(len(raw)):
            if i == largest_idx:
                raw[i][0] = 2 # force ambulance
    elif forced_class is not None:
        # For brand folders (Audi, BMW etc), override ALL detections
        for i in range(len(raw)):
            raw[i][0] = forced_class

    return [tuple(r) for r in raw]






def draw_verification(img_path: Path, annotations: list, out_path: Path):
    img = cv2.imread(str(img_path))
    if img is None:
        return
    ih, iw = img.shape[:2]
    for cls_id, cx, cy, bw, bh in annotations:
        x1 = int((cx - bw / 2) * iw)
        y1 = int((cy - bh / 2) * ih)
        x2 = int((cx + bw / 2) * iw)
        y2 = int((cy + bh / 2) * ih)
        color = COLORS.get(cls_id, (128, 128, 128))
        label = CLASS_NAMES.get(cls_id, str(cls_id))
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(img, label, (x1, max(y1 - 6, 14)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)
    cv2.imwrite(str(out_path), img)


def run_batch(args):
    # Clear staging so old runs don't mix in
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(exist_ok=True)
    # Clear verification folder each run
    if VERIFY_DIR.exists():
        shutil.rmtree(VERIFY_DIR)
    VERIFY_DIR.mkdir(exist_ok=True)

    all_imgs = sorted([
        f for f in IMAGE_DIR.glob("*")
        if f.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ])
    random.shuffle(all_imgs)

    batch = all_imgs[args.offset: args.offset + args.size]
    print(f"Total images: {len(all_imgs)}")
    print(f"Batch: offset={args.offset}, size={args.size} → {len(batch)} images\n")

    if not batch:
        print("No images in this range. Check --offset and --size.")
        return

    model = load_model()

    verify_picks = set(random.sample(range(len(batch)), min(30, len(batch))))
    counts = {i: 0 for i in range(6)}
    no_detections = 0

    for idx, img_path in enumerate(batch):
        try:
            annotations = annotate_one(model, img_path)
        except Exception as e:
            print(f"\n  ERROR {img_path.name}: {e}")
            continue

        if not annotations:
            no_detections += 1
        else:
            staging_lbl = STAGING_DIR / (img_path.stem + ".txt")
            lines = [f"{c} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"
                     for c, cx, cy, w, h in annotations]
            staging_lbl.write_text("\n".join(lines) + "\n")
            for cls_id, *_ in annotations:
                counts[cls_id] += 1

        if idx in verify_picks:
            draw_verification(img_path, annotations or [],
                              VERIFY_DIR / img_path.name)

        if (idx + 1) % 50 == 0 or (idx + 1) == len(batch):
            print(f"\r  [{idx+1}/{len(batch)}] processed", end="", flush=True)

    print(f"\n\nBatch done.")
    print(f"  No detections: {no_detections}/{len(batch)}")
    print(f"\nClass distribution:")
    print(f"  0 car:      {counts[0]}")
    print(f"  1 2wheeler: {counts[1]}")
    print(f"  2 ambulance:{counts[2]}")
    print(f"  3 bus:      {counts[3]}")
    print(f"  4 truck:    {counts[4]}")
    print(f"  5 3wheeler: {counts[5]}")
    print(f"  5 3wheeler: {counts[5]}")
    print(f"\n✅ Check verification images → {VERIFY_DIR}")
    print(f"\nIf labels look GOOD:")
    print(f"  python annotate_batch.py --commit")
    print(f"\nNext batch:")
    print(f"  python annotate_batch.py --size {args.size} --offset {args.offset + args.size}")


def commit_batch(args):
    staged = list(STAGING_DIR.glob("*.txt"))
    if not staged:
        print("Nothing in staging to commit.")
        return
    for f in staged:
        shutil.copy(f, LABEL_DIR / f.name)
    print(f"✅ Committed {len(staged)} labels → {LABEL_DIR}")
    shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir()
    print("Staging cleared. Ready for next batch.")


def main():
    parser = argparse.ArgumentParser(description="ARG Batch Annotation (yolo11m COCO)")
    parser.add_argument("--size",   type=int, default=500, help="Batch size")
    parser.add_argument("--offset", type=int, default=0,   help="Start offset")
    parser.add_argument("--commit", action="store_true",   help="Commit staged labels")
    parser.add_argument("--full",   action="store_true",
                        help="Annotate ALL images at once (no batching, auto-commits)")
    args = parser.parse_args()

    if args.commit:
        commit_batch(args)
    elif args.full:
        args.size = 999999   # effectively unlimited
        args.offset = 0
        run_batch(args)
        commit_batch(args)
        print("\n✅ Full annotation complete and committed.")
    else:
        run_batch(args)


if __name__ == "__main__":
    main()
