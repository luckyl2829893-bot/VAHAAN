"""
ARG Live Detect — Real-Time Plate Detection + Auto-Proxy Identity Generator

Usage:
    python live_detect.py path/to/image.jpg
    python live_detect.py path/to/folder/

When a NEW license plate is detected that doesn't exist in the database,
the system automatically creates a full simulated proxy identity (Aadhaar,
VAHAN record, FASTag wallet) and displays the complete profile on screen.
"""

import os
import sys
import cv2
import re
import sqlite3
import random
from datetime import datetime, timedelta
from ultralytics import YOLO
import easyocr

# Import the data generators from the main proxy database script
from generate_proxy_database import (
    STATE_RTO_MAP, VEHICLE_PROFILES, INSURANCE_COMPANIES, BANKS,
    generate_aadhar, generate_virtual_id, generate_pan, generate_chassis,
    generate_engine_no, random_date, get_vehicle_class_from_coco,
    generate_vehicle_details, generate_citizen_profile,
    generate_fastag_transactions, create_database_schema
)

PATTERN_INDIA = re.compile(r'([A-Z]{2})([0-9]{1,2})([A-Z]{1,3})([0-9]{1,4})')
DB_PATH = 'arg_master_database.sqlite'


def load_models():
    """Load the Two-Stage AI models once."""
    print("Loading Stage 1 (Vehicle Finder): yolo11m.pt...")
    vehicle_model = YOLO("yolo11m.pt")
    
    plate_path = r"runs\detect\plate_model_train_final\weights\best.pt"
    if not os.path.exists(plate_path):
        print(f"ERROR: Plate Sniper not found at {plate_path}")
        sys.exit(1)

    print("Loading Stage 2 (Plate Sniper)...")
    plate_model = YOLO(plate_path)
    
    print("Loading EasyOCR Engine...")
    reader = easyocr.Reader(['en'], gpu=True)
    
    return vehicle_model, plate_model, reader


def lookup_or_create_profile(plate_number, state_code, vehicle_coco_class, conn):
    """
    Check if plate exists in DB.
    If YES → return existing profile.
    If NO  → auto-generate a full proxy identity, insert it, return the new profile.
    """
    c = conn.cursor()
    
    # Check if plate already exists
    c.execute("""SELECT v.*, c.full_name, c.gender, c.date_of_birth, c.city, c.state,
                 c.phone_masked, c.cibil_score, c.pan_number,
                 f.fastag_id, f.wallet_balance, f.issuer_bank, f.tag_status
              FROM vahan_registry v
              LEFT JOIN citizens c ON v.owner_aadhar = c.aadhar_masked
              LEFT JOIN fastag_accounts f ON v.plate_number = f.plate_number
              WHERE v.plate_number = ?""", (plate_number,))
    
    row = c.fetchone()
    
    if row:
        # Existing profile found!
        return {
            "status": "EXISTING",
            "plate": plate_number,
            "vehicle_class": row[1], "make": row[2], "model": row[3],
            "color": row[4], "fuel": row[5],
            "chassis": row[6], "engine": row[7],
            "reg_date": row[8], "rto": row[9], "rc_status": row[10],
            "fitness_valid": row[11], "invoice_price": row[12],
            "insurance_co": row[13], "insurance_policy": row[14],
            "insurance_expiry": row[15], "puc_valid": row[16],
            "hypothecation": row[17], "financer": row[18],
            "owner_name": row[21], "gender": row[22], "dob": row[23],
            "city": row[24], "state": row[25], "phone": row[26],
            "cibil": row[27], "pan": row[28],
            "fastag_id": row[29], "wallet_balance": row[30],
            "issuer_bank": row[31], "tag_status": row[32],
        }
    
    # ---- NEW PLATE: Auto-generate proxy identity ----
    vehicle_class = get_vehicle_class_from_coco(vehicle_coco_class)
    vehicle = generate_vehicle_details(vehicle_class)
    citizen = generate_citizen_profile(state_code)
    aadhar = generate_aadhar()
    virtual_id = generate_virtual_id()
    
    rto_city = random.choice(STATE_RTO_MAP.get(state_code, STATE_RTO_MAP["DL"])["cities"])
    reg_date = random_date(2010, 2025)
    fitness_date = random_date(2025, 2030)
    insurance_co = random.choice(INSURANCE_COMPANIES)
    insurance_policy = f"POL-{random.randint(100000, 999999)}"
    insurance_expiry = random_date(2025, 2027)
    puc_date = random_date(2025, 2026)
    
    has_loan = random.choice([True, False])
    hypothecation = "Yes" if has_loan else "No"
    financer = random.choice(BANKS) if has_loan else "N/A"
    
    fastag_id = f"FAS-{random.randint(100000, 999999)}"
    tag_id = ''.join(random.choices("0123456789ABCDEF", k=20))
    wallet = round(random.uniform(25.0, 5000.0), 2)
    issuer = random.choice(BANKS)
    bank_masked = f"XXXX XXXX {random.randint(1000, 9999)}"
    vc_code = {"2-Wheeler": "VC2", "3-Wheeler": "VC3",
               "4-Wheeler (Hatchback)": "VC4", "4-Wheeler (Luxury SUV)": "VC4",
               "Heavy Commercial": "VC7"}.get(vehicle_class, "VC4")
    low_bal = 1 if wallet < 100 else 0
    tag_status = "Active" if wallet > 50 else "Blacklisted"
    
    # Insert into DB
    c.execute("""INSERT OR IGNORE INTO citizens
                 (aadhar_masked, virtual_id, full_name, gender, date_of_birth,
                  address, city, state, phone_masked, pan_number, cibil_score, kyc_status)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
              (aadhar, virtual_id, citizen["name"], citizen["gender"], citizen["dob"],
               citizen["address"], citizen["city"], citizen["state"],
               citizen["phone_masked"], citizen["pan"], citizen["cibil_score"], "Full KYC"))
    
    c.execute("""INSERT OR IGNORE INTO vahan_registry
                 (plate_number, vehicle_class, make, model, color, fuel_type, chassis_number,
                  engine_number, registration_date, rto_location, rc_status, fitness_valid_upto, invoice_price,
                  insurance_company, insurance_policy, insurance_expiry, puc_valid_upto,
                  hypothecation, financer_bank, owner_aadhar, owner_name)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (plate_number, vehicle_class, vehicle["make"], vehicle["model"],
               vehicle["color"], vehicle["fuel_type"], generate_chassis(),
               generate_engine_no(), reg_date, f"RTO {rto_city}", "Active",
               fitness_date, vehicle["invoice_price"], insurance_co,
               insurance_policy, insurance_expiry, puc_date,
               hypothecation, financer, aadhar, citizen["name"]))
    
    c.execute("""INSERT OR IGNORE INTO fastag_accounts
                 (fastag_id, tag_id, plate_number, owner_cid, wallet_balance, issuer_bank,
                  linked_bank_masked, tag_status, vc_code, kyc_status, low_balance_alert)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
              (fastag_id, tag_id, plate_number, f"CID-{random.randint(10000, 99999)}",
               wallet, issuer, bank_masked, tag_status, vc_code, "Full KYC", low_bal))
    
    # Generate toll transactions
    transactions = generate_fastag_transactions()
    for tx in transactions:
        c.execute("INSERT INTO fastag_transactions (fastag_id, toll_plaza, timestamp, amount_deducted) VALUES (?,?,?,?)",
                  (fastag_id, tx["toll_plaza"], tx["timestamp"], tx["amount_deducted"]))
    
    conn.commit()
    
    return {
        "status": "NEW (Auto-Generated)",
        "plate": plate_number,
        "vehicle_class": vehicle_class,
        "make": vehicle["make"], "model": vehicle["model"],
        "color": vehicle["color"], "fuel": vehicle["fuel_type"],
        "invoice_price": vehicle["invoice_price"],
        "reg_date": reg_date, "rto": f"RTO {rto_city}", "rc_status": "Active",
        "insurance_co": insurance_co, "hypothecation": hypothecation,
        "financer": financer,
        "owner_name": citizen["name"], "gender": citizen["gender"],
        "dob": citizen["dob"], "city": citizen["city"], "state": citizen["state"],
        "phone": citizen["phone_masked"], "cibil": citizen["cibil_score"],
        "pan": citizen["pan"],
        "fastag_id": fastag_id, "wallet_balance": wallet,
        "issuer_bank": issuer, "tag_status": tag_status,
    }


def display_profile(profile):
    """Print a beautiful formatted profile to the terminal."""
    status_tag = "🟢 EXISTING RECORD" if profile["status"] == "EXISTING" else "🟡 NEW PROXY GENERATED"
    
    print("\n" + "=" * 65)
    print(f"  {status_tag}")
    print("=" * 65)
    print(f"  📋 LICENSE PLATE:  {profile['plate']}")
    print("-" * 65)
    print(f"  👤 OWNER PROFILE")
    print(f"     Name:           {profile['owner_name']}")
    print(f"     Gender:         {profile.get('gender', 'N/A')}")
    print(f"     DOB:            {profile.get('dob', 'N/A')}")
    print(f"     City:           {profile.get('city', 'N/A')}, {profile.get('state', 'N/A')}")
    print(f"     Phone:          {profile.get('phone', 'N/A')}")
    print(f"     PAN:            {profile.get('pan', 'N/A')}")
    print(f"     CIBIL Score:    {profile.get('cibil', 'N/A')}")
    print("-" * 65)
    print(f"  🚗 VEHICLE (VAHAN)")
    print(f"     Class:          {profile['vehicle_class']}")
    print(f"     Vehicle:        {profile['make']} {profile['model']}")
    print(f"     Color:          {profile.get('color', 'N/A')}")
    print(f"     Fuel:           {profile.get('fuel', 'N/A')}")
    print(f"     Invoice Price:  ₹{profile['invoice_price']:,.0f}")
    print(f"     Reg. Date:      {profile.get('reg_date', 'N/A')}")
    print(f"     RTO:            {profile.get('rto', 'N/A')}")
    print(f"     RC Status:      {profile.get('rc_status', 'N/A')}")
    print(f"     Insurance:      {profile.get('insurance_co', 'N/A')}")
    print(f"     Loan:           {profile.get('hypothecation', 'N/A')} ({profile.get('financer', 'N/A')})")
    print("-" * 65)
    print(f"  💳 FASTAG")
    print(f"     FASTag ID:      {profile.get('fastag_id', 'N/A')}")
    print(f"     Wallet Balance: ₹{profile.get('wallet_balance', 0):,.2f}")
    print(f"     Issuer Bank:    {profile.get('issuer_bank', 'N/A')}")
    print(f"     Tag Status:     {profile.get('tag_status', 'N/A')}")
    print("=" * 65)
    
    # Wealth Multiplier Calculation
    price = profile.get('invoice_price', 500000)
    multiplier = max(1.0, min(10.0, price / 500000))
    base_fine = 5000
    final_fine = round(base_fine * multiplier, 2)
    print(f"\n  ⚖️  WEALTH MULTIPLIER PREVIEW")
    print(f"     Vehicle Value:      ₹{price:,.0f}")
    print(f"     Multiplier:         {multiplier:.2f}x")
    print(f"     Sample Fine (₹5k):  ₹{final_fine:,.0f}")
    print("=" * 65 + "\n")


def process_image(img_path, vehicle_model, plate_model, reader, conn):
    """Run Two-Stage detection on a single image."""
    img = cv2.imread(img_path)
    if img is None:
        print(f"  ⚠️  Could not read: {img_path}")
        return

    print(f"\n🔍 Scanning: {os.path.basename(img_path)}")

    # Stage 1: Find vehicles
    v_results = vehicle_model.predict(img, verbose=False)
    found_any = False

    for v_box in v_results[0].boxes:
        v_cls = int(v_box.cls[0])
        if v_cls not in [1, 2, 3, 5, 7]:
            continue

        x1, y1, x2, y2 = map(int, v_box.xyxy[0])
        vehicle_crop = img[y1:y2, x1:x2]
        if vehicle_crop.shape[0] < 20 or vehicle_crop.shape[1] < 20:
            continue

        # Stage 2: Find plates inside vehicle
        p_results = plate_model.predict(vehicle_crop, verbose=False)

        for p_box in p_results[0].boxes:
            px1, py1, px2, py2 = map(int, p_box.xyxy[0])
            plate_crop = vehicle_crop[
                max(0, py1 - 5):min(vehicle_crop.shape[0], py2 + 5),
                max(0, px1 - 5):min(vehicle_crop.shape[1], px2 + 5)
            ]
            if plate_crop.shape[0] == 0 or plate_crop.shape[1] == 0:
                continue

            # Stage 3: OCR
            ocr_results = reader.readtext(plate_crop)
            raw_text = "".join([res[1] for res in ocr_results])
            clean_plate = re.sub(r'[^A-Z0-9]', '', raw_text.upper())

            if len(clean_plate) < 6:
                continue

            match = PATTERN_INDIA.search(clean_plate)
            if not match:
                continue

            state_code = match.group(1)
            profile = lookup_or_create_profile(clean_plate, state_code, v_cls, conn)
            display_profile(profile)
            found_any = True

    if not found_any:
        print("  ❌ No valid plates detected in this image.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python live_detect.py <image_or_folder>")
        print("  Example: python live_detect.py test/car1.jpg")
        print("  Example: python live_detect.py test/")
        sys.exit(1)

    target = sys.argv[1]
    vehicle_model, plate_model, reader = load_models()

    # Ensure DB exists and schema is ready
    conn = sqlite3.connect(DB_PATH)
    create_database_schema(conn)

    if os.path.isdir(target):
        # Process all images in folder
        import glob
        images = glob.glob(os.path.join(target, "*.jpg")) + \
                 glob.glob(os.path.join(target, "*.jpeg")) + \
                 glob.glob(os.path.join(target, "*.png"))
        print(f"\n📁 Processing {len(images)} images from: {target}\n")
        for img_path in images:
            process_image(img_path, vehicle_model, plate_model, reader, conn)
    elif os.path.isfile(target):
        process_image(target, vehicle_model, plate_model, reader, conn)
    else:
        print(f"ERROR: '{target}' is not a valid file or directory.")

    conn.close()
    print("\n✅ Done! All new plates have been auto-added to arg_master_database.sqlite")


if __name__ == "__main__":
    main()
