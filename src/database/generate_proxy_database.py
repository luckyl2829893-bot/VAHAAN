import random
import re
import string
from datetime import datetime, timedelta
import os

# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

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
}

VEHICLE_PROFILES = {
    "2-Wheeler":{"makes":[
        {"make":"Hero",          "models":["Splendor Plus","HF Deluxe","Glamour","Xtreme 160R"],   "prices":[75000,60000,85000,130000]},
        {"make":"Honda",         "models":["Activa 6G","Shine","SP 125","Unicorn"],                "prices":[75000,80000,85000,105000]},
    ],"colors":["Black","Red","Blue","Grey","White"],"fuel":"Petrol"},
    "4-Wheeler (Hatchback)":{"makes":[
        {"make":"Maruti Suzuki","models":["Swift","WagonR","Baleno","Alto K10","Celerio"],"prices":[650000,570000,690000,380000,520000]},
        {"make":"Hyundai",      "models":["i20","Grand i10 Nios","Santro"],               "prices":[750000,600000,520000]},
    ],"colors":["White","Silver","Red","Blue","Grey"],"fuel":"Petrol"},
    "4-Wheeler (Luxury SUV)":{"makes":[
        {"make":"Mahindra","models":["XUV700","Thar","Scorpio-N","XUV300"],              "prices":[1500000,1100000,1350000,850000]},
        {"make":"Toyota",  "models":["Fortuner","Innova Crysta","Urban Cruiser Hyryder"],"prices":[3500000,2000000,1100000]},
    ],"colors":["White","Black","Grey","Silver","Deep Blue"],"fuel":"Diesel"},
    "Heavy Commercial":{"makes":[
        {"make":"Tata Motors",  "models":["Prima 4028.S","LPT 3518","Signa 4825.TK","Ultra T.16"],"prices":[3200000,2500000,3800000,1500000]},
        {"make":"BharatBenz",   "models":["1617R","2823R","3523R"],                                "prices":[2200000,3100000,3600000]},
    ],"colors":["Red","Blue","White","Green"],"fuel":"Diesel"},
}

INSURANCE_COMPANIES = ["ICICI Lombard", "HDFC ERGO", "Bajaj Allianz", "New India Assurance", "SBI General", "Tata AIG"]
BANKS = ["State Bank of India", "HDFC Bank", "ICICI Bank", "Axis Bank", "Kotak Mahindra Bank"]

# ══════════════════════════════════════════════════════════════════════════════
#  GENERATORS
# ══════════════════════════════════════════════════════════════════════════════

def random_date(y1, y2):
    s = datetime(y1, 1, 1)
    d = datetime(y2, 12, 31) - s
    return (s + timedelta(days=random.randint(0, d.days))).strftime("%Y-%m-%d")

def generate_aadhar():
    return f"XXXX XXXX {random.randint(1000, 9999)}"

def generate_virtual_id():
    return " ".join(str(random.randint(1000, 9999)) for _ in range(4))

def generate_chassis():
    return "XXXXX" + "".join(random.choices(string.ascii_uppercase + string.digits, k=11))

def generate_engine_no():
    return "XXX" + "".join(random.choices(string.ascii_uppercase, k=3)) + "".join(random.choices(string.digits, k=6))

def generate_vehicle_details(vehicle_class):
    p = VEHICLE_PROFILES.get(vehicle_class, VEHICLE_PROFILES["4-Wheeler (Hatchback)"])
    b = random.choice(p["makes"])
    i = random.randint(0, len(b["models"]) - 1)
    return {
        "make": b["make"],
        "model": b["models"][i],
        "color": random.choice(p["colors"]),
        "fuel_type": p["fuel"],
        "invoice_price": b["prices"][i]
    }

def generate_citizen_profile(state_code):
    si = STATE_RTO_MAP.get(state_code, STATE_RTO_MAP.get("DL", {"state": "Delhi", "cities": ["New Delhi"]}))
    city = random.choice(si["cities"])
    first_names = ["Rajesh", "Priya", "Amit", "Sunita", "Vikram", "Neha"]
    last_names = ["Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel"]
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    return {
        "name": name,
        "gender": random.choice(["Male", "Female"]),
        "dob": random_date(1965, 2002),
        "address": f"House {random.randint(1, 500)}, Sector {random.randint(1, 100)}, {city}, {si['state']}",
        "city": city,
        "state": si["state"],
        "phone_masked": f"******{random.randint(1000, 9999)}",
        "pan": f"{''.join(random.choices(string.ascii_uppercase, k=5))}{random.randint(1000, 9999)}{random.choice(string.ascii_uppercase)}",
        "cibil_score": random.randint(550, 850)
    }

def get_vehicle_class_from_coco(coco_cls):
    return {1: "2-Wheeler", 2: "4-Wheeler (Hatchback)", 3: "2-Wheeler", 5: "Heavy Commercial", 7: "Heavy Commercial"}.get(coco_cls, "4-Wheeler (Hatchback)")

def create_database_schema():
    from arg_db_manager import DBManager
    return DBManager.ensure_schema()
