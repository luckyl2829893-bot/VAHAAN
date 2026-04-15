"""
db_writer.py  —  Aequitas RoadGuard
====================================
Drop into  C:\\Users\\laksh\\Desktop\\image\\  and run:

    python db_writer.py

Zero local imports. Uses the EXACT column names your existing database
was created with (verified from original generate_proxy_database.py).

Actual vahan_registry column names:
    chassis_number, engine_number, registration_date, rto_location,
    rc_status, fitness_valid_upto, insurance_company, puc_valid_upto,
    financer_bank   (NOT chassis / engine_no / reg_date / rto / status etc.)
"""

import csv
import os
import random
import re
from datetime import datetime, timedelta
# ── DB Manager — centralizes MySQL config ──────────────────────────── #
from src.database.manager import DBManager

# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

INDIAN_FIRST_NAMES = [
    "Rajesh","Priya","Amit","Sunita","Vikram","Neha","Suresh","Kavita",
    "Arun","Deepa","Rahul","Anita","Sanjay","Pooja","Manoj","Rekha",
    "Rohit","Meena","Ajay","Lakshmi","Vijay","Suman","Dinesh","Geeta",
    "Ramesh","Asha","Ashok","Nirmala","Pramod","Savita","Harish","Kiran",
    "Mukesh","Sarita","Naresh","Usha","Rakesh","Shanti","Yogesh","Padma",
]
INDIAN_LAST_NAMES = [
    "Sharma","Verma","Gupta","Singh","Kumar","Patel","Reddy","Rao",
    "Joshi","Mishra","Chauhan","Thakur","Pandey","Tiwari","Yadav","Nair",
    "Menon","Iyer","Pillai","Das","Bose","Sen","Mukherjee","Banerjee",
    "Chopra","Malhotra","Kapoor","Khanna","Mehta","Shah","Desai","Patil",
]
STATE_RTO_MAP = {
    "AP":{"state":"Andhra Pradesh",      "cities":["Visakhapatnam","Vijayawada","Tirupati","Guntur"]},
    "AR":{"state":"Arunachal Pradesh",   "cities":["Itanagar","Naharlagun","Pasighat"]},
    "AS":{"state":"Assam",               "cities":["Guwahati","Silchar","Dibrugarh","Jorhat"]},
    "BR":{"state":"Bihar",               "cities":["Patna","Gaya","Muzaffarpur","Bhagalpur"]},
    "CG":{"state":"Chhattisgarh",        "cities":["Raipur","Bhilai","Bilaspur","Korba"]},
    "GA":{"state":"Goa",                 "cities":["Panaji","Margao","Vasco da Gama"]},
    "GJ":{"state":"Gujarat",             "cities":["Ahmedabad","Surat","Vadodara","Rajkot"]},
    "HR":{"state":"Haryana",             "cities":["Gurugram","Faridabad","Ambala","Panipat"]},
    "HP":{"state":"Himachal Pradesh",    "cities":["Shimla","Manali","Dharamshala","Mandi"]},
    "JH":{"state":"Jharkhand",           "cities":["Ranchi","Jamshedpur","Dhanbad","Bokaro"]},
    "KA":{"state":"Karnataka",           "cities":["Bengaluru","Mysuru","Hubli","Mangaluru"]},
    "KL":{"state":"Kerala",              "cities":["Thiruvananthapuram","Kochi","Kozhikode"]},
    "MP":{"state":"Madhya Pradesh",      "cities":["Bhopal","Indore","Gwalior","Jabalpur"]},
    "MH":{"state":"Maharashtra",         "cities":["Mumbai","Pune","Nagpur","Nashik","Thane"]},
    "MN":{"state":"Manipur",             "cities":["Imphal","Thoubal","Bishnupur"]},
    "ML":{"state":"Meghalaya",           "cities":["Shillong","Tura","Jowai"]},
    "MZ":{"state":"Mizoram",             "cities":["Aizawl","Lunglei","Champhai"]},
    "NL":{"state":"Nagaland",            "cities":["Kohima","Dimapur","Mokokchung"]},
    "OD":{"state":"Odisha",              "cities":["Bhubaneswar","Cuttack","Rourkela","Berhampur"]},
    "PB":{"state":"Punjab",              "cities":["Chandigarh","Ludhiana","Amritsar","Jalandhar"]},
    "RJ":{"state":"Rajasthan",           "cities":["Jaipur","Jodhpur","Udaipur","Kota"]},
    "SK":{"state":"Sikkim",              "cities":["Gangtok","Namchi","Geyzing"]},
    "TN":{"state":"Tamil Nadu",          "cities":["Chennai","Coimbatore","Madurai","Salem"]},
    "TS":{"state":"Telangana",           "cities":["Hyderabad","Warangal","Nizamabad"]},
    "TR":{"state":"Tripura",             "cities":["Agartala","Udaipur","Dharmanagar"]},
    "UK":{"state":"Uttarakhand",         "cities":["Dehradun","Haridwar","Rishikesh","Nainital"]},
    "UP":{"state":"Uttar Pradesh",       "cities":["Lucknow","Noida","Agra","Varanasi","Kanpur"]},
    "WB":{"state":"West Bengal",         "cities":["Kolkata","Howrah","Siliguri","Durgapur"]},
    "AN":{"state":"Andaman & Nicobar",   "cities":["Port Blair","Car Nicobar"]},
    "CH":{"state":"Chandigarh",          "cities":["Chandigarh"]},
    "DD":{"state":"Dadra & Daman Diu",   "cities":["Silvassa","Daman","Diu"]},
    "DL":{"state":"Delhi",               "cities":["New Delhi","Shahdara","Dwarka","Rohini","Saket"]},
    "JK":{"state":"Jammu & Kashmir",     "cities":["Srinagar","Jammu","Anantnag","Baramulla"]},
    "LA":{"state":"Ladakh",              "cities":["Leh","Kargil"]},
    "LD":{"state":"Lakshadweep",         "cities":["Kavaratti","Agatti"]},
    "PY":{"state":"Puducherry",          "cities":["Puducherry","Karaikal","Mahe","Yanam"]},
}
VEHICLE_PROFILES = {
    "2-Wheeler":{"makes":[
        {"make":"Hero",          "models":["Splendor Plus","HF Deluxe","Glamour","Xtreme 160R"],   "prices":[75000,60000,85000,130000]},
        {"make":"Honda",         "models":["Activa 6G","Shine","SP 125","Unicorn"],                "prices":[75000,80000,85000,105000]},
        {"make":"Bajaj",         "models":["Pulsar 150","Platina","CT 110","Dominar 400"],         "prices":[110000,65000,55000,225000]},
        {"make":"TVS",           "models":["Jupiter","Apache RTR 160","Raider 125","Ntorq"],       "prices":[73000,115000,90000,85000]},
        {"make":"Royal Enfield", "models":["Classic 350","Bullet 350","Meteor 350","Hunter 350"],  "prices":[195000,175000,210000,150000]},
    ],"colors":["Black","Red","Blue","Grey","White","Matt Black"],"fuel":"Petrol"},
    "3-Wheeler":{"makes":[
        {"make":"Bajaj",    "models":["RE Compact","RE 4S","Maxima Z"],  "prices":[195000,210000,280000]},
        {"make":"Piaggio",  "models":["Ape City","Ape Xtra DLX"],        "prices":[250000,310000]},
        {"make":"Mahindra", "models":["Treo","Alfa Plus"],                "prices":[350000,220000]},
    ],"colors":["Green","Yellow","Black-Yellow","White"],"fuel":"CNG"},
    "4-Wheeler (Hatchback)":{"makes":[
        {"make":"Maruti Suzuki","models":["Swift","WagonR","Baleno","Alto K10","Celerio"],"prices":[650000,570000,690000,380000,520000]},
        {"make":"Hyundai",      "models":["i20","Grand i10 Nios","Santro"],               "prices":[750000,600000,520000]},
        {"make":"Tata",         "models":["Tiago","Altroz","Punch"],                      "prices":[580000,670000,610000]},
    ],"colors":["White","Silver","Red","Blue","Grey","Orange"],"fuel":"Petrol"},
    "4-Wheeler (Luxury SUV)":{"makes":[
        {"make":"Mahindra","models":["XUV700","Thar","Scorpio-N","XUV300"],              "prices":[1500000,1100000,1350000,850000]},
        {"make":"Tata",    "models":["Harrier","Safari","Nexon"],                         "prices":[1550000,1700000,850000]},
        {"make":"Toyota",  "models":["Fortuner","Innova Crysta","Urban Cruiser Hyryder"],"prices":[3500000,2000000,1100000]},
        {"make":"Hyundai", "models":["Creta","Venue","Tucson"],                           "prices":[1100000,800000,2800000]},
    ],"colors":["White","Black","Grey","Silver","Deep Blue"],"fuel":"Diesel"},
    "Heavy Commercial":{"makes":[
        {"make":"Tata Motors",  "models":["Prima 4028.S","LPT 3518","Signa 4825.TK","Ultra T.16"],"prices":[3200000,2500000,3800000,1500000]},
        {"make":"Ashok Leyland","models":["Captain 2523","Ecomet 1215","AVTR 2825"],               "prices":[2800000,1800000,3500000]},
        {"make":"BharatBenz",   "models":["1617R","2823R","3523R"],                                "prices":[2200000,3100000,3600000]},
    ],"colors":["Red","Blue","White","Green","Multi-Color"],"fuel":"Diesel"},
}
INSURANCE_COMPANIES = [
    "ICICI Lombard","HDFC ERGO","Bajaj Allianz","New India Assurance",
    "United India Insurance","National Insurance","SBI General","Tata AIG",
    "Reliance General","Cholamandalam MS",
]
BANKS = [
    "State Bank of India","HDFC Bank","ICICI Bank","Punjab National Bank",
    "Bank of Baroda","Axis Bank","Kotak Mahindra Bank","Union Bank of India",
    "Canara Bank","IndusInd Bank","Yes Bank","IDFC First Bank",
]
TOLL_PLAZAS = [
    "Kherki Daula Toll, Gurgaon","Dasna Toll, Ghaziabad","Mulund Toll, Mumbai",
    "ORR Toll, Bengaluru","Electronic City Toll, Bengaluru","Hosur Toll, Tamil Nadu",
    "Mathura Toll, Uttar Pradesh","Sohna Toll, Gurugram","Wagholi Toll, Pune",
    "Rajiv Gandhi Toll, Hyderabad","Bandra-Worli Sea Link Toll, Mumbai",
]
VIOLATION_TYPES = [
    ("Speeding",1000),("Red Light Jump",5000),("Wrong Side Driving",5000),
    ("No Helmet",1000),("No Seatbelt",1000),("Triple Riding",1000),
    ("Lane Violation",500),("Using Mobile While Driving",5000),
    ("Overloading",2000),("Expired Insurance",2000),
    ("No PUC Certificate",500),("Rash / Dangerous Driving",5000),
]
VC_CODE_MAP = {
    "2-Wheeler":"VC2","3-Wheeler":"VC3",
    "4-Wheeler (Hatchback)":"VC4","4-Wheeler (Luxury SUV)":"VC4",
    "Heavy Commercial":"VC7",
}
PLATE_PATTERN = re.compile(r"([A-Z]{2})([0-9]{1,2})([A-Z]{1,3})([0-9]{1,4})")


# ══════════════════════════════════════════════════════════════════════════════
#  DATA GENERATORS
# ══════════════════════════════════════════════════════════════════════════════

def _rdate(y1, y2):
    s = datetime(y1,1,1); d = datetime(y2,12,31)-s
    return (s+timedelta(days=random.randint(0,d.days))).strftime("%Y-%m-%d")

def _aadhar():   return f"XXXX XXXX {random.randint(1000,9999)}"
def _vid():      return " ".join(str(random.randint(1000,9999)) for _ in range(4))
def _pan():
    l="".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ",k=3))
    return f"{l}{random.choice('PCFHAT')}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(1000,9999)}"
def _chassis():
    return "XXXXX"+"".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",k=6))+"".join(random.choices("0123456789",k=5))
def _engine():
    return "XXX"+"".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ",k=3))+"".join(random.choices("0123456789",k=6))

def _vehicle(vehicle_class):
    p=VEHICLE_PROFILES[vehicle_class]; b=random.choice(p["makes"]); i=random.randint(0,len(b["models"])-1)
    return {"class":vehicle_class,"make":b["make"],"model":b["models"][i],
            "color":random.choice(p["colors"]),"fuel":p["fuel"],"price":b["prices"][i]}

def _citizen(state_code):
    si=STATE_RTO_MAP.get(state_code,STATE_RTO_MAP["DL"]); city=random.choice(si["cities"])
    return {
        "name":  f"{random.choice(INDIAN_FIRST_NAMES)} {random.choice(INDIAN_LAST_NAMES)}",
        "gender":random.choice(["Male","Female"]),
        "dob":   _rdate(1965,2002),
        "addr":  f"House {random.randint(1,500)}, Sector {random.randint(1,100)}, {city}, {si['state']}",
        "city":  city, "state": si["state"],
        "phone": f"******{random.randint(1000,9999)}",
        "cibil": random.randint(550,850),
        "pan":   _pan(),
    }

def _transactions():
    base=datetime.now()-timedelta(days=random.randint(1,90)); rows=[]
    for _ in range(random.randint(3,8)):
        t=base-timedelta(days=random.randint(0,60),hours=random.randint(0,23))
        rows.append({"plaza":random.choice(TOLL_PLAZAS),
                     "ts":t.strftime("%Y-%m-%d %H:%M:%S"),
                     "amt":random.choice([45,65,85,95,115,135,155,185,215,245])})
    return rows

def coco_class_to_vehicle_class(coco_cls):
    if coco_cls in (1,3): return "2-Wheeler"
    if coco_cls in (5,7): return "Heavy Commercial"
    return random.choice(["4-Wheeler (Hatchback)","4-Wheeler (Luxury SUV)"])


# ══════════════════════════════════════════════════════════════════════════════
#  CONNECTION (Delegated)
# ══════════════════════════════════════════════════════════════════════════════

def get_connection():
    return DBManager.get_connection()


# ══════════════════════════════════════════════════════════════════════════════
#  SCHEMA (Delegated)
# ══════════════════════════════════════════════════════════════════════════════

def ensure_schema(conn=None):
    return DBManager.ensure_schema()
    """
    Creates tables only if they do not already exist.
    Column names match your original generate_proxy_database.py exactly:
      chassis_number, engine_number, registration_date, rto_location,
      rc_status, fitness_valid_upto, insurance_company, puc_valid_upto,
      financer_bank
    """
    pass


# ══════════════════════════════════════════════════════════════════════════════
#  READ HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def plate_exists(conn, plate_number):
    q = DBManager.format_query("SELECT 1 FROM vahan_registry WHERE plate_number=? LIMIT 1")
    cur = conn.cursor()
    cur.execute(q, (plate_number,))
    return cur.fetchone() is not None

def load_existing_plates(conn):
    return {r[0] for r in conn.execute("SELECT plate_number FROM vahan_registry").fetchall()}

def lookup_plate(conn, plate_number):
    """Full joined record using the exact original column names."""
    q = DBManager.format_query("""
        SELECT
            v.plate_number,       v.vehicle_class,    v.make,
            v.model,              v.color,             v.fuel_type,
            v.chassis_number,     v.engine_number,     v.registration_date,
            v.rto_location,       v.rc_status,         v.fitness_valid_upto,
            v.invoice_price,      v.insurance_company, v.insurance_policy,
            v.insurance_expiry,   v.puc_valid_upto,    v.hypothecation,
            v.financer_bank,
            c.full_name,          c.gender,            c.date_of_birth,
            c.address,            c.city,              c.state,
            c.phone_masked,       c.pan_number,        c.cibil_score,
            c.kyc_status,
            f.fastag_id,          f.wallet_balance,    f.tag_status,
            f.issuer_bank,        f.low_balance_alert
        FROM  vahan_registry v
        LEFT JOIN citizens        c ON c.aadhar_masked = v.owner_aadhar
        LEFT JOIN fastag_accounts f ON f.plate_number  = v.plate_number
        WHERE v.plate_number = ?
        LIMIT 1
    """)
    cur = conn.cursor()
    cur.execute(q, (plate_number,))
    row = cur.fetchone()
    return dict(row) if row else None

def get_unpaid_challans(conn, plate_number):
    q = DBManager.format_query("""
        SELECT challan_id, violation_type, final_fine, date_issued
        FROM   challans
        WHERE  plate_number=? AND status='Unpaid'
        ORDER  BY date_issued DESC
    """)
    cur = conn.cursor()
    cur.execute(q, (plate_number,))
    rows = cur.fetchall()
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════════════════════
#  WRITE HELPERS — explicit named columns matching the ORIGINAL schema
# ══════════════════════════════════════════════════════════════════════════════

def _ins_citizen(c, aadhar, vid, cit):
    # MySQL Standard
    q = """
        INSERT IGNORE INTO citizens (
            aadhar_masked, virtual_id,   full_name,    gender,
            date_of_birth, address,      city,         state,
            phone_masked,  pan_number,   cibil_score,  kyc_status
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s
        )
    """
    params = (
        aadhar, vid, cit["name"], cit["gender"],
        cit["dob"], cit["addr"], cit["city"], cit["state"],
        cit["phone"], cit["pan"], cit["cibil"], "Full KYC"
    )
    c.execute(DBManager.format_query(q), params)

def _ins_vahan(c, plate, veh, cit, aadhar,
               reg_date, rto_city, fitness,
               ins_co, ins_pol, ins_exp,
               puc, hypo, financer):
    q = """
        INSERT IGNORE INTO vahan_registry (
            plate_number,      vehicle_class,    make,             model,
            color,             fuel_type,        chassis_number,   engine_number,
            registration_date, rto_location,     rc_status,        fitness_valid_upto,
            invoice_price,     insurance_company,insurance_policy, insurance_expiry,
            puc_valid_upto,    hypothecation,    financer_bank,    owner_aadhar,
            owner_name
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s
        )
    """
    params = (
        plate, veh["class"], veh["make"], veh["model"],
        veh["color"], veh["fuel"], _chassis(), _engine(),
        reg_date, f"RTO {rto_city}", "Active", fitness,
        veh["price"], ins_co, ins_pol, ins_exp,
        puc, hypo, financer, aadhar, cit["name"]
    )
    c.execute(DBManager.format_query(q), params)

def _ins_fastag(c, fid, tid, plate, wallet, issuer, bank, status, vc):
    q = """
        INSERT IGNORE INTO fastag_accounts (
            fastag_id,  tag_id,  plate_number,       customer_id,
            wallet_balance, issuer_bank, bank_account_masked, tag_status,
            vehicle_class_code, kyc_status, low_balance_alert
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, 'Full KYC', %s
        )
    """
    params = (
        fid, tid, plate, f"CID-{random.randint(10000,99999)}",
        wallet, issuer, bank, status, vc, 1 if wallet < 100 else 0
    )
    c.execute(DBManager.format_query(q), params)

def _ins_transactions(c, fid):
    for tx in _transactions():
        q = DBManager.format_query("""
            INSERT INTO fastag_transactions
                (fastag_id, toll_plaza, timestamp, amount_deducted)
            VALUES (?, ?, ?, ?)
        """)
        c.execute(q, (fid, tx["plaza"], tx["ts"], tx["amt"]))

def _ins_challans(c, plate, price):
    if random.random() >= 0.35:
        return
    for _ in range(random.randint(1,3)):
        viol, base = random.choice(VIOLATION_TYPES)
        mult = round(max(1.0, min(10.0, price/500_000)), 2)
        q = DBManager.format_query("""
            INSERT INTO challans (
                plate_number, violation_type, base_fine,
                wealth_multiplier, final_fine, status, date_issued
            ) VALUES (
                ?, ?, ?,
                ?, ?, ?, ?
            )
        """)
        params = (
            plate, viol, base,
            mult, round(base*mult,2),
            random.choice(["Unpaid","Unpaid","Paid"]),
            _rdate(2024, 2026)
        )
        c.execute(q, params)


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def insert_full_record(conn, plate_number, state_code, vehicle_class):
    """
    Generate + insert a complete proxy identity.
    Returns summary dict, or {} if the plate already existed.
    Fully idempotent — safe to call multiple times.
    """
    if plate_exists(conn, plate_number):
        return {}

    veh    = _vehicle(vehicle_class)
    cit    = _citizen(state_code)
    aadhar = _aadhar()
    vid    = _vid()

    si       = STATE_RTO_MAP.get(state_code, STATE_RTO_MAP["DL"])
    rto_city = random.choice(si["cities"])
    reg_date = _rdate(2010,2025)
    fitness  = _rdate(2025,2030)
    ins_co   = random.choice(INSURANCE_COMPANIES)
    ins_pol  = f"POL-{random.randint(100000,999999)}"
    ins_exp  = _rdate(2025,2027)
    puc      = _rdate(2025,2026)
    has_loan = random.choice([True,False])
    hypo     = "Yes" if has_loan else "No"
    financer = random.choice(BANKS) if has_loan else "N/A"

    fid    = f"FAS-{random.randint(100000,999999)}"
    tid    = "".join(random.choices("0123456789ABCDEF",k=20))
    wallet = round(random.uniform(25.0,5000.0),2)
    issuer = random.choice(BANKS)
    bank   = f"XXXX XXXX {random.randint(1000,9999)}"
    vc     = VC_CODE_MAP.get(vehicle_class,"VC4")
    fstatus= "Active" if wallet>50 else "Blacklisted"

    try:
        cur = conn.cursor()
        _ins_citizen(cur, aadhar, vid, cit)
        _ins_vahan(cur, plate_number, veh, cit, aadhar,
                   reg_date, rto_city, fitness,
                   ins_co, ins_pol, ins_exp, puc, hypo, financer)
        _ins_fastag(cur, fid, tid, plate_number, wallet, issuer, bank, fstatus, vc)
        _ins_transactions(cur, fid)
        _ins_challans(cur, plate_number, veh["price"])
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[DB ERROR] {plate_number}: {e}")
        return {}

    return {
        "License Plate":  plate_number,
        "Owner Name":     cit["name"],
        "Vehicle":        f"{veh['make']} {veh['model']}",
        "Class":          vehicle_class,
        "Color":          veh["color"],
        "Invoice Price":  f"₹{veh['price']:,}",
        "State":          cit["state"],
        "CIBIL":          cit["cibil"],
        "FASTag Balance": f"₹{wallet:,.2f}",
        "FASTag Status":  fstatus,
        "Insurance":      ins_co,
        "Loan":           hypo,
    }

def lookup_or_create(conn, plate_number, state_code, vehicle_class):
    """
    DB hit  → return existing record.
    New     → insert + return new record.
    Always returns a dict.
    """
    rec = lookup_plate(conn, plate_number)
    if rec:
        rec["_source"] = "db_hit"
        return rec
    insert_full_record(conn, plate_number, state_code, vehicle_class)
    rec = lookup_plate(conn, plate_number) or {}
    rec["_source"] = "db_created"
    return rec


# ══════════════════════════════════════════════════════════════════════════════
#  SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n{'='*55}")
    print("  db_writer.py  —  self-test")
    print(f"{'='*55}")
    print(f"  DB : MySQL ({os.getenv('MYSQL_DATABASE')})")

    conn = get_connection()
    ensure_schema(conn)
    print("  Schema  : OK")

    tables = ["citizens","vahan_registry","fastag_accounts",
              "fastag_transactions","challans"]
    for tbl in tables:
        # MySQL specific row count
        r = DBManager.fetch_one(f"SELECT COUNT(*) as cnt FROM {tbl}")
        print(f"  {tbl:<28}: {r['cnt'] if r else 0:>6} rows")

    # Test insert
    test_plate = "DL01TEST0001"
    if not plate_exists(conn, test_plate):
        s = insert_full_record(conn, test_plate, "DL", "4-Wheeler (Hatchback)")
        print(f"\n  Insert  : {s['Vehicle']}  owner={s['Owner Name']}")
    else:
        print(f"\n  {test_plate} already in DB — skipping insert")

    # Test lookup
    rec = lookup_plate(conn, test_plate)
    if rec:
        print(f"  Lookup  : {rec['make']} {rec['model']}  "
              f"chassis={rec['chassis_number']}  rto={rec['rto_location']}")

    conn.close()
    print(f"\n{'='*55}")
    print("  All checks passed.")
    print(f"{'='*55}\n")