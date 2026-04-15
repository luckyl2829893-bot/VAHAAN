import os
import sys
import cv2
import random
import torch
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from ultralytics import YOLO

# ── Paths ──────────────────────────────────────────────────────────────────────
IMAGE_DIR   = Path(r"C:\Users\laksh\Desktop\image\data\labeled\vehicle_dataset\train\images")
LABEL_DIR   = Path(r"C:\Users\laksh\Desktop\image\data\labeled\stage2_dataset\labels")
VERIFY_DIR  = Path(r"C:\Users\laksh\Desktop\image\label_verification_stage2")
STAGE1_MODEL= Path(r"yolo11m.pt")
GDINO_DIR   = Path(r"C:\Users\laksh\Desktop\image\models\gdino")

LABEL_DIR.mkdir(parents=True, exist_ok=True)
VERIFY_DIR.mkdir(parents=True, exist_ok=True)

# ── Grounding DINO Config ──────────────────────────────────────────────────────
CONFIG_PATH  = GDINO_DIR / "GroundingDINO_SwinT_OGC.py"
WEIGHTS_PATH = GDINO_DIR / "groundingdino_swint_ogc.pth"
CAPTION      = "license plate . vehicle logo . radiator grille . headlight . taillight"
BOX_THRESHOLD = 0.35
TEXT_THRESHOLD = 0.25

# ── Stage 2 Class Map ──────────────────────────────────────────────────────────
# Matches src/pipeline/inference_heirarchical.py
STAGE2_MAP = {
    "license plate": 0,
    "plate": 0,
    "logo": 1,
    "brand logo": 1,
    "vehicle logo": 1,
    "grille": 2,
    "radiator grille": 2,
    "headlight": 3,
    "headlamp": 3,
    "taillight": 4,
    "taillamp": 4
}
COLORS = {0: (255, 255, 0), 1: (0, 255, 255), 2: (255, 0, 255), 3: (0, 255, 0), 4: (0, 0, 255)}

def load_gdino():
    from groundingdino.util.inference import load_model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[GDINO] Loading on {device}...")
    return load_model(str(CONFIG_PATH), str(WEIGHTS_PATH), device=device)

def phrase_to_id(phrase: str) -> int:
    p = phrase.lower()
    for key, val in STAGE2_MAP.items():
        if key in p: return val
    return -1

def annotate_crop(gdino_model, crop_img):
    from groundingdino.util.inference import predict, preprocess_caption
    import groundingdino.datasets.transforms as T
    
    from PIL import Image
    # Preprocess image for GDINO
    transform = T.Compose([
        T.RandomResize([800], max_size=1333),
        T.ToTensor(),
        T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    
    # GDINO transforms expect a PIL Image, not a numpy array
    pil_img = Image.fromarray(cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB))
    image_transformed, _ = transform(pil_img, None)
    
    boxes, logits, phrases = predict(
        model=gdino_model,
        image=image_transformed,
        caption=CAPTION,
        box_threshold=BOX_THRESHOLD,
        text_threshold=TEXT_THRESHOLD,
        device=str(gdino_model.device)
    )
    
    results = []
    for box, phrase, logit in zip(boxes, phrases, logits):
        cls_id = phrase_to_id(phrase)
        if cls_id != -1:
            results.append({"cls": cls_id, "box": box.tolist(), "conf": float(logit)})
    return results

import argparse

def main():
    parser = argparse.ArgumentParser(description="ARG Stage 2 Auto-Annotator")
    parser.add_argument("--size", type=int, default=10, help="Number of images to process")
    parser.add_argument("--offset", type=int, default=0, help="Starting index")
    parser.add_argument("--full", action="store_true", help="Process all images")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle images before picking")
    args = parser.parse_args()

    print("="*60)
    print("  ARG STAGE 2 AUTO-ANNOTATOR (Hierarchical)")
    print("="*60)
    
    # 1. Load Models
    s1_model = YOLO(STAGE1_MODEL)
    try:
        gd_model = load_gdino()
    except ImportError:
        print("❌ Error: groundingdino-py not installed. Run 'pip install groundingdino-py'")
        return

    # 2. Get images
    all_imgs = sorted(list(IMAGE_DIR.glob("*")))
    if args.shuffle:
        random.shuffle(all_imgs)
    
    if args.full:
        test_imgs = all_imgs[args.offset:]
    else:
        test_imgs = all_imgs[args.offset : args.offset + args.size]
    
    print(f"Batch: offset={args.offset}, size={len(test_imgs)} → {len(test_imgs)} images")

    for idx, img_path in enumerate(test_imgs):
        img0 = cv2.imread(str(img_path))
        if img0 is None: continue
        ih, iw = img0.shape[:2]
        
        # Stage 1: Find Vehicles
        s1_results = s1_model(img0, verbose=False, conf=0.4)[0]
        full_annotations = []
        
        for box in s1_results.boxes:
            c_coco = int(box.cls.item())
            if c_coco not in [2, 3, 5, 7]: continue # car, motor, bus, truck
            
            # Crop ROI
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(iw, x2), min(ih, y2)
            crop = img0[y1:y2, x1:x2]
            cw, ch = x2-x1, y2-y1
            if cw < 20 or ch < 20: continue
            
            # Stage 2: Sub-components in crop
            sub_comps = annotate_crop(gd_model, crop)
            
            for sc in sub_comps:
                # GDINO boxes are normalized [cx, cy, w, h] relative to CROP
                cx_c, cy_c, bw_c, bh_c = sc["box"]
                
                # Transform back to GLOBAL space
                # cx_abs = x1 + cx_c * cw
                # ... but we want normalized global for YOLO
                cx_g = (x1 + cx_c * cw) / iw
                cy_g = (y1 + cy_c * ch) / ih
                bw_g = (bw_c * cw) / iw
                bh_g = (bh_c * ch) / ih
                
                full_annotations.append((sc["cls"], cx_g, cy_g, bw_g, bh_g))

        # Save & Verification
        if full_annotations:
            # Draw
            vis_img = img0.copy()
            for cls_id, cx, cy, bw, bh in full_annotations:
                ax1 = int((cx - bw/2) * iw)
                ay1 = int((cy - bh/2) * ih)
                ax2 = int((cx + bw/2) * iw)
                ay2 = int((cy + bh/2) * ih)
                color = COLORS.get(cls_id, (255,255,255))
                cv2.rectangle(vis_img, (ax1, ay1), (ax2, ay2), color, 2)
                cv2.putText(vis_img, f"C{cls_id}", (ax1, ay1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            cv2.imwrite(str(VERIFY_DIR / img_path.name), vis_img)
            
            # Save YOLO txt
            lbl_path = LABEL_DIR / (img_path.stem + ".txt")
            with open(lbl_path, "w") as f:
                for ann in full_annotations:
                    f.write(f"{ann[0]} {ann[1]:.6f} {ann[2]:.6f} {ann[3]:.6f} {ann[4]:.6f}\n")
        
        print(f"\r  [{idx+1}/{len(test_imgs)}] processed", end="", flush=True)

    print(f"\n\nDone! Check verification images in {VERIFY_DIR}")

if __name__ == "__main__":
    main()
