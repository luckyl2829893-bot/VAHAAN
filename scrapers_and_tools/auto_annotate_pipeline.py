import os
import shutil
from pathlib import Path
from tqdm import tqdm
import cv2
import yaml
from ultralytics import YOLO

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
SOURCE_DIR = r"c:\Users\laksh\Desktop\image\images"
OUTPUT_DIR = r"c:\Users\laksh\Desktop\image\compiled_training_data"
BASE_MODEL = r"c:\Users\laksh\Desktop\image\yolo11m.pt"

# Folder to Class ID Mapping
# Whatever folder an image is in, any large bounding box found will be assigned THIS class ID.
CLASS_MAP = {
    "car": 0,
    "2wheeler": 1,
    "3wheeler": 2,
    "heavy_commercial_vehicles": 3
}

# The names we want in our final custom model
CLASS_NAMES = ["Car", "2-Wheeler", "3-Wheeler", "Commercial-Vehicle"]

def auto_annotate():
    print(f"Loading Base AI Model for bounding box generation: {BASE_MODEL}")
    model = YOLO(BASE_MODEL)
    
    # Setup output directories
    img_train_dir = os.path.join(OUTPUT_DIR, "images", "train")
    img_val_dir   = os.path.join(OUTPUT_DIR, "images", "valid")
    lbl_train_dir = os.path.join(OUTPUT_DIR, "labels", "train")
    lbl_val_dir   = os.path.join(OUTPUT_DIR, "labels", "valid")
    
    for d in [img_train_dir, img_val_dir, lbl_train_dir, lbl_val_dir]:
        os.makedirs(d, exist_ok=True)
        
    print(f"Output mapped to: {OUTPUT_DIR}")

    total_annotated = 0
    
    # Loop over our 4 main category folders
    for folder_name, class_id in CLASS_MAP.items():
        folder_path = os.path.join(SOURCE_DIR, folder_name)
        if not os.path.exists(folder_path):
            continue
            
        print(f"\nScanning: {folder_path} -> Will map to Class {class_id} ({CLASS_NAMES[class_id]})")
        
        # Recursively find all images in this directory
        image_files = list(Path(folder_path).rglob("*.jpg")) + \
                      list(Path(folder_path).rglob("*.png")) + \
                      list(Path(folder_path).rglob("*.webp"))
                      
        print(f"Found {len(image_files)} images.")
        
        # We will split 90% train, 10% valid
        for idx, img_path in enumerate(image_files):
            # Try to read
            img = cv2.imread(str(img_path))
            if img is None:
                continue
                
            H, W = img.shape[:2]
            
            # Use base YOLO to find bounding boxes
            # We don't care what class base YOLO thinks it is, we only want the bounding box coords
            results = model.predict(img, conf=0.25, verbose=False)
            
            if not results or results[0].boxes is None or len(results[0].boxes) == 0:
                # No object found by base model in this studio image
                continue
            
            # Find the largest bounding box (assuming studio shots feature one main vehicle)
            best_box = None
            max_area = 0
            
            for box in results[0].boxes:
                # Get Normalized XYWH coordinates from YOLO
                xywhn = box.xywhn.cpu().numpy()[0] 
                b_w, b_h = xywhn[2], xywhn[3]
                area = b_w * b_h
                if area > max_area:
                    max_area = area
                    best_box = xywhn
                    
            if best_box is None:
                continue
                
            # Formatting the YOLO label text
            # format: <class> <cx> <cy> <w> <h>
            label_text = f"{class_id} {best_box[0]:.6f} {best_box[1]:.6f} {best_box[2]:.6f} {best_box[3]:.6f}\n"
            
            # Split into train/val
            is_valid = (idx % 10 == 0) # 1 in 10 goes to validation
            
            dest_img_dir = img_val_dir if is_valid else img_train_dir
            dest_lbl_dir = lbl_val_dir if is_valid else lbl_train_dir
            
            # Create unique filenames to avoid overwriting identical names from different folders
            unique_filename = f"{folder_name}_{img_path.stem}_{idx}"
            
            out_img_path = os.path.join(dest_img_dir, unique_filename + img_path.suffix)
            out_lbl_path = os.path.join(dest_lbl_dir, unique_filename + ".txt")
            
            # Copy image and write label
            shutil.copy2(str(img_path), out_img_path)
            with open(out_lbl_path, "w") as f:
                f.write(label_text)
                
            total_annotated += 1
            if total_annotated % 500 == 0:
                print(f"  ...auto-annotated {total_annotated} images successfully.")

    # Create the data.yaml file needed for training
    yaml_path = os.path.join(OUTPUT_DIR, "data.yaml")
    yaml_content = {
        "path": OUTPUT_DIR,
        "train": "images/train",
        "val": "images/valid",
        "nc": len(CLASS_NAMES),
        "names": CLASS_NAMES
    }
    
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_content, f, default_flow_style=False)
        
    print(f"\n[DONE] Generated pure localized dataset at {OUTPUT_DIR}/data.yaml")
    print(f"Total Annotations Created: {total_annotated}")
    print("\nYou can now start training with:")
    print(f"yolo train data={yaml_path} model={BASE_MODEL} epochs=100 imgsz=640")

if __name__ == "__main__":
    auto_annotate()
