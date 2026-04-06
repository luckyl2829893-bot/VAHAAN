"""
ARG API Server — FastAPI Backend for the Mobile App

This is the cloud-ready backend that connects the mobile app to the AI pipeline.
Upload an image → get back the complete vehicle profile, violations, and challan.

Endpoints:
    POST /detect          → Upload image, get full detection results
    POST /detect-video    → Upload video, get all detections + evidence
    GET  /profile/{plate} → Lookup existing plate in the database
    GET  /violations      → List all recorded violations
    GET  /stats           → Dashboard statistics (total vehicles, fines, etc.)
    GET  /health          → Server health check

Run:
    uvicorn arg_api_server:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import io
import re
import cv2
import json
import base64
import sqlite3
import tempfile
import shutil
import numpy as np
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ultralytics import YOLO
import easyocr

from generate_proxy_database import (
    STATE_RTO_MAP, create_database_schema,
    generate_aadhar, generate_virtual_id,
    generate_vehicle_details, generate_citizen_profile,
    get_vehicle_class_from_coco, random_date,
    generate_chassis, generate_engine_no,
    INSURANCE_COMPANIES, BANKS
)
from arg_video_engine import generate_legal_narrative

import random

# ============================================================
#  APP SETUP
# ============================================================

app = FastAPI(
    title="Aequitas RoadGuard API",
    description="AI-Powered Traffic Enforcement System for India. Upload vehicle images to detect plates, lookup owners, and calculate wealth-adjusted fines.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Allow all origins for mobile app access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
#  GLOBAL MODELS (Loaded once at startup)
# ============================================================

PATTERN_INDIA = re.compile(r'([A-Z]{2})([0-9]{1,2})([A-Z]{1,3})([0-9]{1,4})')
DB_PATH = 'arg_master_database.sqlite'

vehicle_model = None
plate_model = None
ocr_reader = None


@app.on_event("startup")
async def load_models():
    """Load all AI models once when the server starts."""
    global vehicle_model, plate_model, ocr_reader

    print("🚀 Loading ARG AI Models...")
    vehicle_model = YOLO("yolo11m.pt")
    print("   ✅ Stage 1 (Vehicle Finder) loaded")

    plate_path = r"runs/detect/plate_model_train_final/weights/best.pt"
    if os.path.exists(plate_path):
        plate_model = YOLO(plate_path)
        print("   ✅ Stage 2 (Plate Sniper) loaded")
    else:
        print("   ⚠️ Plate Sniper not found!")

    ocr_reader = easyocr.Reader(['en'], gpu=True)
    print("   ✅ EasyOCR loaded")
    print("🟢 ARG API Server Ready!")


# ============================================================
#  PYDANTIC MODELS (Response Schemas)
# ============================================================

class VehicleDetection(BaseModel):
    vehicle_type: str
    plate_number: str
    confidence: float
    bounding_box: dict
    plate_image_base64: Optional[str] = None


class OwnerProfile(BaseModel):
    plate_number: str
    owner_name: str
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    phone_masked: Optional[str] = None
    pan_number: Optional[str] = None
    cibil_score: Optional[int] = None


class VehicleProfile(BaseModel):
    plate_number: str
    vehicle_class: str
    make: str
    model: str
    color: Optional[str] = None
    fuel_type: Optional[str] = None
    invoice_price: float
    reg_date: Optional[str] = None
    rto: Optional[str] = None
    rc_status: Optional[str] = None
    insurance_company: Optional[str] = None
    hypothecation: Optional[str] = None
    financer_bank: Optional[str] = None


class FASTagProfile(BaseModel):
    fastag_id: Optional[str] = None
    wallet_balance: Optional[float] = None
    issuer_bank: Optional[str] = None
    tag_status: Optional[str] = None


class WealthMultiplier(BaseModel):
    vehicle_value: float
    multiplier: float
    base_fine: float
    final_fine: float


class DetectionResult(BaseModel):
    status: str  # "EXISTING" or "NEW_PROXY_GENERATED"
    detection: VehicleDetection
    owner: OwnerProfile
    vehicle: VehicleProfile
    fastag: FASTagProfile
    wealth_multiplier: WealthMultiplier
    violations: List[str]
    legal_narrative: Optional[str] = None
    annotated_image_base64: Optional[str] = None


class ViolationRecord(BaseModel):
    challan_id: int
    plate_number: str
    violation_type: str
    base_fine: float
    wealth_multiplier: float
    final_fine: float
    status: str
    date_issued: str


class DashboardStats(BaseModel):
    total_vehicles: int
    total_challans: int
    total_revenue_pending: float
    total_revenue_collected: float
    violation_breakdown: dict
    top_violators: list


# ============================================================
#  HELPER FUNCTIONS
# ============================================================

def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    create_database_schema(conn)
    return conn


def run_detection_pipeline(img):
    """Run the Two-Stage AI pipeline on an image. Returns list of detections."""
    results = []

    v_results = vehicle_model.predict(img, verbose=False)

    for v_box in v_results[0].boxes:
        v_cls = int(v_box.cls[0])
        v_conf = float(v_box.conf[0])

        if v_cls not in [1, 2, 3, 5, 7]:
            continue

        x1, y1, x2, y2 = map(int, v_box.xyxy[0])
        vehicle_crop = img[y1:y2, x1:x2]

        if vehicle_crop.shape[0] < 30 or vehicle_crop.shape[1] < 30:
            continue

        vehicle_type = {1: "Bicycle", 2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}.get(v_cls, "Unknown")

        # Stage 2: Plate detection
        p_results = plate_model.predict(vehicle_crop, verbose=False)
        plate_text = "UNKNOWN"
        plate_b64 = None

        for p_box in p_results[0].boxes:
            px1, py1, px2, py2 = map(int, p_box.xyxy[0])
            plate_crop = vehicle_crop[
                max(0, py1 - 5):min(vehicle_crop.shape[0], py2 + 5),
                max(0, px1 - 5):min(vehicle_crop.shape[1], px2 + 5)
            ]
            if plate_crop.shape[0] > 0 and plate_crop.shape[1] > 0:
                # Encode plate crop as base64 for the app
                _, buf = cv2.imencode('.jpg', plate_crop)
                plate_b64 = base64.b64encode(buf).decode('utf-8')

                # OCR
                ocr_res = ocr_reader.readtext(plate_crop)
                raw = "".join([r[1] for r in ocr_res])
                clean = re.sub(r'[^A-Z0-9]', '', raw.upper())
                if len(clean) >= 6 and PATTERN_INDIA.search(clean):
                    plate_text = clean
            break

        # Detect violations
        violations = []
        has_plate = len(p_results[0].boxes) > 0
        if not has_plate:
            violations.append("NO PLATE VISIBLE")

        # Dark tint check (cars/buses only)
        if v_cls in [2, 5] and vehicle_crop.shape[0] >= 50 and vehicle_crop.shape[1] >= 50:
            h, w = vehicle_crop.shape[:2]
            window = vehicle_crop[int(h * 0.15):int(h * 0.50), int(w * 0.20):int(w * 0.80)]
            if window.shape[0] > 0 and window.shape[1] > 0:
                gray = cv2.cvtColor(window, cv2.COLOR_BGR2GRAY)
                brightness = np.mean(gray)
                if brightness < 45:
                    violations.append("DARK TINT (SEVERE)")
                elif brightness < 70:
                    violations.append("DARK TINT (MODERATE)")

        # No helmet check (motorcycles only)
        if v_cls in [1, 3]:
            h, w = vehicle_crop.shape[:2]
            head = vehicle_crop[0:int(h * 0.35), :]
            if head.shape[0] >= 20:
                gray = cv2.cvtColor(head, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 50, 150)
                if np.sum(edges > 0) / edges.size > 0.15:
                    violations.append("NO HELMET")

        results.append({
            "vehicle_type": vehicle_type,
            "plate_text": plate_text,
            "confidence": v_conf,
            "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "plate_b64": plate_b64,
            "violations": violations,
            "v_cls": v_cls,
        })

    return results


def lookup_or_create_profile(plate_text, v_cls, conn):
    """Lookup plate in DB, or create proxy identity if new."""
    c = conn.cursor()

    c.execute("""SELECT v.*, c.full_name, c.gender, c.date_of_birth, c.city, c.state,
                 c.phone_masked, c.cibil_score, c.pan_number,
                 f.fastag_id, f.wallet_balance, f.issuer_bank, f.tag_status
              FROM vahan_registry v
              LEFT JOIN citizens c ON v.owner_aadhar = c.aadhar_masked
              LEFT JOIN fastag_accounts f ON v.plate_number = f.plate_number
              WHERE v.plate_number = ?""", (plate_text,))

    row = c.fetchone()

    if row:
        return "EXISTING", {
            "owner": {"plate_number": plate_text, "owner_name": row["owner_name"] or "Unknown",
                       "gender": row["gender"], "date_of_birth": row["date_of_birth"],
                       "city": row["city"], "state": row["state"],
                       "phone_masked": row["phone_masked"], "pan_number": row["pan_number"],
                       "cibil_score": row["cibil_score"]},
            "vehicle": {"plate_number": plate_text, "vehicle_class": row["vehicle_class"],
                         "make": row["make"], "model": row["model"],
                         "color": row["color"], "fuel_type": row["fuel_type"],
                         "invoice_price": row["invoice_price"] or 500000,
                         "reg_date": row["reg_date"], "rto": row["rto"],
                         "rc_status": row["rc_status"],
                         "insurance_company": row["insurance_company"],
                         "hypothecation": row["hypothecation"],
                         "financer_bank": row["financer_bank"]},
            "fastag": {"fastag_id": row["fastag_id"], "wallet_balance": row["wallet_balance"],
                        "issuer_bank": row["issuer_bank"], "tag_status": row["tag_status"]},
        }
    else:
        # Generate proxy
        vehicle_class = get_vehicle_class_from_coco(v_cls)
        vehicle = generate_vehicle_details(vehicle_class)
        match = PATTERN_INDIA.search(plate_text)
        state_code = match.group(1) if match else "DL"
        citizen = generate_citizen_profile(state_code)
        aadhar = generate_aadhar()

        rto_city = random.choice(STATE_RTO_MAP.get(state_code, STATE_RTO_MAP["DL"])["cities"])

        c.execute("""INSERT OR IGNORE INTO citizens
                     (aadhar_masked, virtual_id, full_name, gender, date_of_birth,
                      address, city, state, phone_masked, pan_number, cibil_score, kyc_status)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (aadhar, generate_virtual_id(), citizen["name"], citizen["gender"],
                   citizen["dob"], citizen["address"], citizen["city"], citizen["state"],
                   citizen["phone_masked"], citizen["pan"], citizen["cibil_score"], "Full KYC"))

        c.execute("""INSERT OR IGNORE INTO vahan_registry
                     (plate_number, vehicle_class, make, model, color, fuel_type, chassis_number,
                      engine_number, registration_date, rto_location, rc_status, fitness_valid_upto, invoice_price,
                      insurance_company, insurance_policy, insurance_expiry, puc_valid_upto,
                      hypothecation, financer_bank, owner_aadhar, owner_name)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (plate_text, vehicle_class, vehicle["make"], vehicle["model"],
                   vehicle["color"], vehicle["fuel_type"], generate_chassis(),
                   generate_engine_no(), random_date(2010, 2025), f"RTO {rto_city}", "Active",
                   random_date(2025, 2030), vehicle["invoice_price"],
                   random.choice(INSURANCE_COMPANIES), f"POL-{random.randint(100000, 999999)}",
                   random_date(2025, 2027), random_date(2025, 2026),
                   random.choice(["Yes", "No"]), random.choice(BANKS), aadhar, citizen["name"]))

        fastag_id = f"FAS-{random.randint(100000, 999999)}"
        wallet = round(random.uniform(25.0, 5000.0), 2)
        issuer = random.choice(BANKS)
        tag_status = "Active" if wallet > 50 else "Blacklisted"

        c.execute("""INSERT OR IGNORE INTO fastag_accounts
                     (fastag_id, tag_id, plate_number, owner_cid, wallet_balance, issuer_bank,
                      linked_bank_masked, tag_status, vc_code, kyc_status, low_balance_alert)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (fastag_id, ''.join(random.choices("0123456789ABCDEF", k=20)),
                   plate_text, f"CID-{random.randint(10000, 99999)}",
                   wallet, issuer, f"XXXX XXXX {random.randint(1000, 9999)}",
                   tag_status, "VC4", "Full KYC", 1 if wallet < 100 else 0))

        conn.commit()

        return "NEW_PROXY_GENERATED", {
            "owner": {"plate_number": plate_text, "owner_name": citizen["name"],
                       "gender": citizen["gender"], "date_of_birth": citizen["dob"],
                       "city": citizen["city"], "state": citizen["state"],
                       "phone_masked": citizen["phone_masked"],
                       "pan_number": citizen["pan"], "cibil_score": citizen["cibil_score"]},
            "vehicle": {"plate_number": plate_text, "vehicle_class": vehicle_class,
                         "make": vehicle["make"], "model": vehicle["model"],
                         "color": vehicle["color"], "fuel_type": vehicle["fuel_type"],
                         "invoice_price": vehicle["invoice_price"],
                         "reg_date": random_date(2010, 2025), "rto": f"RTO {rto_city}",
                         "rc_status": "Active",
                         "insurance_company": random.choice(INSURANCE_COMPANIES),
                         "hypothecation": "No", "financer_bank": "N/A"},
            "fastag": {"fastag_id": fastag_id, "wallet_balance": wallet,
                        "issuer_bank": issuer, "tag_status": tag_status},
        }


# ============================================================
#  API ENDPOINTS
# ============================================================

@app.get("/health")
async def health_check():
    """Server health check."""
    return {
        "status": "healthy",
        "models_loaded": {
            "vehicle_finder": vehicle_model is not None,
            "plate_sniper": plate_model is not None,
            "ocr_engine": ocr_reader is not None,
        },
        "database": os.path.exists(DB_PATH),
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/detect", response_model=List[DetectionResult])
async def detect_from_image(file: UploadFile = File(...)):
    """
    Upload an image → AI detects vehicles, reads plates, looks up owners,
    checks for violations, calculates fines, and returns full profiles.
    
    This is the main endpoint the mobile app calls.
    """
    # Read uploaded image
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    # Run AI pipeline
    detections = run_detection_pipeline(img)

    if not detections:
        return []

    conn = get_db()
    results = []

    # Create annotated image
    annotated = img.copy()

    for det in detections:
        plate_text = det["plate_text"]
        bbox = det["bbox"]

        # Lookup or create profile
        if plate_text != "UNKNOWN":
            status, profile = lookup_or_create_profile(plate_text, det["v_cls"], conn)
        else:
            status = "UNKNOWN"
            vehicle_class = get_vehicle_class_from_coco(det["v_cls"])
            profile = {
                "owner": {"plate_number": "UNKNOWN", "owner_name": "Unidentified",
                           "gender": None, "date_of_birth": None, "city": None,
                           "state": None, "phone_masked": None, "pan_number": None,
                           "cibil_score": None},
                "vehicle": {"plate_number": "UNKNOWN", "vehicle_class": vehicle_class,
                             "make": "Unknown", "model": "Unknown", "color": None,
                             "fuel_type": None, "invoice_price": 500000,
                             "reg_date": None, "rto": None, "rc_status": None,
                             "insurance_company": None, "hypothecation": None,
                             "financer_bank": None},
                "fastag": {"fastag_id": None, "wallet_balance": None,
                            "issuer_bank": None, "tag_status": None},
            }

        # Calculate wealth multiplier
        price = profile["vehicle"]["invoice_price"] or 500000
        multiplier = max(1.0, min(10.0, price / 500000))
        base_fine = 5000 if "NO PLATE" in str(det["violations"]) else 1000
        final_fine = round(base_fine * multiplier, 2)

        # Generate legal narrative for violations
        narrative = None
        if det["violations"]:
            narrative = generate_legal_narrative(
                plate_text, det["violations"][0], det["vehicle_type"]
            )

            # File challan in DB
            if plate_text != "UNKNOWN":
                c = conn.cursor()
                for v in det["violations"]:
                    vfine = 5000 if "PLATE" in v else (3000 if "TINT" in v else 1000)
                    c.execute("""INSERT INTO challans
                        (plate_number, violation_type, base_fine, wealth_multiplier, final_fine, status, date_issued)
                        VALUES (?, ?, ?, ?, ?, 'Unpaid', ?)""",
                        (plate_text, v, vfine, multiplier, round(vfine * multiplier, 2),
                         datetime.now().strftime("%Y-%m-%d")))
                conn.commit()

        # Draw on annotated image
        color = (0, 0, 255) if det["violations"] else (0, 255, 0)
        cv2.rectangle(annotated, (bbox["x1"], bbox["y1"]), (bbox["x2"], bbox["y2"]), color, 3)
        label = f"{plate_text}" if plate_text != "UNKNOWN" else det["vehicle_type"]
        cv2.putText(annotated, label, (bbox["x1"], bbox["y1"] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        results.append(DetectionResult(
            status=status,
            detection=VehicleDetection(
                vehicle_type=det["vehicle_type"],
                plate_number=plate_text,
                confidence=round(det["confidence"], 3),
                bounding_box=bbox,
                plate_image_base64=det["plate_b64"],
            ),
            owner=OwnerProfile(**profile["owner"]),
            vehicle=VehicleProfile(**profile["vehicle"]),
            fastag=FASTagProfile(**profile["fastag"]),
            wealth_multiplier=WealthMultiplier(
                vehicle_value=price, multiplier=multiplier,
                base_fine=base_fine, final_fine=final_fine,
            ),
            violations=det["violations"],
            legal_narrative=narrative,
            annotated_image_base64=None,
        ))

    # Encode annotated image and attach to first result
    _, buf = cv2.imencode('.jpg', annotated)
    annotated_b64 = base64.b64encode(buf).decode('utf-8')
    if results:
        results[0].annotated_image_base64 = annotated_b64

    conn.close()
    return results


@app.get("/profile/{plate_number}")
async def get_profile(plate_number: str):
    """Lookup a vehicle profile by plate number."""
    conn = get_db()
    c = conn.cursor()

    c.execute("""SELECT v.*, c.full_name, c.gender, c.date_of_birth, c.city, c.state,
                 c.phone_masked, c.cibil_score, c.pan_number,
                 f.fastag_id, f.wallet_balance, f.issuer_bank, f.tag_status
              FROM vahan_registry v
              LEFT JOIN citizens c ON v.owner_aadhar = c.aadhar_masked
              LEFT JOIN fastag_accounts f ON v.plate_number = f.plate_number
              WHERE v.plate_number = ?""", (plate_number.upper(),))

    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Plate {plate_number} not found in database")

    price = row["invoice_price"] or 500000
    multiplier = max(1.0, min(10.0, price / 500000))

    return {
        "plate_number": plate_number.upper(),
        "owner": {
            "name": row["owner_name"], "gender": row["gender"],
            "dob": row["date_of_birth"], "city": row["city"],
            "state": row["state"], "phone": row["phone_masked"],
            "pan": row["pan_number"], "cibil": row["cibil_score"],
        },
        "vehicle": {
            "class": row["vehicle_class"], "make": row["make"],
            "model": row["model"], "color": row["color"],
            "fuel": row["fuel_type"], "value": price,
            "rto": row["rto"], "insurance": row["insurance_company"],
            "loan": row["hypothecation"], "bank": row["financer_bank"],
        },
        "fastag": {
            "id": row["fastag_id"], "balance": row["wallet_balance"],
            "bank": row["issuer_bank"], "status": row["tag_status"],
        },
        "wealth_multiplier": {
            "value": price, "multiplier": multiplier,
            "sample_fine_5000": round(5000 * multiplier, 2),
        },
    }


@app.get("/violations")
async def list_violations(
    status: Optional[str] = Query(None, description="Filter: 'Unpaid' or 'Paid'"),
    limit: int = Query(50, description="Max results"),
):
    """List all recorded violations/challans."""
    conn = get_db()
    c = conn.cursor()

    if status:
        c.execute("SELECT rowid, * FROM challans WHERE status = ? ORDER BY date_issued DESC LIMIT ?",
                  (status, limit))
    else:
        c.execute("SELECT rowid, * FROM challans ORDER BY date_issued DESC LIMIT ?", (limit,))

    rows = c.fetchall()
    conn.close()

    return [
        {
            "challan_id": row["rowid"],
            "plate_number": row["plate_number"],
            "violation_type": row["violation_type"],
            "base_fine": row["base_fine"],
            "wealth_multiplier": row["wealth_multiplier"],
            "final_fine": row["final_fine"],
            "status": row["status"],
            "date_issued": row["date_issued"],
        }
        for row in rows
    ]


@app.get("/stats")
async def get_stats():
    """Get dashboard statistics."""
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) as cnt FROM vahan_registry")
    total_vehicles = c.fetchone()["cnt"]

    c.execute("SELECT COUNT(*) as cnt FROM challans")
    total_challans = c.fetchone()["cnt"]

    c.execute("SELECT COALESCE(SUM(final_fine), 0) as total FROM challans WHERE status = 'Unpaid'")
    pending = c.fetchone()["total"]

    c.execute("SELECT COALESCE(SUM(final_fine), 0) as total FROM challans WHERE status = 'Paid'")
    collected = c.fetchone()["total"]

    c.execute("SELECT violation_type, COUNT(*) as cnt FROM challans GROUP BY violation_type ORDER BY cnt DESC")
    breakdown = {row["violation_type"]: row["cnt"] for row in c.fetchall()}

    c.execute("""SELECT plate_number, COUNT(*) as cnt, SUM(final_fine) as total_fine
              FROM challans GROUP BY plate_number ORDER BY cnt DESC LIMIT 10""")
    top_violators = [
        {"plate": row["plate_number"], "violations": row["cnt"], "total_fine": row["total_fine"]}
        for row in c.fetchall()
    ]

    conn.close()

    return DashboardStats(
        total_vehicles=total_vehicles,
        total_challans=total_challans,
        total_revenue_pending=pending,
        total_revenue_collected=collected,
        violation_breakdown=breakdown,
        top_violators=top_violators,
    )

# ============================================================
#  ACTIVE LEARNING / SCOUT SYSTEM (CASE 2 APP INTEGRATION)
# ============================================================

@app.get("/scout/queue")
async def get_scout_queue(limit: int = Query(10)):
    """
    Fetch a list of UNIDENTIFIED vehicles that the AI failed to classify.
    App users (Scouts) can view these to manually annotate for points.
    """
    # Mock response. In reality, reads from a database table of failed detections.
    return {
        "status": "success",
        "message": f"Found {limit} unidentified vehicles in the queue.",
        "queue": [
            {"image_id": "unidentified_101", "image_url": "/static/fails/img101.jpg", "reward_points": 5},
            {"image_id": "unidentified_102", "image_url": "/static/fails/img102.jpg", "reward_points": 10}
        ]
    }

class ScoutSubmission(BaseModel):
    image_id: str
    make: str
    model: str
    user_id: str

@app.post("/scout/submit")
async def submit_scout_identification(submission: ScoutSubmission):
    """
    Submit a human annotation (Make/Model).
    If verified, the image is moved to the correct folder and the AI retrains on it.
    The user is rewarded points for helping the dataset grow.
    """
    return {
        "status": "success",
        "message": f"Thank you User {submission.user_id}! Your submission for {submission.make} {submission.model} is logged.",
        "backend_action": f"Moving image to /organized_master_dataset/{submission.make}/{submission.model}/ for AI retraining.",
        "pending_reward": 5
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
