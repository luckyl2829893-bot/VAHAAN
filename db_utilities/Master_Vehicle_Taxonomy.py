import pandas as pd

def generate_master_taxonomy():
    print("🚀 Generating Master Indian Vehicle Taxonomy...")
    
    data = [
        # --- CARS (High Volume) ---
        {"type": "PV", "brand": "Maruti Suzuki", "model": "Swift"},
        {"type": "PV", "brand": "Maruti Suzuki", "model": "Baleno"},
        {"type": "PV", "brand": "Tata", "model": "Nexon"},
        {"type": "PV", "brand": "Hyundai", "model": "Creta"},
        # --- TRUCKS (HCV) ---
        {"type": "HCV", "brand": "Tata", "model": "Signa 5530.S"},
        {"type": "HCV", "brand": "Ashok Leyland", "model": "Ecomet Star"},
        {"type": "HCV", "brand": "BharatBenz", "model": "3523R"},
        # --- RICKSHAWS (3W) ---
        {"type": "3W", "brand": "Bajaj", "model": "RE E-TEC"},
        {"type": "3W", "brand": "Piaggio", "model": "Ape E-City"},
        {"type": "3W", "brand": "Mahindra", "model": "Treo"},
        # --- BIKES (2W) ---
        {"type": "2W", "brand": "Hero", "model": "Splendor Plus"},
        {"type": "2W", "brand": "Honda", "model": "Activa 6G"},
        {"type": "2W", "brand": "Royal Enfield", "model": "Classic 350"}
    ]

    df = pd.DataFrame(data)
    df.to_csv("arg_master_vehicles.csv", index=False)
    print("✅ Success! 'arg_master_vehicles.csv' created.")

if __name__ == "__main__":
    generate_master_taxonomy()