import os
import shutil
from pathlib import Path
import sys

# Add project root to path
root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path: sys.path.append(str(root_path))

from src.utils.config import DATA_DIR, LABELED_DATA_DIR

# Configuration
SOURCE_BASE = DATA_DIR / "images"
DEST_DATASET = LABELED_DATA_DIR / "vehicle_dataset"
TRAIN_IMG_DIR = DEST_DATASET / "train" / "images"
TRAIN_LBL_DIR = DEST_DATASET / "train" / "labels"

# Mapping: Folder Name -> YOLO Class ID (matches vehicle_data.yaml)
# Categories: [Bus=0, Car=1, LCV=2, Motorcycle=3, Pickup=4, Truck=5, Van=6]
CLASS_MAP = {
    "car": 1,
    "2wheeler": 3,
    "heavy_commercial_vehicles": 5,
    "3wheeler": 6
}

def ingest():
    print(f"Starting Ingestion from {SOURCE_BASE} to {DEST_DATASET}")
    
    # Ensure destination exists
    TRAIN_IMG_DIR.mkdir(parents=True, exist_ok=True)
    TRAIN_LBL_DIR.mkdir(parents=True, exist_ok=True)

    for folder, class_id in CLASS_MAP.items():
        src_path = SOURCE_BASE / folder
        if not src_path.exists():
            continue
            
        print(f"Processing category: {folder}")
        
        # Search for images recursively to catch brand subfolders
        images = list(src_path.rglob("*.jpg")) + list(src_path.rglob("*.png"))
        
        for img_p in images:
            # Determine Make from parent folder if it's in ARG_360_Dataset
            parent_name = img_p.parent.name.capitalize()
            brand_list = ["Audi", "Bmw", "Honda", "Hyundai", "Kia", "Lamborghini", "Land-rover", 
                          "Mahindra", "Maruti", "Tata", "Toyota", "Bajaj", "Hero", "Royal-enfield", 
                          "Suzuki", "Tvs", "Yamaha"]
            make_tag = parent_name if parent_name in brand_list else "Generic"
            
            # Copy image with brand prefix to help model identify it
            new_name = f"{make_tag}_{img_p.name}"
            dest_img = TRAIN_IMG_DIR / new_name
            if not dest_img.exists():
                shutil.copy(img_p, dest_img)
            
            # Create label
            label_p = TRAIN_LBL_DIR / (Path(new_name).stem + ".txt")
            if not label_p.exists():
                with open(label_p, "w") as f:
                    # class_id is the primary (car/2w), maybe we add a secondary label for Make later
                    f.write(f"{class_id} 0.500000 0.500000 0.900000 0.900000\n")

    print("\nIngestion Complete with Brand Mapping!")
    print(f"Total training images now: {len(list(TRAIN_IMG_DIR.glob('*')))}")

if __name__ == "__main__":
    ingest()
