import os
import shutil
from pathlib import Path

# --- Configuration ---
SOURCE_BASE = Path(r"C:\Users\laksh\Desktop\image\data\images")
DEST_DIR    = Path(r"C:\Users\laksh\Desktop\image\data\labeled\vehicle_dataset\train\images")

# Map of raw folders to tidy categories
CATEGORIES = ["2wheeler", "3wheeler", "car", "heavy_commercial_vehicles"]

def consolidate():
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    moved_count = 0
    skipped_count = 0

    print(f"[*] Starting consolidation from {SOURCE_BASE} to {DEST_DIR}...")

    # Recursive crawl
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.PNG"]:
        for img_path in SOURCE_BASE.rglob(ext):
            try:
                # Extract Brand/Model from path parts
                # Structure: data/images/[Category]/[Sub-Category]/[Brand]/[Model]/[Image]
                # Example: data/images/car/cars/Audi/Audi_A4/image.jpg
                parts = img_path.relative_to(SOURCE_BASE).parts
                
                if len(parts) < 2:
                    skipped_count += 1
                    continue

                # We want a readable prefix
                # We'll take the last few parts before the filename as Brand/Model
                # Usually: [Brand, Model, Filename] or [SubCat, Brand, Model, Filename]
                prefix_parts = [p.replace(" ", "_") for p in parts[:-1]]
                # Filter out generic category names if they appear too many times
                prefix_parts = [p for p in prefix_parts if p.lower() not in ["cars", "2_wheeler", "heavy_vehicle"]]
                
                prefix = "_".join(prefix_parts)
                new_name = f"Studio_{prefix}_{img_path.name}"
                dest_path = DEST_DIR / new_name

                # Copy (to be safe instead of move first)
                shutil.copy2(img_path, dest_path)
                moved_count += 1
                
                if moved_count % 500 == 0:
                    print(f"    - Processed {moved_count} images...")

            except Exception as e:
                print(f"[!] Error processing {img_path}: {e}")
                skipped_count += 1

    print(f"\n[DONE] Consolidation Complete!")
    print(f"  - Successfully copied: {moved_count}")
    print(f"  - Skipped/Errors: {skipped_count}")
    print(f"  - Destination: {DEST_DIR}")

if __name__ == "__main__":
    consolidate()
