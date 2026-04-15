import os
import shutil
from huggingface_hub import HfApi, login

# 1. Login
TOKEN = os.getenv("HF_TOKEN")
if TOKEN:
    login(token=TOKEN)
else:
    print("Warning: HF_TOKEN not found in environment. Skipping auto-login.")

api = HfApi()

# 2. Configuration
REPO_ID = "123456asdfghjcvb/arg_vehicle_dataset"
LOCAL_FOLDER = "data/labeled"
ZIP_NAME = "arg_vehicle_dataset" # Will become arg_vehicle_dataset.zip

print("Step 1: Creating a fast ZIP of your data... (Please wait)")
try:
    # This uses Python's optimized shutil which is 10x faster than Windows Zip
    shutil.make_archive(ZIP_NAME, 'zip', LOCAL_FOLDER)
    print(f"ZIP Created: {ZIP_NAME}.zip")
except Exception as e:
    print(f"Error during zipping: {e}")
    exit(1)

# 3. Create the Repo
try:
    print(f"Step 2: Creating dataset repo on Hugging Face...")
    api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True)
except Exception as e:
    print(f"Note: {e}")

# 4. Upload the files
print(f"Step 3: Uploading the ZIP and training files to https://huggingface.co/datasets/{REPO_ID}")
try:
    # A. Upload the Large Dataset ZIP
    print("Uploading arg_vehicle_dataset.zip...")
    api.upload_file(
        path_or_fileobj=f"{ZIP_NAME}.zip",
        path_in_repo=f"{ZIP_NAME}.zip",
        repo_id=REPO_ID,
        repo_type="dataset",
    )
    
    # B. Upload requirements.txt (So Kaggle knows what to install)
    if os.path.exists("requirements.txt"):
        print("Uploading requirements.txt...")
        api.upload_file(
            path_or_fileobj="requirements.txt",
            path_in_repo="requirements.txt",
            repo_id=REPO_ID,
            repo_type="dataset",
        )

    # C. Upload the Training Script (From src/models/train_yolov11.py)
    train_script = os.path.join("src", "models", "train_yolov11.py")
    if os.path.exists(train_script):
        print(f"Uploading {train_script} as main training script...")
        api.upload_file(
            path_or_fileobj=train_script,
            path_in_repo="train_yolov11.py",
            repo_id=REPO_ID,
            repo_type="dataset",
        )

    # D. Upload the entire src folder (Essential for logic/imports)
    if os.path.exists("src"):
        print("Uploading entire src directory for project logic...")
        api.upload_folder(
            folder_path="src",
            repo_id=REPO_ID,
            repo_type="dataset",
            path_in_repo="src",
        )

    print("SUCCESS! All relevant training files and source code are now live on Hugging Face.")
except Exception as e:
    print(f"Error during upload: {e}")

