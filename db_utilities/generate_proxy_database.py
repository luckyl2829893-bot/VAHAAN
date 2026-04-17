"""
auto_annotate_car_parts.py
==========================
Bulk-annotates a folder of car images using Autodistill + GroundedSAM.
Saves results in YOLOv8 format to /annotated_data.
Includes a supervision-based preview of N random samples.

Dependencies (install in order):
    pip install autodistill autodistill-grounded-sam supervision
    pip install "git+https://github.com/facebookresearch/segment-anything.git"
    pip install groundingdino-py          # or: pip install autodistill-grounding-dino
"""

import os
import random
import glob
import cv2
import numpy as np
import supervision as sv

# --------------------------------------------------------------------------- #
#  Autodistill imports                                                          #
# --------------------------------------------------------------------------- #
from autodistill.detection import CaptionOntology

# Choose ONE of the two base models below.
# GroundedSAM  → produces segmentation masks + boxes (higher quality, slower)
# GroundingDINO → produces bounding boxes only (faster, lighter)

USE_GROUNDED_SAM = True          # Set False to switch to GroundingDINO

if USE_GROUNDED_SAM:
    from autodistill_grounded_sam import GroundedSAM as BaseModel
else:
    from autodistill_grounding_dino import GroundingDINO as BaseModel


# --------------------------------------------------------------------------- #
#  Configuration                                                                #
# --------------------------------------------------------------------------- #
INPUT_DIRS       = ["2 wheeler", "3 wheeler", "heavy vehicle", "ambulance", "test", "ARG_360_Dataset", "ARG_360_Dataset_Bikes"]
OUTPUT_DIR       = "annotated_data"       # YOLOv8 dataset will be written here
PREVIEW_SAMPLES  = 6                      # How many images to visualise
PREVIEW_DIR      = "annotated_data/previews"   # Where preview PNGs are saved

# Supported extensions
IMAGE_EXTENSIONS = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"]

# Confidence threshold for GroundedSAM / GroundingDINO detections
BOX_THRESHOLD    = 0.30
TEXT_THRESHOLD   = 0.25


# --------------------------------------------------------------------------- #
#  Ontology                                                                    #
#  Keys   = natural-language prompts understood by the foundation model        #
#  Values = class labels that will appear in the YOLO annotation files         #
# --------------------------------------------------------------------------- #
ONTOLOGY = CaptionOntology({
    "license plate": "license_plate",
    "headlamp":      "headlight",
    "tail lamp":     "taillight",
    "emblem":        "car_logo",
    "grille":        "front_grill",
})

CLASS_NAMES = ONTOLOGY.classes()   # ordered list for the viewer


# --------------------------------------------------------------------------- #
#  Helpers                                                                     #
# --------------------------------------------------------------------------- #

def collect_images(roots: list[str]) -> list[str]:
    """Recursively collect all image paths under *roots*."""
    paths = []
    for root in roots:
        if not os.path.exists(root): continue
        for ext in IMAGE_EXTENSIONS:
            paths.extend(glob.glob(os.path.join(root, "**", ext), recursive=True))
    paths.sort()
    return paths


def build_color_map(n: int) -> list[tuple[int, int, int]]:
    """Generate visually distinct BGR colours for *n* classes."""
    rng = random.Random(42)
    return [
        (rng.randint(60, 255), rng.randint(60, 255), rng.randint(60, 255))
        for _ in range(n)
    ]


def draw_preview(
    image_path: str,
    detections: sv.Detections,
    class_names: list[str],
    color_map: list[tuple],
    save_path: str,
) -> None:
    """
    Render bounding boxes + labels on *image_path* using supervision
    and write the result to *save_path*.
    """
    image = cv2.imread(image_path)
    if image is None:
        print(f"  [WARN] Could not read image for preview: {image_path}")
        return

    if len(detections) == 0:
        # Still save the image so the user can see empty results too
        cv2.imwrite(save_path, image)
        return

    # Build per-detection colours from the class_id field
    colors_list = [
        sv.Color(*color_map[cid % len(color_map)][::-1])   # BGR → RGB
        for cid in (detections.class_id if detections.class_id is not None
                    else [0] * len(detections))
    ]

    # ---- Box annotator ----
    box_annotator = sv.BoxAnnotator(thickness=2)
    image = box_annotator.annotate(scene=image, detections=detections)

    # ---- Label annotator ----
    if detections.class_id is not None and detections.confidence is not None:
        labels = [
            f"{class_names[cid]}  {conf:.2f}"
            for cid, conf in zip(detections.class_id, detections.confidence)
        ]
    elif detections.class_id is not None:
        labels = [class_names[cid] for cid in detections.class_id]
    else:
        labels = ["detection"] * len(detections)

    label_annotator = sv.LabelAnnotator(text_scale=0.5, text_thickness=1)
    image = label_annotator.annotate(scene=image, detections=detections, labels=labels)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    cv2.imwrite(save_path, image)
    print(f"  [Preview saved] → {save_path}")


# --------------------------------------------------------------------------- #
#  Main                                                                        #
# --------------------------------------------------------------------------- #

def main():
    print("=" * 65)
    print("  Car-Parts Auto-Annotator  |  Autodistill + Supervision")
    print("=" * 65)

    # ---------------------------------------------------------------- #
    #  1. Sanity-check input folders                                    #
    # ---------------------------------------------------------------- #
    image_paths = collect_images(INPUT_DIRS)
    if not image_paths:
        raise RuntimeError(f"No images found in any of {INPUT_DIRS}.")

    print(f"\n  Found {len(image_paths)} image(s) across folders")
    print(f"  Output directory : {OUTPUT_DIR}")
    print(f"  Model            : {'GroundedSAM' if USE_GROUNDED_SAM else 'GroundingDINO'}")
    print(f"  Classes          : {CLASS_NAMES}\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PREVIEW_DIR, exist_ok=True)

    # ---------------------------------------------------------------- #
    #  2. Instantiate the base model                                    #
    # ---------------------------------------------------------------- #
    print("  Loading foundation model (first run downloads weights)…")
    base_model = BaseModel(
        ontology=ONTOLOGY,
        box_threshold=BOX_THRESHOLD,
        text_threshold=TEXT_THRESHOLD,
    )

    # ---------------------------------------------------------------- #
    #  3. Bulk-annotate → YOLOv8 format                                #
    #                                                                  #
    #  autodistill writes:                                             #
    #    <OUTPUT_DIR>/images/<filename>                                #
    #    <OUTPUT_DIR>/labels/<stem>.txt   (YOLO format)               #
    #    <OUTPUT_DIR>/data.yaml           (class list)                #
    # ---------------------------------------------------------------- #
    print("  Starting bulk annotation…\n")
    for input_dir in INPUT_DIRS:
        if not os.path.exists(input_dir):
            continue
        print(f"  --> Annotating folder: {input_dir}")
        base_model.label(
            input_folder=input_dir,
            output_folder=OUTPUT_DIR,
            extension=".jpg",       # autodistill glob; adjust if needed
        )
    print(f"\n  Annotation complete!  Dataset saved to: {OUTPUT_DIR}")

    # ---------------------------------------------------------------- #
    #  4. Visualisation – preview N random samples                     #
    # ---------------------------------------------------------------- #
    print(f"\n  Generating {PREVIEW_SAMPLES} random annotation previews…")

    color_map = build_color_map(len(CLASS_NAMES))

    # Re-collect images (autodistill may have copied them to output/images/)
    annotated_images_dir = os.path.join(OUTPUT_DIR, "images")
    labels_dir           = os.path.join(OUTPUT_DIR, "labels")

    preview_candidates = collect_images(annotated_images_dir)
    if not preview_candidates:
        # Fall back to original source folder
        preview_candidates = image_paths

    sample_paths = random.sample(
        preview_candidates,
        min(PREVIEW_SAMPLES, len(preview_candidates))
    )

    for img_path in sample_paths:
        stem      = os.path.splitext(os.path.basename(img_path))[0]
        label_txt = os.path.join(labels_dir, stem + ".txt")

        # ---- Load YOLO annotations back into supervision.Detections ----
        if os.path.exists(label_txt):
            img_bgr = cv2.imread(img_path)
            h, w    = img_bgr.shape[:2]

            boxes, class_ids, confs = [], [], []
            with open(label_txt) as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) < 5:
                        continue
                    cls_id         = int(parts[0])
                    cx, cy, bw, bh = map(float, parts[1:5])
                    conf           = float(parts[5]) if len(parts) == 6 else 1.0

                    # Convert normalised YOLO → absolute xyxy
                    x1 = (cx - bw / 2) * w
                    y1 = (cy - bh / 2) * h
                    x2 = (cx + bw / 2) * w
                    y2 = (cy + bh / 2) * h
                    boxes.append([x1, y1, x2, y2])
                    class_ids.append(cls_id)
                    confs.append(conf)

            if boxes:
                detections = sv.Detections(
                    xyxy       = np.array(boxes, dtype=np.float32),
                    class_id   = np.array(class_ids, dtype=int),
                    confidence = np.array(confs, dtype=np.float32),
                )
            else:
                detections = sv.Detections.empty()
        else:
            detections = sv.Detections.empty()

        preview_path = os.path.join(PREVIEW_DIR, stem + "_preview.jpg")
        draw_preview(img_path, detections, CLASS_NAMES, color_map, preview_path)

    # ---------------------------------------------------------------- #
    #  5. Summary                                                       #
    # ---------------------------------------------------------------- #
    print("\n" + "=" * 65)
    print("  DONE")
    print("=" * 65)
    print(f"  YOLOv8 dataset  →  {OUTPUT_DIR}")
    print(f"    ├── images/       (copied input images)")
    print(f"    ├── labels/       (one .txt per image, YOLO format)")
    print(f"    └── data.yaml     (class names for Roboflow / Ultralytics)")
    print(f"  Previews        →  {PREVIEW_DIR}")
    print(f"\n  Upload '{OUTPUT_DIR}' directly to Roboflow for manual review.")
    print("=" * 65)


if __name__ == "__main__":
    main()
