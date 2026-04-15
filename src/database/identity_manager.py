import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.database.manager import DBManager

def setup_identity_system():
    # 1. Create Identities Table
    create_identities_query = """
    CREATE TABLE IF NOT EXISTS official_identities (
        identity_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        full_name VARCHAR(255),
        id_type VARCHAR(50), -- 'Aadhaar', 'Police Badge', 'Voter ID'
        id_number VARCHAR(50) UNIQUE,
        id_card_image TEXT, -- Path to generated card
        clearance_level INT, -- 1 to 5
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """
    DBManager.execute(create_identities_query)
    print("Identity management system initialized.")

def register_admin_slasher():
    # 1. Ensure user exists
    # We use a dummy encoding for now until image is processed
    check_query = "SELECT user_id FROM users WHERE contact_no = '9999999999'"
    user = DBManager.fetch_one(check_query)
    
    if not user:
        insert_user = """
        INSERT INTO users (full_name, contact_no, professional_id, role)
        VALUES (%s, %s, %s, %s)
        """
        DBManager.execute(insert_user, ("Slasher", "9999999999", "ARG-SENTINEL-001", "Sentinel"))
        user = DBManager.fetch_one(check_query)
    
    user_id = user['user_id']
    
    # 2. Add Official Identity (Aadhaar)
    insert_id = """
    INSERT INTO official_identities (user_id, full_name, id_type, id_number, clearance_level)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE clearance_level=5
    """
    DBManager.execute(insert_id, (user_id, "Slasher", "Aadhaar", "4920 5831 9274 005", 5))
    print("Admin 'Slasher' registered with Level 5 clearance.")

if __name__ == "__main__":
    setup_identity_system()
    register_admin_slasher()
