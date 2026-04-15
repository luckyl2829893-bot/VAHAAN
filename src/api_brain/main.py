from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile
from pydantic import BaseModel
from typing import List, Optional
import os
import sys
import time
import shutil
try:
    import torch
    import torchvision.transforms as T
    from torchvision.models import resnet18, ResNet18_Weights
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from PIL import Image
import io
import numpy as np
from pathlib import Path

# Fix paths for imports
root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from src.database.manager import DBManager
from src.database.db_writer import lookup_plate, insert_full_record

# --- Setup Directories ---
USER_DATA_DIR = root_path / "data" / "users"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- AI Face Engine ---
class FaceEngine:
    def __init__(self):
        if TORCH_AVAILABLE:
            # Using a lightweight ResNet for feature extraction
            self.model = resnet18(weights=ResNet18_Weights.DEFAULT)
            self.model.eval()
            self.preprocess = T.Compose([
                T.Resize((224, 224)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
        else:
            print("WARNING: PyTorch not found. Using fallback mock biometric engine.")

    def get_encoding(self, image_bytes):
        if TORCH_AVAILABLE:
            img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            input_tensor = self.preprocess(img).unsqueeze(0)
            with torch.no_grad():
                embedding = self.model(input_tensor)
            return embedding.numpy().flatten().tolist()
        else:
            # Simple fallback hash based on image size/average (not secure, just for dev)
            return [len(image_bytes) % 100] * 512

    def compare_faces(self, encoding1, encoding2, threshold=0.70):
        if TORCH_AVAILABLE:
            # Simple Cosine Similarity
            v1 = np.array(encoding1)
            v2 = np.array(encoding2)
            sim = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            return sim > threshold, float(sim)
        else:
            # Simple fallback match
            return encoding1 == encoding2, 1.0

face_engine = FaceEngine()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ARG Flutter Backend API")

# Add CORS for Flutter compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "online", "system": "Aequitas RoadGuard", "clearance": "standard"}

# --- Models ---

class ReportViolation(BaseModel):
    plate: str
    type: str
    lat: float
    lng: float
    timestamp: str

class UserCreate(BaseModel):
    full_name: str
    contact_no: str
    professional_id: Optional[str] = None
    face_encoding: Optional[str] = None # Base64 or hash string

class LoginRequest(BaseModel):
    contact_no: str
    face_encoding: Optional[str] = None

# --- Endpoints ---

import json

@app.post("/api/register")
async def register_user(
    full_name: str,
    contact_no: str,
    professional_id: Optional[str] = None,
    face_image: UploadFile = File(...)
):
    """Register user with real passport-size image and biometric encoding."""
    image_bytes = await face_image.read()
    
    # 1. Generate Biometric ID
    encoding = face_engine.get_encoding(image_bytes)
    encoding_json = json.dumps(encoding)
    
    # 2. Save Image to Disk
    file_ext = face_image.filename.split(".")[-1]
    image_filename = f"{contact_no}.{file_ext}"
    image_path = USER_DATA_DIR / image_filename
    with open(image_path, "wb") as buffer:
        buffer.write(image_bytes)
        
    # 3. Save to Database
    query = """
    INSERT INTO users (full_name, contact_no, professional_id, face_encoding, profile_image)
    VALUES (%s, %s, %s, %s, %s)
    """
    try:
        res = DBManager.execute(query, (full_name, contact_no, professional_id, encoding_json, str(image_path)))
        if res:
            return {"status": "success", "message": "Identity registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"User already exists or DB error: {str(e)}")
    
    raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/api/login-by-face")
async def login_by_face(
    face_image: UploadFile = File(...)
):
    """Zero-Input Login: Finds a user just by their face scan."""
    # 1. Capture current face
    current_image_bytes = await face_image.read()
    current_encoding = face_engine.get_encoding(current_image_bytes)
    
    # 2. Get all users
    query = "SELECT * FROM users WHERE face_encoding IS NOT NULL"
    users = DBManager.fetch_all(query)
    
    best_match = None
    max_confidence = 0
    
    # 3. 1:N Biometric Search
    for user in users:
        stored_encoding = json.loads(user['face_encoding'])
        is_match, confidence = face_engine.compare_faces(current_encoding, stored_encoding, threshold=0.70)
        
        print(f"DEBUG: Comparing with {user['full_name']} | Confidence: {confidence:.4f} | Match: {is_match}")
        
        if is_match and confidence > max_confidence:
            max_confidence = confidence
            best_match = user
            
    if best_match:
        user_data = dict(best_match)
        user_data.pop('face_encoding')
        return {
            "status": "success",
            "message": f"Welcome back, {user_data['full_name']}! (Confidence: {max_confidence:.2f})",
            "user": user_data
        }
    
    raise HTTPException(status_code=401, detail="Identity not recognized. Please register or enter details.")

@app.get("/api/vehicle/{plate}")
async def get_vehicle(plate: str):
    """Lookup vehicle details from VAHAN/FASTag."""
    conn = DBManager.get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    # Try to lookup existing record
    result = lookup_plate(conn, plate.upper())
    
    # If not found, simulate VAHAN registration for the demo
    if not result:
        # For demo purposes, we auto-register unrecognized cars in the prototype
        insert_full_record(conn, plate.upper(), "DL", "4-Wheeler (Luxury SUV)")
        result = lookup_plate(conn, plate.upper())
    
    conn.close()
    
    if result:
        # Calculate a mock wealth multiplier for the UI
        price = result.get('invoice_price', 1000000)
        result['wealth_multiplier'] = round(max(1.0, min(10.0, price/500000)), 2)
        return result
    
    raise HTTPException(status_code=404, detail="Vehicle not found")

@app.post("/api/report")
async def report_violation(report: ReportViolation):
    """Log a citizen report into the database."""
    query = """
    INSERT INTO challans (plate_number, violation_type, base_fine, status)
    VALUES (%s, %s, %s, %s)
    """
    # Mock fine amounts for the prototype
    base_fines = {"Speeding": 1000, "Red Light Jump": 5000, "Pothole": 0}
    fine = base_fines.get(report.type, 500)
    
    res = DBManager.execute(query, (report.plate.upper(), report.type, fine, "Pending Verification"))
    
    if res:
        return {"status": "success", "message": "Report logged for Sentinel verification"}
    
    raise HTTPException(status_code=500, detail="Failed to log report")

@app.get("/api/challans/{plate}")
async def get_challans(plate: str):
    """Retrieve unpaid challans for a plate."""
    query = "SELECT * FROM challans WHERE plate_number = %s ORDER BY date_issued DESC"
    results = DBManager.fetch_all(query, (plate.upper(),))
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
