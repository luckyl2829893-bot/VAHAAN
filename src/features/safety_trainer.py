"""
VAHAAN Safety Net — Model Trainer
===================================
Train a YOLOv8 model to detect road safety violations simultaneously:
  - No Helmet (class 0)
  - No Seat Belt (class 1)
  - Mobile Phone While Driving (class 2)
  - Triple Riding (class 3)
  - Wrong Way Driving (class 4)

How to Use:
-----------
1. Download a pre-built dataset (see DATASET SOURCES below)
2. Set DATASET_YAML to point at your data.yaml
3. Run: python src/features/safety_trainer.py
4. Your trained model is saved as safety_net.pt in the project root

DATASET SOURCES (Free, India-relevant):
----------------------------------------
  Helmet:      https://universe.roboflow.com/search?q=helmet+motorcycle+india
  Seatbelt:    https://universe.roboflow.com/search?q=seatbelt+car+detection
  Phone:       https://universe.roboflow.com/search?q=phone+driving+distraction
  Combined:    https://universe.roboflow.com/search?q=road+safety+violation

RECOMMENDED: Use the Roboflow "Road Safety Violation Detection" dataset
which combines all violations in a single annotated dataset (~6,500 images).

Expected data.yaml format:
    path: ./data/safety_dataset
    train: images/train
    val: images/val
    nc: 5
    names:
      0: no_helmet
      1: no_seatbelt
      2: mobile_phone_driving
      3: triple_riding
      4: wrong_way_driving
"""

from pathlib import Path
from ultralytics import YOLO

# ── Configuration ─────────────────────────────────────────────────────────────

# Path to your downloaded dataset's data.yaml
DATASET_YAML = "./data/safety_dataset/data.yaml"

# Base model: yolov8n=fastest, yolov8s=balanced, yolov8m=accurate
BASE_MODEL = "yolov8n.pt"

# Training hyperparameters
EPOCHS    = 80
IMGSZ     = 640
BATCH     = 16   # Reduce to 8 if you get OOM errors

# Output location
OUTPUT_NAME = "safety_net"
ROOT = Path(__file__).resolve().parent.parent.parent   # project root

# ── Training ──────────────────────────────────────────────────────────────────

def train():
    print("=" * 60)
    print("  VAHAAN Safety Net — Model Training")
    print("=" * 60)
    print(f"  Base model  : {BASE_MODEL}")
    print(f"  Dataset     : {DATASET_YAML}")
    print(f"  Epochs      : {EPOCHS}")
    print(f"  Image size  : {IMGSZ}px")
    print("=" * 60)

    model = YOLO(BASE_MODEL)

    results = model.train(
        data        = DATASET_YAML,
        epochs      = EPOCHS,
        imgsz       = IMGSZ,
        batch       = BATCH,
        name        = OUTPUT_NAME,
        patience    = 20,          # Early stopping if no improvement for 20 epochs
        device      = 0,           # 0 = GPU, "cpu" = CPU only
        augment     = True,        # Enable real-time augmentation
        # India-specific augmentation for diverse weather/lighting
        hsv_h       = 0.02,
        hsv_s       = 0.8,
        hsv_v       = 0.5,
        flipud      = 0.05,
        # Weights & Biases logging (optional, remove if not configured)
        # project   = "VAHAAN",
    )

    # Copy best weights to project root as safety_net.pt
    best_weights = Path(f"runs/detect/{OUTPUT_NAME}/weights/best.pt")
    if best_weights.exists():
        dest = ROOT / "safety_net.pt"
        import shutil
        shutil.copy(best_weights, dest)
        print(f"\n[✓] Model saved to: {dest}")
        print("[✓] Restart the VAHAAN API to load the new model.")
    else:
        print("[!] Training complete but best.pt not found. Check runs/ directory.")

    return results


def validate():
    """Quick validation pass on the trained model."""
    model_path = ROOT / "safety_net.pt"
    if not model_path.exists():
        print("[!] safety_net.pt not found. Train first.")
        return

    model = YOLO(str(model_path))
    metrics = model.val(data=DATASET_YAML, imgsz=IMGSZ)
    print(f"\n[✓] mAP50: {metrics.box.map50:.4f}")
    print(f"[✓] mAP50-95: {metrics.box.map:.4f}")
    return metrics


if __name__ == "__main__":
    import sys
    if "--validate" in sys.argv:
        validate()
    else:
        train()
