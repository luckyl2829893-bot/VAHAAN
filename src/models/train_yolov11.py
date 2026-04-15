import os
import sys
import yaml
import torch
import time
import shutil
import argparse
from pathlib import Path
from ultralytics import YOLO

# --- KAGGLE TIME MANAGEMENT ---
START_TIME = time.time()
# Kaggle limit is 12h (43200s). We stop at 11h 45m (42300s) to allow 15m for zipping/uploading.
SESSION_LIMIT = 42300 

# --- ENVIRONMENT CONFIG ---
WANDB_DISABLED = True
os.environ["WANDB_MODE"] = "disabled"
os.environ["YOLO_VERBOSE"] = "False"  
os.environ["PYTHONWARNINGS"] = "ignore"

def timer_callback(trainer):
    """Callback to stop training and upload checkpoint before Kaggle session expires."""
    elapsed = time.time() - START_TIME
    if elapsed > SESSION_LIMIT:
        print(f"\n⏳ SESSION LIMIT REACHED ({elapsed/3600:.2f}h). Saving progress...")
        trainer.stop = True  
        with open("ABORT_FOR_CHECKPOINT.txt", "w") as f:
            f.write("Time limit hit. Please upload and resume.")

def upload_to_hf(project_name):
    """Pushes the training state to Hugging Face for the next session."""
    print(f"📦 Preparing {project_name} checkpoint for Hugging Face...")
    try:
        from huggingface_hub import HfApi
        hf_token = None
        try:
            from kaggle_secrets import UserSecretsClient
            hf_token = UserSecretsClient().get_secret("HF_TOKEN")
        except:
            hf_token = os.environ.get("HF_TOKEN")
            
        if not hf_token:
            print("⚠️ No HF_TOKEN found in Kaggle Secrets or Env. Skipping cloud upload.")
            return

        zip_file = f"{project_name}_checkpoint"
        shutil.make_archive(zip_file, 'zip', project_name)
        
        api = HfApi(token=hf_token)
        print(f"📡 Uploading {zip_file}.zip...")
        api.upload_file(
            path_or_fileobj=f"{zip_file}.zip",
            path_in_repo=f"{zip_file}.zip",
            repo_id="123456asdfghjcvb/arg_vehicle_dataset",
            repo_type="dataset"
        )
        print("✅ Checkpoint uploaded successfully!")
    except Exception as e:
        print(f"⚠️ Could not upload to HF: {e}")

def run_training(stage=1, epochs=100):
    """Orchestrates a single stage of training."""
    if stage == 1:
        project_name = "arg_vehicle_training"
        exp_name = "arg_vehicle_v11m"
        base_model = "yolo11m.pt"
        data_config = {
            'path': os.path.join(os.getcwd(), "dataset", "vehicle_dataset"),
            'train': "train/images",
            'val': "train/images",
            'nc': 4,
            'names': {0: 'car', 1: 'motorcycle', 2: 'bus', 3: 'truck'}
        }
    else:
        project_name = "arg_component_training"
        exp_name = "arg_component_v11m"
        base_model = "yolo11m.pt"
        data_config = {
            'path': os.path.join(os.getcwd(), "dataset", "stage2_dataset"),
            'train': "images",
            'val': "images",
            'nc': 5,
            'names': {0: 'license_plate', 1: 'vehicle_logo', 2: 'grille', 3: 'headlamp', 4: 'taillamp'}
        }

    # --- ULTRALYTICS DICT FIX (V23) ---
    # Some Ultralytics versions fail when passing a dict to 'data'. 
    # We save as a physical YAML file to ensure compatibility.
    yaml_path = f"temp_stage{stage}.yaml"
    with open(yaml_path, 'w') as f:
        yaml.dump(data_config, f)
    
    print(f"\n--- 🚀 STARTING STAGE {stage} ({exp_name}) ---")
    print(f"📍 Data Path: {data_config['path']}")
    print(f"📍 Config: {yaml_path}")
    
    num_gpus = torch.cuda.device_count()
    devices = list(range(num_gpus)) if num_gpus > 0 else "cpu"
    
    # Local checkpoint check
    checkpoint_path = Path(project_name) / exp_name / "weights" / "last.pt"
    best_path = Path(project_name) / exp_name / "weights" / "best.pt"
    
    if checkpoint_path.exists():
        model_path = str(checkpoint_path)
        print(f"📍 Resuming from existing weights: {model_path}")
    else:
        model_path = base_model
        print(f"📍 Starting fresh with base model: {model_path}")
    
    model = YOLO(model_path)
    model.add_callback('on_train_epoch_end', timer_callback)
    
    model.train(
        data=yaml_path, # Pass STRING path instead of DICT to avoid clean_url crash
        epochs=epochs,
        imgsz=640,
        batch=16,
        device=devices,
        project=project_name,
        name=exp_name,
        exist_ok=True,
        resume=False, # FORCED FALSE: This bypasses corrupted Windows paths in checkpoints
        patience=20,
        save=True,
        verbose=True
    )
    
    # Check for session timeout
    if os.path.exists("ABORT_FOR_CHECKPOINT.txt"):
        upload_to_hf(project_name)
        print("\n⏳ 12h Limit - Checkpoint Uploaded. Restart required.")
        sys.exit(0)

    print(f"✅ STAGE {stage} COMPLETE!")
    return str(best_path) if best_path.exists() else None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, default=0, help="0: Full Pipeline, 1: Vehicle Only, 2: Components Only")
    parser.add_argument("--epochs", type=int, default=100)
    args = parser.parse_args()

    if args.stage == 0:
        print("🚩 FULL DUAL-STAGE PIPELINE INITIATED")
        # STAGE 1
        run_training(stage=1, epochs=args.epochs)
        # STAGE 2
        run_training(stage=2, epochs=args.epochs)
    elif args.stage == 1:
        run_training(stage=1, epochs=args.epochs)
    elif args.stage == 2:
        run_training(stage=2, epochs=args.epochs)

if __name__ == "__main__":
    main()
