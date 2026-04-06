"""
auto_organize_dataset.py
========================
Case 1: The Auto-Sorter (Bulk Organization)

This script acts as the "Layer 2" of your AI architecture.
It reads an input directory of unorganized images, runs them through a 
fine-grained image classifier (trained on your scraped datasets), 
and automatically moves them into specific `Make/Model` directories 
if the AI is highly confident.
"""

import os
import shutil
import glob

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
UNORGANIZED_DIR = "unorganized_pipeline_inbox"
ORGANIZED_DIR   = "organized_master_dataset"
CONFIDENCE_THRESHOLD = 0.85   # 85% confidence required to auto-sort

# --------------------------------------------------------------------------- #
# Mock Classifier (To be replaced with your trained EfficientNet/ResNet)
# --------------------------------------------------------------------------- #
def predict_make_model(image_path: str):
    """
    TODO: Insert your actual Layer 2 model inference here.
    This model should take an image (ideally cropped tightly by YOLO),
    and output the precise Make, Model, and a confidence score.
    """
    # Mocking a prediction for demonstration...
    # In reality, this will be: `results = my_fine_grained_model.predict(image)`
    
    mock_predictions = [
        ("Maruti Suzuki", "Swift Dzire", 0.92),
        ("Tata Motors", "Safari", 0.95),
        ("Hyundai", "Creta", 0.40) # Low confidence
    ]
    import random
    return random.choice(mock_predictions)


# --------------------------------------------------------------------------- #
# Sorting Logic
# --------------------------------------------------------------------------- #
def main():
    print("=" * 50)
    print("  Auto-Sorter | Bulk Dataset Organization")
    print("=" * 50)

    if not os.path.exists(UNORGANIZED_DIR):
        os.makedirs(UNORGANIZED_DIR)
        print(f"Created '{UNORGANIZED_DIR}'. Drop raw images here to be sorted.")
        return

    images = glob.glob(os.path.join(UNORGANIZED_DIR, "*.jpg"))
    if not images:
        print("No images found to sort.")
        return

    print(f"Found {len(images)} images to process...\n")

    for img_path in images:
        filename = os.path.basename(img_path)
        
        # 1. Predict Make and Model
        make, model, confidence = predict_make_model(img_path)

        # 2. Check confidence against threshold
        if confidence >= CONFIDENCE_THRESHOLD:
            # Create destination folder: e.g., organized_master_dataset/Maruti Suzuki/Swift Dzire/
            dest_folder = os.path.join(ORGANIZED_DIR, make, model)
            os.makedirs(dest_folder, exist_ok=True)
            
            dest_path = os.path.join(dest_folder, filename)
            
            # Move the file
            shutil.move(img_path, dest_path)
            print(f"[SORTED ✔] {filename} -> {make}/{model} (Confidence: {confidence:.2f})")
        else:
            # Leave it alone or move it to a "needs human review" folder
            review_folder = os.path.join(ORGANIZED_DIR, "Needs_Human_Review")
            os.makedirs(review_folder, exist_ok=True)
            dest_path = os.path.join(review_folder, filename)
            
            shutil.move(img_path, dest_path)
            print(f"[REVIEW ⚠] {filename} -> Sent to Human Review Queue (Confidence: {confidence:.2f})")

    print("\nSorting Complete!")

if __name__ == "__main__":
    main()
