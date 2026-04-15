"""
ARG_Auto_Growth_Pipeline.py
============================
Aequitas RoadGuard — Self-Growing Continuous Learning Engine (MySQL Version)
=============================================================================

What this script does (fully automatically, zero manual steps):
-----------------------------------------------------------------
1. SIGHTING LOGGER      — Hooks into ARG detections. Every plate seen.
2. OCR READER           — Reads the plate text using EasyOCR.
3. DATABASE CHECKER     — Looks up the plate in MySQL.
4. PROXY RECORD GEN     — Auto-generates a full synthetic record if new.
5. TRAINING DATA SINK   — Saves crops as YOLO-format training samples.
6. AUTO RETRAINER       — Retrains model after NEW_PLATES_RETRAIN_THRESHOLD.
"""

import os
import sys
import random
import string
import re
import json
import subprocess
import shutil
import cv2
import csv
import time
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

# Add project root to path
root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from src.database.manager import DBManager
from src.utils.config import (
    DATA_CSV_DIR, PIPELINE_DIR, INCOMING_DIR, TRAINING_IMG_DIR,
    TRAINING_LBL_DIR, GROWTH_LOG, SUBCOMP_MODEL, TRAIN_SCRIPT,
    BASE_DIR
)

# ── Configuration ──────────────────────────────────────────────────────────────
GROWTH_LOG_FILE       = os.path.join(PIPELINE_DIR, "growth_log.jsonl")
PLATE_CONF_GATE       = 0.50   # Lowered from 0.70 to capture more experimental data
NEW_PLATES_RETRAIN_THRESHOLD = 200  
WATCH_INTERVAL_SEC    = 3      

# Indian state codes
STATE_CODES = ["DL","MH","KA","TN","UP","GJ","RJ","MP","WB","AP","TS","KL","HR","PB","UK"]

FIRST_NAMES = [
    "Rahul","Priya","Amit","Neha","Suresh","Pooja","Rajesh","Anjali","Vikram",
    "Sunita","Arun","Meena","Deepak","Kavita","Manoj","Rekha","Sanjay","Shilpa",
    "Arjun","Divya","Kiran","Ravi","Lakshmi","Gopal","Sita","Ramesh","Usha",
]

LAST_NAMES = [
    "Sharma","Verma","Singh","Kumar","Gupta","Patel","Joshi","Mehta","Rao","Nair",
    "Iyer","Pillai","Mishra","Agarwal","Tiwari","Pandey","Sinha","Yadav","Shah",
]

CITIES = [
    "New Delhi","Mumbai","Bengaluru","Chennai","Hyderabad","Ahmedabad","Jaipur",
    "Lucknow","Kolkata","Pune","Chandigarh","Noida","Gurgaon","Faridabad",
]

MAKES = {
    "Car":                ["Maruti Suzuki","Hyundai","Tata","Honda","Toyota","Kia","MG","Renault"],
    "Motorcycle":         ["Hero","Honda","Bajaj","TVS","Royal Enfield","Yamaha","Suzuki"],
    "Commercial Taxi":    ["Maruti Suzuki","Tata","Mahindra"],
    "EV Taxi":            ["Tata","MG","Hyundai","BYD"],
    "EV (Private)":       ["Tata","MG","Hyundai","Ola Electric","Ather"],
    "3-Wheeler":          ["Bajaj","Piaggio","TVS"],
    "Small Commercial":   ["Tata","Mahindra","Ashok Leyland"],
    "Heavy Commercial":   ["Tata","Ashok Leyland","Mahindra","Eicher"],
    "Commercial Vehicle": ["Tata","Ashok Leyland","Mahindra"],
}

MODELS_BY_MAKE = {
    "Maruti Suzuki": ["Swift Dzire","WagonR","Alto","Swift","Ertiga","Baleno","Brezza"],
    "Hyundai":       ["Grand i10","i20","Venue","Creta","Verna","Santro","Aura"],
    "Tata":          ["Nexon","Punch","Altroz","Harrier","Tigor","Safari","Ace"],
    "Honda":         ["Amaze","City","Jazz","WR-V"],
    "Hero":          ["Splendor","Passion","HF Deluxe","Xtreme","Glamour"],
    "Bajaj":         ["Pulsar","Platina","CT100","Dominar","RE Auto"],
    "TVS":           ["Jupiter","Apache","XL100","Sport"],
    "Audi":          ["Q7", "A4", "A6", "Q3", "RS5"],
    "Bmw":           ["X5", "3 Series", "5 Series", "X3", "M4"],
    "Kia":           ["Seltos", "Sonet", "Carens", "Carnival"],
    "Lamborghini":   ["Urus", "Huracan", "Aventador"],
    "Land-rover":    ["Range Rover", "Defender", "Discovery"],
}

# ── Directories setup ──────────────────────────────────────────────────────────
for d in [PIPELINE_DIR, INCOMING_DIR, TRAINING_IMG_DIR, TRAINING_LBL_DIR]:
    os.makedirs(d, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  DATABASE HELPERS (MySQL Optimized)
# ═══════════════════════════════════════════════════════════════════════════════

def init_db():
    """Ensure the pipeline tables exist in MySQL."""
    DBManager.ensure_schema()

def get_known_vehicle_info(plate_text: str) -> dict:
    """Check MySQL database for existing data."""
    row = DBManager.fetch_one("SELECT * FROM vahan_registry WHERE plate_number=%s", (plate_text,))
    if row:
        return {
            "vehicle": row,
            "citizen": DBManager.fetch_one("SELECT * FROM citizens WHERE aadhar_masked=%s", (row.get("owner_aadhar"),))
        }
    return None

def is_plate_known(plate_text: str) -> bool:
    info = get_known_vehicle_info(plate_text)
    return info is not None

def update_sighting_count(plate_text: str):
    DBManager.execute("""
        UPDATE plate_registry
        SET last_seen=NOW(), sighting_count=sighting_count+1
        WHERE plate_text=%s
    """, (plate_text,))

def log_sighting(plate_text: str, vehicle_class: str, conf: float, img_path: str):
    DBManager.execute("""
        INSERT INTO plate_sightings (plate_text, timestamp, vehicle_class, confidence, image_path)
        VALUES (%s, NOW(), %s, %s, %s)
    """, (plate_text, vehicle_class, conf, img_path))

def count_new_plates_since_last_retrain() -> int:
    marker = os.path.join(PIPELINE_DIR, "last_retrain_count.txt")
    last_count = 0
    if os.path.exists(marker):
        with open(marker) as f:
            last_count = int(f.read().strip() or "0")
    
    row = DBManager.fetch_one("SELECT COUNT(*) as cnt FROM plate_registry WHERE auto_generated=1")
    total = row["cnt"] if row else 0
    return max(0, total - last_count)

def update_retrain_marker():
    row = DBManager.fetch_one("SELECT COUNT(*) as cnt FROM plate_registry")
    max_count = row["cnt"] if row else 0
    with open(os.path.join(PIPELINE_DIR, "last_retrain_count.txt"), "w") as f:
        f.write(str(max_count))


# ═══════════════════════════════════════════════════════════════════════════════
#  OCR — Read License Plate Text
# ═══════════════════════════════════════════════════════════════════════════════

_ocr_reader = None

def get_ocr():
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            _ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        except ImportError:
            print("[OCR] easyocr not installed. Run: pip install easyocr")
            _ocr_reader = None
    return _ocr_reader

def read_plate_text(plate_img: np.ndarray) -> str:
    """Returns cleaned plate text or empty string if OCR fails."""
    reader = get_ocr()
    if reader is None: return ""
    try:
        results = reader.readtext(plate_img, detail=0, paragraph=True)
        raw = " ".join(results).upper().strip()
        cleaned = re.sub(r"[^A-Z0-9]", "", raw)
        if 6 <= len(cleaned) <= 12:
            return cleaned
    except Exception:
        pass
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
#  PROXY RECORD GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def _rand_aadhaar(): return f"{random.randint(2,9)}" + "".join(random.choices(string.digits, k=11))
def _rand_phone():   return "9" + "".join(random.choices(string.digits, k=9))
def _rand_date(s=1960, e=2000):
    d = datetime(s, 1, 1) + timedelta(days=random.randint(0, (e-s)*365))
    return d.strftime("%Y-%m-%d")

def extract_fine_grained_features(img_path: str) -> dict:
    fname = os.path.basename(img_path).lower()
    features = {"make": None, "orientation": "Front", "model": None}
    brands = ["audi", "bmw", "honda", "hyundai", "kia", "lamborghini", "land-rover", "tata", "mahindra", "maruti"]
    for b in brands:
        if b in fname:
            features["make"] = b.capitalize()
            break
    if any(x in fname for x in ["rear", "back", "tail"]):
        features["orientation"] = "Back"
    return features

def generate_proxy_record(plate_text: str, vehicle_class: str, features: dict = None) -> dict:
    features = features or {"make": None, "model": None, "orientation": "Front"}
    first = random.choice(FIRST_NAMES)
    last  = random.choice(LAST_NAMES)
    city  = random.choice(CITIES)
    state = plate_text[:2] if len(plate_text) >= 2 else random.choice(STATE_CODES)

    make = features.get("make") or random.choice(MAKES.get(vehicle_class, MAKES["Car"]))
    model = random.choice(MODELS_BY_MAKE.get(make, ["Standard City"]))
    price = random.randint(200000, 2000000)
    if make in ["Audi", "Bmw", "Lamborghini"]: price = random.randint(5000000, 25000000)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "citizen": {
            "citizen_id": f"CIT-{random.randint(1000,9999)}",
            "name": f"{first} {last}",
            "dob": _rand_date(),
            "aadhaar": _rand_aadhaar(),
            "phone": _rand_phone(),
            "address": f"{random.randint(1,99)}, Sector {random.randint(1,10)}, {city}",
            "city": city, "state": state,
        },
        "vehicle": {
            "vehicle_id": f"VEH-{random.randint(1000,9999)}",
            "plate_number": plate_text,
            "make": make, "model": model, "year": random.randint(2010, 2024),
            "color": random.choice(["White","Black","Silver"]),
            "vehicle_class": vehicle_class,
            "fuel_type": random.choice(["Petrol","Diesel"]),
            "ex_showroom": price,
        },
        "fastag": {
            "fastag_id": f"FT-{random.randint(1000,9999)}",
            "balance": round(random.uniform(100, 2000), 2),
            "linked_bank": random.choice(["SBI","HDFC"]),
        }
    }

def write_proxy_to_db(plate_text: str, record: dict):
    cr = record["citizen"]
    # Citizens
    DBManager.execute("""
        INSERT IGNORE INTO citizens (aadhar_masked, virtual_id, full_name, gender, date_of_birth, address, city, state, phone_masked, kyc_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Full KYC')
    """, (cr["aadhaar"], cr["citizen_id"], cr["name"], random.choice(["M","F"]), cr["dob"], cr["address"], cr["city"], cr["state"], cr["phone"]))

    # Vahan
    vr = record["vehicle"]
    DBManager.execute("""
        INSERT IGNORE INTO vahan_registry (plate_number, vehicle_class, make, model, color, fuel_type, chassis_number, engine_number, registration_date, rto_location, owner_aadhar, owner_name, invoice_price)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (plate_text, vr["vehicle_class"], vr["make"], vr["model"], vr["color"], vr["fuel_type"], f"CH{random.randint(1000,9999)}", f"EN{random.randint(1000,9999)}", "2023-01-01", f"RTO {cr['city']}", cr["aadhaar"], cr["name"], vr["ex_showroom"]))

    # Fastag
    fr = record["fastag"]
    DBManager.execute("""
        INSERT IGNORE INTO fastag_accounts (fastag_id, plate_number, wallet_balance, issuer_bank, tag_status)
        VALUES (%s, %s, %s, %s, 'Active')
    """, (fr["fastag_id"], plate_text, fr["balance"], fr["linked_bank"]))

    # Registry Index
    DBManager.execute("""
        INSERT IGNORE INTO plate_registry (plate_text, citizen_id, vehicle_id, first_seen, last_seen, auto_generated)
        VALUES (%s, %s, %s, NOW(), NOW(), 1)
    """, (plate_text, cr["citizen_id"], vr["vehicle_id"]))


def append_to_csv(record: dict):
    os.makedirs(DATA_CSV_DIR, exist_ok=True)
    def _app(fn, data):
        path = os.path.join(DATA_CSV_DIR, fn)
        ex = os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=data.keys())
            if not ex: w.writeheader()
            w.writerow(data)

    _app("export_citizens.csv", record["citizen"])
    _app("export_vahan_registry.csv", record["vehicle"])
    
    # Master Row for easy app lookup
    master = {
        "License Plate": record["vehicle"]["plate_number"],
        "Owner Name": record["citizen"]["name"],
        "Vehicle": f"{record['vehicle']['make']} {record['vehicle']['model']}",
        "Class": record["vehicle"]["vehicle_class"],
        "FASTag Balance": f"₹{record['fastag']['balance']}",
    }
    _app("ARG_Proxy_Dataset_Master.csv", master)


# ═══════════════════════════════════════════════════════════════════════════════
#  TRAINING DATA SINK
# ═══════════════════════════════════════════════════════════════════════════════

def save_training_sample(plate_img: np.ndarray, plate_filename: str):
    h, w = plate_img.shape[:2]
    if h == 0 or w == 0: return
    stem = Path(plate_filename).stem
    img_out = os.path.join(TRAINING_IMG_DIR, stem + ".jpg")
    lbl_out = os.path.join(TRAINING_LBL_DIR, stem + ".txt")
    cv2.imwrite(img_out, plate_img)
    with open(lbl_out, "w") as f:
        # We tag this as class 0 in the pipeline training (Generic Plate/Vehicle)
        f.write("0 0.500000 0.500000 1.000000 1.000000\n")
    return img_out


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTO RETRAINER
# ═══════════════════════════════════════════════════════════════════════════════

def maybe_retrain():
    new = count_new_plates_since_last_retrain()
    if new < NEW_PLATES_RETRAIN_THRESHOLD:
        print(f"[AutoTrain] {new}/{NEW_PLATES_RETRAIN_THRESHOLD} new plates. Standing by.")
        return

    print(f"\n[AutoTrain] Threshold reached ({new})! Starting Retrain...\n")
    update_retrain_marker()
    
    python_exe = os.path.join(BASE_DIR, "ARGvenv", "Scripts", "python.exe")
    if not os.path.exists(python_exe): python_exe = "python"
    
    subprocess.Popen([python_exe, TRAIN_SCRIPT])
    print("[AutoTrain] Training triggered in background.")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

def process_plate_image(img_path: str, vehicle_class: str = "Car", conf: float = 0.99):
    filename = os.path.basename(img_path)
    img = cv2.imread(img_path)
    if img is None: return

    plate_text = read_plate_text(img)
    if not plate_text:
        plate_text = f"AUTO-{filename[:6]}"

    features = extract_fine_grained_features(img_path)
    log_sighting(plate_text, vehicle_class, conf, img_path)

    existing = get_known_vehicle_info(plate_text)
    if existing:
        update_sighting_count(plate_text)
        print(f"[Pipeline] {plate_text} → Re-sighting: {existing['vehicle']['make']} ({features['orientation']})")
    else:
        print(f"[Pipeline] {plate_text} → Discovery! Brand: {features['make'] or 'Unknown'}")
        record = generate_proxy_record(plate_text, vehicle_class, features)
        write_proxy_to_db(plate_text, record)
        append_to_csv(record)
        print(f"[Pipeline] ✓ Record Created: {record['citizen']['name']}")

    save_training_sample(img, filename)
    maybe_retrain()


def watch_and_process():
    processed = set()
    print(f"[Watcher] Scanning {INCOMING_DIR} ...")
    while True:
        try:
            files = [f for f in os.listdir(INCOMING_DIR) if f.lower().endswith((".jpg",".png")) and f not in processed]
            for fn in files:
                processed.add(fn)
                p = os.path.join(INCOMING_DIR, fn)
                parts = fn.split("__")
                v_class = parts[1] if len(parts) > 1 else "Car"
                process_plate_image(p, v_class.replace("-"," "))
            time.sleep(WATCH_INTERVAL_SEC)
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"[Watcher] Error: {e}")
            time.sleep(WATCH_INTERVAL_SEC)

if __name__ == "__main__":
    init_db()
    print("="*60)
    print("  ARG AUTO-GROWTH PIPELINE (MySQL Version)")
    print("="*60)
    watch_and_process()
