import os
import shutil
import zipfile
from huggingface_hub import hf_hub_download
from pathlib import Path
import subprocess

# --- CONFIGURATION ---
REPO_ID = "123456asdfghjcvb/arg_vehicle_dataset"
CHECKPOINT_FILENAME = "arg_training_checkpoint.zip"
TARGET_DIR = Path("arg_vehicle_training")

def sync_from_cloud():
    print(f"📡 Checking Hugging Face for cloud checkpoints...")
    try:
        # 1. Download the checkpoint from the dataset repo
        checkpoint_path = hf_hub_download(
            repo_id=REPO_ID,
            filename=CHECKPOINT_FILENAME,
            repo_type="dataset",
            local_dir=".",
            local_dir_use_symlinks=False
        )
        
        print(f"📦 Found cloud checkpoint. Unpacking to {TARGET_DIR}...")
        
        # 2. Extract the zip into the training directory
        if not TARGET_DIR.exists():
            TARGET_DIR.mkdir(parents=True, exist_ok=True)
            
        with zipfile.ZipFile(CHECKPOINT_FILENAME, 'r') as zip_ref:
            zip_ref.extractall(TARGET_DIR)
            
        print("✅ Cloud weights successfully synced to local machine.")
        
        # Clean up the zip file
        os.remove(CHECKPOINT_FILENAME)
        return True
    except Exception as e:
        print(f"ℹ️ No cloud checkpoint found or error occurred: {e}")
        print("Starting from local files instead...")
        return False

def run_local_training():
    print("\n🚀 Launching Local Training Pipe...")
    # Ensure src is in the python path
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    
    # Run the training script
    subprocess.run(["python", "src/models/train_yolov11.py"], env=env)

if __name__ == "__main__":
    # 1. Try to sync before starting
    sync_from_cloud()
    
    # 2. Run the actual training
    run_local_training()
