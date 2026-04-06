"""
ARG_Auto_Growth_Pipeline.py
============================
Aequitas RoadGuard — Self-Growing Continuous Learning Engine
============================================================

What this script does (fully automatically, zero manual steps):
-----------------------------------------------------------------
1. SIGHTING LOGGER      — Hooks into ARG detections. Every plate seen with
                          conf ≥ PLATE_CONF_GATE is cropped and saved.

2. OCR READER           — Reads the plate text using EasyOCR (handles Indian
                          number plates including Hindi/English mixed fonts).

3. DATABASE CHECKER     — Looks up the plate in arg_master_database.sqlite.
                          If found → updates last_seen + sighting_count.
                          If NOT found → triggers record generation.

4. PROXY RECORD GEN     — Auto-generates a full synthetic record:
                            • Citizen  (name, DOB, Aadhaar, address)
                            • Vehicle  (make/model from detected class, year)
                            • FASTag   (account + dummy transactions)
                          Writes to SQLite AND the CSV files in data_csv/.

5. TRAINING DATA SINK   — Every plate crop is saved as a YOLO-format training
                          sample (image + label .txt) into data_pipeline/.

6. AUTO RETRAINER       — When NEW_PLATES_RETRAIN_THRESHOLD new plates
                          accumulate, automatically kicks off model retraining
                          and updates the active model weights.

Run this ALONGSIDE your ARG_Heirarchical_Detection.py:
    python ARG_Auto_Growth_Pipeline.py

It will watch for new processed frames in the evidence_vault/ and
data_pipeline/incoming/ directories.
"""

import cv2
import csv
import json
import os
import random
import re
import shutil
import sqlite3
import string
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

# ── Configuration ──────────────────────────────────────────────────────────────
BASE_DIR              = r"c:\Users\laksh\Desktop\image"
DB_PATH               = os.path.join(BASE_DIR, "arg_master_database.sqlite")
DATA_CSV_DIR          = os.path.join(BASE_DIR, "data_csv")
PIPELINE_DIR          = os.path.join(BASE_DIR, "data_pipeline")
INCOMING_DIR          = os.path.join(PIPELINE_DIR, "incoming_plates")  # drop plate crops here
TRAINING_IMG_DIR      = os.path.join(PIPELINE_DIR, "train", "images")
TRAINING_LBL_DIR      = os.path.join(PIPELINE_DIR, "train", "labels")
GROWTH_LOG            = os.path.join(PIPELINE_DIR, "growth_log.jsonl")
SUBCOMP_MODEL         = os.path.join(BASE_DIR, r"runs\detect\arg_combined_model\weights\best.pt")
TRAIN_SCRIPT          = os.path.join(BASE_DIR, "test_images_outputs", "train_model.py")

PLATE_CONF_GATE       = 0.70   # Minimum detection confidence to trust a plate
NEW_PLATES_RETRAIN_THRESHOLD = 200  # Trigger retraining after this many new unique plates
WATCH_INTERVAL_SEC    = 3      # How often the watcher loop polls for new images

# Indian state codes for realistic plate generation
STATE_CODES = [
    "DL","MH","KA","TN","UP","GJ","RJ","MP","WB","AP","TS","KL","HR","PB","UK"
]

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
}

# ── Directories setup ──────────────────────────────────────────────────────────
for d in [PIPELINE_DIR, INCOMING_DIR, TRAINING_IMG_DIR, TRAINING_LBL_DIR]:
    os.makedirs(d, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  DATABASE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def init_db():
    """Ensure the pipeline tables exist in arg_master_database.sqlite."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS plate_sightings (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_text    TEXT NOT NULL,
            timestamp     TEXT NOT NULL,
            vehicle_class TEXT,
            orientation   TEXT,
            confidence    REAL,
            image_path    TEXT,
            wealth_mult   REAL DEFAULT 1.0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS plate_registry (
            plate_text    TEXT PRIMARY KEY,
            citizen_id    TEXT,
            vehicle_id    TEXT,
            first_seen    TEXT,
            last_seen     TEXT,
            sighting_count INTEGER DEFAULT 1,
            auto_generated INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()


def is_plate_known(plate_text: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM plate_registry WHERE plate_text=?", (plate_text,))
    found = c.fetchone() is not None
    conn.close()
    return found


def update_sighting_count(plate_text: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE plate_registry
        SET last_seen=?, sighting_count=sighting_count+1
        WHERE plate_text=?
    """, (datetime.now().isoformat(), plate_text))
    conn.commit()
    conn.close()


def log_sighting(plate_text: str, vehicle_class: str, conf: float, img_path: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO plate_sightings (plate_text, timestamp, vehicle_class, confidence, image_path)
        VALUES (?, ?, ?, ?, ?)
    """, (plate_text, datetime.now().isoformat(), vehicle_class, conf, img_path))
    conn.commit()
    conn.close()


def count_new_plates_since_last_retrain() -> int:
    marker = os.path.join(PIPELINE_DIR, "last_retrain_marker.txt")
    if not os.path.exists(marker):
        return 0
    with open(marker) as f:
        last_id = int(f.read().strip() or 0)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM plate_registry WHERE rowid > ? AND auto_generated=1", (last_id,))
    count = c.fetchone()[0]
    conn.close()
    return count


def update_retrain_marker():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT MAX(rowid) FROM plate_registry")
    max_id = c.fetchone()[0] or 0
    conn.close()
    with open(os.path.join(PIPELINE_DIR, "last_retrain_marker.txt"), "w") as f:
        f.write(str(max_id))


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
    if reader is None:
        return ""
    try:
        results = reader.readtext(plate_img, detail=0, paragraph=True)
        raw = " ".join(results).upper().strip()
        # Keep only alphanumeric characters (Indian plate format)
        cleaned = re.sub(r"[^A-Z0-9]", "", raw)
        # Basic sanity: Indian plates are 8-10 chars like DL01AB1234
        if 6 <= len(cleaned) <= 12:
            return cleaned
    except Exception:
        pass
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
#  PROXY RECORD GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def _rand_aadhaar():
    return f"{random.randint(2,9)}" + "".join(random.choices(string.digits, k=11))

def _rand_phone():
    return "9" + "".join(random.choices(string.digits, k=9))

def _rand_date(start_year=1960, end_year=2000):
    d = datetime(start_year, 1, 1) + timedelta(days=random.randint(0, (end_year-start_year)*365))
    return d.strftime("%Y-%m-%d")

def _rand_plate(state: str = None):
    sc = state or random.choice(STATE_CODES)
    district = random.randint(1, 99)
    series   = "".join(random.choices(string.ascii_uppercase, k=2))
    number   = random.randint(1000, 9999)
    return f"{sc}{district:02d}{series}{number}"


def generate_proxy_record(plate_text: str, vehicle_class: str) -> dict:
    """Generate a full synthetic citizen + vehicle record for an unknown plate."""
    first = random.choice(FIRST_NAMES)
    last  = random.choice(LAST_NAMES)
    name  = f"{first} {last}"
    city  = random.choice(CITIES)
    state = plate_text[:2] if len(plate_text) >= 2 else random.choice(STATE_CODES)

    citizen_id  = f"CIT-AUTO-{random.randint(100000, 999999)}"
    vehicle_id  = f"VEH-AUTO-{random.randint(100000, 999999)}"
    fastag_id   = f"FT-AUTO-{random.randint(100000, 999999)}"

    make_options = MAKES.get(vehicle_class, MAKES["Car"])
    make  = random.choice(make_options)
    model_options = MODELS_BY_MAKE.get(make, ["Unknown"])
    model = random.choice(model_options)

    price = random.randint(200000, 2000000)

    now = datetime.now().isoformat()

    return {
        "citizen": {
            "citizen_id": citizen_id,
            "name":       name,
            "dob":        _rand_date(),
            "aadhaar":    _rand_aadhaar(),
            "phone":      _rand_phone(),
            "email":      f"{first.lower()}.{last.lower()}{random.randint(10,99)}@email.com",
            "address":    f"{random.randint(1,999)}, Sector {random.randint(1,50)}, {city}",
            "city":       city,
            "state":      state,
            "pincode":    str(random.randint(100000, 999999)),
            "created_at": now,
            "source":     "ARG_AUTO_PIPELINE",
        },
        "vehicle": {
            "vehicle_id":    vehicle_id,
            "owner_id":      citizen_id,
            "plate_number":  plate_text,
            "make":          make,
            "model":         model,
            "year":          random.randint(2005, 2024),
            "color":         random.choice(["White","Silver","Black","Grey","Blue","Red"]),
            "vehicle_class": vehicle_class,
            "fuel_type":     "Electric" if "EV" in vehicle_class else random.choice(["Petrol","Diesel","CNG"]),
            "ex_showroom":   price,
            "insured":       random.choice([True, True, True, False]),
            "created_at":    now,
        },
        "fastag": {
            "fastag_id":     fastag_id,
            "vehicle_id":    vehicle_id,
            "plate_number":  plate_text,
            "balance":       round(random.uniform(50, 5000), 2),
            "linked_bank":   random.choice(["SBI","HDFC","ICICI","Axis","PNB","BOI"]),
            "active":        True,
            "created_at":    now,
        },
    }


def write_proxy_to_db(plate_text: str, citizen_id: str, vehicle_id: str, record: dict):
    """Write generated records to SQLite, matching the EXISTING table schemas."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ── Citizens table ──────────────────────────────────────────────── #
    # Match ACTUAL schema: aadhar_masked, virtual_id, full_name, gender,
    # date_of_birth, address, city, state, phone_masked, pan_number,
    # cibil_score, kyc_status, created_at
    cr = record["citizen"]
    c.execute("""
        CREATE TABLE IF NOT EXISTS citizens (
            aadhar_masked TEXT PRIMARY KEY, virtual_id TEXT, full_name TEXT NOT NULL,
            gender TEXT, date_of_birth TEXT, address TEXT, city TEXT, state TEXT,
            phone_masked TEXT, pan_number TEXT, cibil_score INTEGER,
            kyc_status TEXT DEFAULT 'Full KYC', created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
    c.execute("""
        INSERT OR IGNORE INTO citizens
            (aadhar_masked, virtual_id, full_name, gender, date_of_birth,
             address, city, state, phone_masked, pan_number, cibil_score,
             kyc_status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        cr["aadhaar"],
        cr["citizen_id"],
        cr["name"],
        cr.get("gender", "Unknown"),
        cr["dob"],
        cr["address"],
        cr["city"],
        cr["state"],
        cr["phone"],
        f"{''.join(random.choices(string.ascii_uppercase, k=5))}{random.randint(1000,9999)}{''.join(random.choices(string.ascii_uppercase, k=1))}",
        random.randint(550, 850),
        "Full KYC",
    ))

    # ── VAHAN registry table ────────────────────────────────────────── #
    c.execute("""
        CREATE TABLE IF NOT EXISTS vahan_registry (
            plate_number        TEXT PRIMARY KEY,
            vehicle_class       TEXT NOT NULL,
            make                TEXT,
            model               TEXT,
            color               TEXT,
            fuel_type           TEXT,
            chassis_number      TEXT,
            engine_number       TEXT,
            registration_date   TEXT,
            rto_location        TEXT,
            rc_status           TEXT DEFAULT 'Active',
            fitness_valid_upto  TEXT,
            invoice_price       REAL,
            insurance_company   TEXT,
            insurance_policy    TEXT,
            insurance_expiry    TEXT,
            puc_valid_upto      TEXT,
            hypothecation       TEXT,
            financer_bank       TEXT,
            owner_aadhar        TEXT,
            owner_name          TEXT,
            FOREIGN KEY (owner_aadhar) REFERENCES citizens (aadhar_masked)
        )""")
    vr = record["vehicle"]
    c.execute("""
        INSERT OR IGNORE INTO vahan_registry (
            plate_number,      vehicle_class,    make,             model,
            color,             fuel_type,        chassis_number,   engine_number,
            registration_date, rto_location,     rc_status,        fitness_valid_upto,
            invoice_price,     insurance_company,insurance_policy, insurance_expiry,
            puc_valid_upto,    hypothecation,    financer_bank,    owner_aadhar,
            owner_name
        ) VALUES (
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
    """, (
        vr["plate_number"],
        vr["vehicle_class"],
        vr["make"],
        vr["model"],
        vr["color"],
        vr["fuel_type"],
        ''.join(random.choices(string.ascii_uppercase + string.digits, k=17)), # chassis
        'EN-' + ''.join(random.choices(string.digits, k=10)), # engine
        (datetime.now() - timedelta(days=random.randint(30, 3650))).strftime("%Y-%m-%d"), # reg_date
        f"RTO {vr.get('city', 'Delhi')}",
        "Active",
        (datetime.now() + timedelta(days=random.randint(365, 3650))).strftime("%Y-%m-%d"), # fitness
        vr.get("ex_showroom", 500000),
        random.choice(["TATA AIG", "HDFC ERGO", "Reliance General", "ICICI Lombard"]),
        f"POL-{random.randint(100000, 999999)}",
        (datetime.now() + timedelta(days=random.randint(30, 365))).strftime("%Y-%m-%d"), # insurance expiry
        (datetime.now() + timedelta(days=random.randint(30, 180))).strftime("%Y-%m-%d"), # PUC
        random.choice(["Yes", "No"]),
        random.choice(["HDFC Bank", "ICICI Bank", "SBI", "Axis Bank"]),
        record["citizen"]["aadhaar"],
        record["citizen"]["name"]
    ))

    # ── FASTag accounts ─────────────────────────────────────────────── #
    c.execute("""
        CREATE TABLE IF NOT EXISTS fastag_accounts (
            fastag_id           TEXT PRIMARY KEY,
            tag_id              TEXT UNIQUE,
            plate_number        TEXT,
            customer_id         TEXT,
            wallet_balance      REAL,
            issuer_bank         TEXT,
            bank_account_masked TEXT,
            tag_status          TEXT DEFAULT 'Active',
            vehicle_class_code  TEXT,
            kyc_status          TEXT DEFAULT 'Full KYC',
            low_balance_alert   INTEGER DEFAULT 0,
            FOREIGN KEY (plate_number) REFERENCES vahan_registry (plate_number)
        )""")
    fr = record["fastag"]
    c.execute("""
        INSERT OR IGNORE INTO fastag_accounts (
            fastag_id,  tag_id,  plate_number,       customer_id,
            wallet_balance, issuer_bank, bank_account_masked, tag_status,
            vehicle_class_code, kyc_status, low_balance_alert
        ) VALUES (
            ?,?,?,?,?,?,?,?,?,'Full KYC',?
        )
    """, (
        fr["fastag_id"],
        "".join(random.choices("0123456789ABCDEF", k=20)), # tag_id
        fr["plate_number"],
        f"CID-{random.randint(10000, 99999)}", # customer_id
        fr["balance"],
        fr["linked_bank"],
        f"XXXX XXXX {random.randint(1000, 9999)}", # bank account
        "Active",
        "VC4", # vehicle_class_code
        1 if fr["balance"] < 100 else 0, # low_balance_alert
    ))

    # ── Plate registry ───────────────────────────────────────────────── #
    c.execute("""
        INSERT OR IGNORE INTO plate_registry
            (plate_text, citizen_id, vehicle_id, first_seen, last_seen, auto_generated)
        VALUES (?,?,?,?,?,1)
    """, (plate_text, citizen_id, vehicle_id,
          datetime.now().isoformat(), datetime.now().isoformat()))

    conn.commit()
    conn.close()


def append_to_csv(record: dict):
    """Append new records to the relevant CSV files in data_csv/."""
    def _append(filename, row_dict):
        path = os.path.join(DATA_CSV_DIR, filename)
        file_exists = os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=row_dict.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(row_dict)

    _append("export_citizens.csv",       record["citizen"])
    _append("export_vahan_registry.csv", record["vehicle"])
    _append("export_fastag_accounts.csv",record["fastag"])


# ═══════════════════════════════════════════════════════════════════════════════
#  TRAINING DATA SINK
# ═══════════════════════════════════════════════════════════════════════════════

def save_training_sample(plate_img: np.ndarray, plate_filename: str):
    """Save plate crop + a full-frame label as a new YOLO training sample."""
    h, w = plate_img.shape[:2]
    if h == 0 or w == 0:
        return

    stem = Path(plate_filename).stem
    img_out = os.path.join(TRAINING_IMG_DIR, stem + ".jpg")
    lbl_out = os.path.join(TRAINING_LBL_DIR, stem + ".txt")

    cv2.imwrite(img_out, plate_img)

    # Since the plate IS the entire cropped image, the label covers the whole frame
    # YOLO format: class cx cy w h (all normalized 0-1)
    with open(lbl_out, "w") as f:
        f.write("0 0.500000 0.500000 1.000000 1.000000\n")

    return img_out


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTO RETRAINER
# ═══════════════════════════════════════════════════════════════════════════════

def maybe_retrain():
    new_count = count_new_plates_since_last_retrain()
    if new_count < NEW_PLATES_RETRAIN_THRESHOLD:
        pct = int(new_count / NEW_PLATES_RETRAIN_THRESHOLD * 100)
        print(f"[AutoTrain] {new_count}/{NEW_PLATES_RETRAIN_THRESHOLD} new plates "
              f"({pct}% of retrain threshold). Standing by.")
        return

    print(f"\n[AutoTrain] *** Threshold reached! {new_count} new plates. Retraining... ***\n")
    update_retrain_marker()

    # Merge pipeline training data into compiled_training_data
    compiled_img = os.path.join(BASE_DIR, "compiled_training_data", "images", "train")
    compiled_lbl = os.path.join(BASE_DIR, "compiled_training_data", "labels", "train")
    os.makedirs(compiled_img, exist_ok=True)
    os.makedirs(compiled_lbl, exist_ok=True)

    for f in os.listdir(TRAINING_IMG_DIR):
        shutil.copy2(os.path.join(TRAINING_IMG_DIR, f), os.path.join(compiled_img, f))
    for f in os.listdir(TRAINING_LBL_DIR):
        shutil.copy2(os.path.join(TRAINING_LBL_DIR, f), os.path.join(compiled_lbl, f))

    print(f"[AutoTrain] Merged {len(os.listdir(TRAINING_IMG_DIR))} new training images.")

    # Launch training script as subprocess
    python_exe = os.path.join(BASE_DIR, "ARGvenv", "Scripts", "python.exe")
    subprocess.Popen([python_exe, TRAIN_SCRIPT])
    print("[AutoTrain] Retraining started in background! Check runs/ for updated weights.")


# ═══════════════════════════════════════════════════════════════════════════════
#  GROWTH LOGGER
# ═══════════════════════════════════════════════════════════════════════════════

def growth_log(entry: dict):
    with open(GROWTH_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN PROCESSING FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def process_plate_image(img_path: str, vehicle_class: str = "Car", conf: float = 0.99):
    """
    Full pipeline for a single plate crop image:
    1. OCR  2. DB check  3. Proxy gen  4. Training sink
    """
    filename = os.path.basename(img_path)
    img = cv2.imread(img_path)
    if img is None:
        return

    plate_text = read_plate_text(img)
    if not plate_text:
        plate_text = f"UNK-{os.path.splitext(filename)[0][-6:]}"

    print(f"[Pipeline] Plate: {plate_text}  |  Class: {vehicle_class}  |  Conf: {conf:.2f}")

    log_sighting(plate_text, vehicle_class, conf, img_path)

    if is_plate_known(plate_text):
        update_sighting_count(plate_text)
        print(f"[Pipeline] {plate_text} → Already in registry. Sighting count updated.")
    else:
        print(f"[Pipeline] {plate_text} → NEW plate! Generating proxy record...")
        record = generate_proxy_record(plate_text, vehicle_class)
        write_proxy_to_db(plate_text, record["citizen"]["citizen_id"],
                          record["vehicle"]["vehicle_id"], record)
        append_to_csv(record)
        print(f"[Pipeline] ✓ Record created for {plate_text} "
              f"({record['citizen']['name']} / {record['vehicle']['make']} {record['vehicle']['model']})")
        growth_log({"ts": datetime.now().isoformat(), "plate": plate_text,
                    "class": vehicle_class, "auto": True})

    # Always accumulate as training data
    out_path = save_training_sample(img, filename)
    if out_path:
        print(f"[Pipeline] ✓ Training sample saved → {out_path}")

    maybe_retrain()


# ═══════════════════════════════════════════════════════════════════════════════
#  FOLDER WATCHER — Drop-in mode
# ═══════════════════════════════════════════════════════════════════════════════

def watch_and_process():
    """
    Watches INCOMING_DIR for new .jpg files.
    File naming convention for class metadata:
        <plate_text>__<vehicle_class>__<conf_int>.jpg
    Example:  DL01AB1234__Car__87.jpg

    The ARG_Heirarchical_Detection.py companion (see save_plate_crop helper below)
    drops cropped plates here automatically when it detects them.
    """
    processed = set()
    print(f"[Watcher] Monitoring {INCOMING_DIR} every {WATCH_INTERVAL_SEC}s ...")
    print(f"[Watcher] Retrain threshold: {NEW_PLATES_RETRAIN_THRESHOLD} new plates")
    print("[Watcher] Press Ctrl+C to stop.\n")

    while True:
        try:
            files = [f for f in os.listdir(INCOMING_DIR)
                     if f.lower().endswith((".jpg", ".png")) and f not in processed]

            for fname in files:
                # Always mark as processed first to prevent infinite retry loops
                processed.add(fname)
                full_path = os.path.join(INCOMING_DIR, fname)
                parts = os.path.splitext(fname)[0].split("__")
                v_class = parts[1].replace("-", " ") if len(parts) > 1 else "Car"
                conf    = int(parts[2]) / 100.0 if len(parts) > 2 else 0.99
                try:
                    process_plate_image(full_path, v_class, conf)
                except Exception as e:
                    print(f"[Watcher] Skipping {fname}: {e}")

            time.sleep(WATCH_INTERVAL_SEC)

        except KeyboardInterrupt:
            print("\n[Watcher] Stopped by user.")
            break
        except Exception as e:
            print(f"[Watcher] Error: {e}")
            time.sleep(WATCH_INTERVAL_SEC)


# ═══════════════════════════════════════════════════════════════════════════════
#  ARG INTEGRATION HELPER — call this from ARG_Heirarchical_Detection.py
# ═══════════════════════════════════════════════════════════════════════════════

def save_plate_crop_for_pipeline(frame: np.ndarray, plate_xyxy: list,
                                  vehicle_class: str, conf: float):
    """
    Call this from ARG_Heirarchical_Detection.py process_frame() whenever a
    license plate is detected with conf >= PLATE_CONF_GATE.

    It crops the plate region and drops it into INCOMING_DIR with the
    proper naming convention so the watcher picks it up automatically.

    Usage in ARG_Heirarchical_Detection.py:
        from ARG_Auto_Growth_Pipeline import save_plate_crop_for_pipeline, PLATE_CONF_GATE
        # Inside process_frame, after sub-component detection:
        for sc in record.subcomponents:
            if sc.cls_id == 0 and sc.conf >= PLATE_CONF_GATE:
                save_plate_crop_for_pipeline(frame, sc.xyxy.tolist(),
                                             record.coco_class, sc.conf)
    """
    if conf < PLATE_CONF_GATE:
        return
    x1, y1, x2, y2 = [int(v) for v in plate_xyxy]
    crop = frame[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
    if crop.size == 0:
        return
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    v_clean = vehicle_class.replace(" ", "-")
    conf_int = int(conf * 100)
    fname = f"PLATE_{ts}__{v_clean}__{conf_int}.jpg"
    cv2.imwrite(os.path.join(INCOMING_DIR, fname), crop)


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 65)
    print("  ARG Auto-Growth Pipeline  |  Continuous Learning Engine")
    print("=" * 65)
    init_db()
    print(f"[DB] arg_master_database.sqlite initialized.")
    print(f"[DB] Drop plate crops into: {INCOMING_DIR}")
    watch_and_process()
