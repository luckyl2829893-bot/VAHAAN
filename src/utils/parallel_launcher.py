import sys
import os
import subprocess
from pathlib import Path
from math import ceil

# CONFIGURATION
IMAGE_DIR = r"C:\Users\laksh\Desktop\image\data\labeled\vehicle_dataset\train\images"
RESUME_OFFSET = 0 # V13: Set to 0 because skip-logic in main script handles this now
WORKERS = 2 # Safe for 8GB VRAM with Float32
PYTHON_PATH = sys.executable

def launch():
    print(f"[*] ARG INFINITE-CRAWL Launcher starting...")
    
    # 1. Recursive count (V13)
    img_path_obj = Path(IMAGE_DIR)
    images = [f for f in img_path_obj.rglob("*") if f.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    total = len(images)
    print(f"[*] Found {total} total images (recursive search).")
    
    remaining = total - RESUME_OFFSET
    print(f"[*] Remaining to process: {remaining} images.")
    
    chunk_size = ceil(remaining / WORKERS)
    
    processes = []
    
    for i in range(WORKERS):
        offset = RESUME_OFFSET + (i * chunk_size)
        size = chunk_size
        
        cmd = [
            PYTHON_PATH, 
            "src/pipeline/inference_heirarchical.py",
            "--source", IMAGE_DIR,
            "--annotate",
            "--auto-label",
            "--offset", str(offset),
            "--size", str(size)
        ]
        
        print(f"[+] Launching Worker {i+1}: offset={offset}, size={size}")
        p = subprocess.Popen(cmd)
        processes.append(p)

    print(f"\n[SUCCESS] {WORKERS} Workers are now running in parallel!")
    print("[TIP] You can close this terminal, the processing will continue in the background.")
    
    # Optional: Wait for completion
    for p in processes:
        p.wait()

if __name__ == "__main__":
    launch()
