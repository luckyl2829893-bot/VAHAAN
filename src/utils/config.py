import os
from pathlib import Path

# Base directory setup
# Since this file is in src/utils/config.py, the root is 2 levels up
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Data Paths
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
LABELED_DATA_DIR = DATA_DIR / "labeled"

# Specific Data Folders
DATA_CSV_DIR = DATA_DIR / "Registry"
PIPELINE_DIR = RAW_DATA_DIR / "data_pipeline"
INCOMING_DIR = PIPELINE_DIR / "incoming_plates"
TRAINING_IMG_DIR = PIPELINE_DIR / "train" / "images"
TRAINING_LBL_DIR = PIPELINE_DIR / "train" / "labels"
EVIDENCE_VAULT = RAW_DATA_DIR / "evidence_vault"

# Pipeline Configs
GROWTH_LOG = PIPELINE_DIR / "growth_log.jsonl"
SUBCOMP_MODEL = BASE_DIR / "runs" / "train" / "arg_vehicle_v11m" / "weights" / "best.pt"
TRAIN_SCRIPT = BASE_DIR / "src" / "models" / "train_yolov11.py"

# Model Paths
MODELS_DIR = BASE_DIR / "models"
VEHICLE_MODEL_PATH = MODELS_DIR / "stage1_vehicle" / "yolo11m.pt"
PLATE_MODEL_PATH = MODELS_DIR / "stage2_plate" / "yolov8n.pt"

# Database Configuration (MySQL env handled in manager.py)

def ensure_dirs():
    """Ensure all required directories exist."""
    dirs = [
        RAW_DATA_DIR, PROCESSED_DATA_DIR, LABELED_DATA_DIR,
        DATA_CSV_DIR, PIPELINE_DIR, INCOMING_DIR,
        TRAINING_IMG_DIR, TRAINING_LBL_DIR, EVIDENCE_VAULT,
        MODELS_DIR
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    print(f"Project Base Directory: {BASE_DIR}")
    ensure_dirs()
    print("All directories verified.")
