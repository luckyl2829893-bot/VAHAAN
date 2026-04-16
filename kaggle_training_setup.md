# Kaggle Training Setup for Aequitas RoadGuard

Copy and paste this code into a single cell in your Kaggle Notebook. 
**Make sure to set the Notebook "Accelerator" to "GPU P100" or "GPU T4 x2" in the right-hand panel.**

```python
import os
import shutil

# --- 1. CONFIGURATION ---
REPO_URL = "https://huggingface.co/datasets/123456asdfghjcvb/arg_vehicle_dataset"
WORKING_DIR = "/kaggle/working"
DATASET_DIR = os.path.join(WORKING_DIR, "dataset")

print("🚀 Starting Kaggle Environment Setup...")

# --- 2. FETCH DATA FROM HUGGING FACE ---
if os.path.exists("arg_vehicle_dataset"):
    shutil.rmtree("arg_vehicle_dataset")

!git clone {REPO_URL} 

# --- 3. UNZIP AND REORGANIZE ---
if os.path.exists(DATASET_DIR):
    shutil.rmtree(DATASET_DIR)
os.makedirs(DATASET_DIR, exist_ok=True)

print("📦 Unzipping dataset and source code...")
!unzip -q arg_vehicle_dataset/arg_vehicle_dataset.zip -d {DATASET_DIR}

# Copy the 'src' folder to the root working directory so imports work
if os.path.exists("arg_vehicle_dataset/src"):
    if os.path.exists("src"): shutil.rmtree("src")
    shutil.copytree("arg_vehicle_dataset/src", "src")
    print("📁 Source code (src) positioned for imports.")

# Copy the training script to root
shutil.copy("arg_vehicle_dataset/train_yolov11.py", "train_yolov11.py")

# --- 4. INSTALL DEPENDENCIES ---
print("⚙️ Installing requirements...")
!pip install -r arg_vehicle_dataset/requirements.txt -q
!pip install ultralytics -q

# --- 5. FIX YAML PATHS (CRITICAL) ---
import yaml
import re

# We iterate through possible nested locations to find the yaml
yaml_candidates = [
    os.path.join(DATASET_DIR, "vehicle_dataset", "vehicle_data.yaml"),
    os.path.join(DATASET_DIR, "vehicle_data.yaml")
]

yaml_path = None
for candidate in yaml_candidates:
    if os.path.exists(candidate):
        yaml_path = candidate
        break

if yaml_path:
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    
    # Correct the root path to Kaggle regardless of what was there before
    # If the zip has vehicle_dataset/ folder inside:
    if "vehicle_dataset" in yaml_path:
        data['path'] = os.path.join(DATASET_DIR, "vehicle_dataset")
    else:
        data['path'] = DATASET_DIR
        
    with open(yaml_path, 'w') as f:
        yaml.dump(data, f)
    print(f"✅ YAML paths re-aligned to: {data['path']}")
else:
    print("⚠️ Warning: vehicle_data.yaml not found. Training might fail.")

# --- 6. START GPU TRAINING ---
print("🏎️ Starting GPU Training...")
# Run from the root where 'src' is now located
!python train_yolov11.py
```

### 💡 Why this works:
1. **Auto-Cleanup**: If you run the cell twice, it deletes the old folders to prevent "disk full" errors.
2. **YAML Realignment**: It automatically finds your `vehicle_data.yaml` and changes the file paths from your local PC's drive letters to Kaggle's `/kaggle/working/dataset` path.
3. **GPU Force**: The `train_yolov11.py` script we uploaded already has `device=0` set, so it will automatically grab the Kaggle GPU.

### 📥 Downloading your results:
Once training is done, your `best.pt` will be in:
`/kaggle/working/runs/train/arg_vehicle_v11m/weights/best.pt`

**You can then download it directly from the "Output" section of your Kaggle notebook!**
