import torch
import sys

def check():
    print("--- GPU Diagnostic ---")
    print(f"Python: {sys.executable}")
    print(f"Torch Version: {torch.__version__}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"CUDA Device Count: {torch.cuda.device_count()}")
        print(f"Current Device Name: {torch.cuda.get_device_name(0)}")
    else:
        print("CUDA NOT DETECTED by Torch.")
        print("Tip: Re-install torch with CUDA support: 'pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121'")

if __name__ == "__main__":
    check()
