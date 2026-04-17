"""
manager.py  —  VAHAAN Database Manager (MySQL Primary)
======================================================
This module provides a unified interface for MySQL.
It handles connection pooling and schema consistency.
"""

import os
import sys
import mysql.connector
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path to allow absolute imports
root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

# Load configuration from .env
load_dotenv(dotenv_path=root_path / ".env")

# MySQL credentials
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "arg_VAHAAN")


class DBManager:
    """Unified MySQL Database Manager for VAHAAN."""

    @staticmethod
    def get_connection():
        """Returns a MySQL connection object."""
        try:
            conn = mysql.connector.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE
            )
            return conn
        except mysql.connector.Error as err:
            print(f"[DB ERROR] MySQL Connection failed: {err}")
            return None

    @staticmethod
    def execute(query, params=(), commit=True):
        """Standard wrapper for common execute-commit cycle."""
        conn = DBManager.get_connection()
        if not conn:
            return None
        
        try:
            # We use dictionary=True for easier record handling in Python
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            if commit:
                conn.commit()
            return cursor
        except Exception as e:
            print(f"[DB ERROR] Execute failed: {e}")
            if commit:
                conn.rollback()
            return None

    @staticmethod
    def fetch_one(query, params=()):
        """Fetch a single record as a dictionary."""
        conn = DBManager.get_connection()
        if not conn:
            return None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def fetch_all(query, params=()):
        """Fetch all records as a list of dictionaries."""
        conn = DBManager.get_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def ensure_schema():
        """Creates the database and tables using MySQL syntax."""
        try:
            # First, connect without a database to create it
            conn_setup = mysql.connector.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD
            )
            cursor_setup = conn_setup.cursor()
            cursor_setup.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE}")
            conn_setup.commit()
            conn_setup.close()
        except Exception as e:
            print(f"[DB ERROR] Could not create database: {e}")
            return False

        conn = DBManager.get_connection()
        if not conn:
            return False
            
        cursor = conn.cursor()
        
        # MySQL Standard Schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS citizens (
                aadhar_masked   VARCHAR(255) PRIMARY KEY,
                virtual_id      VARCHAR(255) UNIQUE,
                full_name       VARCHAR(255) NOT NULL,
                gender          VARCHAR(50),
                date_of_birth   VARCHAR(50),
                address         TEXT,
                city            VARCHAR(100),
                state           VARCHAR(100),
                phone_masked    VARCHAR(50),
                pan_number      VARCHAR(50),
                cibil_score     INTEGER,
                good_human_points INTEGER DEFAULT 1000,
                kyc_status      VARCHAR(50) DEFAULT 'Full KYC',
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vahan_registry (
                plate_number        VARCHAR(50) PRIMARY KEY,
                vehicle_class       VARCHAR(100) NOT NULL,
                make                VARCHAR(100),
                model               VARCHAR(100),
                color               VARCHAR(50),
                fuel_type           VARCHAR(50),
                chassis_number      VARCHAR(255),
                engine_number       VARCHAR(255),
                registration_date   VARCHAR(50),
                rto_location        VARCHAR(100),
                rc_status           VARCHAR(50) DEFAULT 'Active',
                fitness_valid_upto  VARCHAR(50),
                invoice_price       DOUBLE,
                insurance_company   VARCHAR(255),
                insurance_policy    VARCHAR(255),
                insurance_expiry    VARCHAR(50),
                puc_valid_upto      VARCHAR(50),
                hypothecation       VARCHAR(255),
                financer_bank       VARCHAR(255),
                owner_aadhar        VARCHAR(255),
                owner_name          VARCHAR(255),
                CONSTRAINT fk_owner FOREIGN KEY (owner_aadhar) REFERENCES citizens (aadhar_masked)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fastag_accounts (
                fastag_id           VARCHAR(100) PRIMARY KEY,
                tag_id              VARCHAR(100) UNIQUE,
                plate_number        VARCHAR(50),
                customer_id         VARCHAR(100),
                wallet_balance      DOUBLE,
                issuer_bank         VARCHAR(255),
                bank_account_masked VARCHAR(100),
                tag_status          VARCHAR(50) DEFAULT 'Active',
                vehicle_class_code  VARCHAR(50),
                kyc_status          VARCHAR(50) DEFAULT 'Full KYC',
                low_balance_alert   INTEGER DEFAULT 0,
                CONSTRAINT fk_plate FOREIGN KEY (plate_number) REFERENCES vahan_registry (plate_number)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fastag_transactions (
                tx_id           INT AUTO_INCREMENT PRIMARY KEY,
                fastag_id       VARCHAR(100),
                toll_plaza      VARCHAR(255),
                timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,
                amount_deducted DOUBLE,
                CONSTRAINT fk_fastag FOREIGN KEY (fastag_id) REFERENCES fastag_accounts (fastag_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS challans (
                challan_id        INT AUTO_INCREMENT PRIMARY KEY,
                plate_number      VARCHAR(50),
                violation_type    VARCHAR(255),
                base_fine         DOUBLE,
                wealth_multiplier DOUBLE,
                final_fine        DOUBLE,
                status            VARCHAR(50) DEFAULT 'Unpaid',
                date_issued       DATETIME DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_plate_challan FOREIGN KEY (plate_number) REFERENCES vahan_registry (plate_number)
            )
        """)

        # Plate Sightings (Pipeline specific)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plate_sightings (
                id            INT AUTO_INCREMENT PRIMARY KEY,
                plate_text    VARCHAR(50) NOT NULL,
                timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,
                vehicle_class VARCHAR(100),
                orientation   VARCHAR(50),
                confidence    DOUBLE,
                image_path    TEXT,
                wealth_mult   DOUBLE DEFAULT 1.0
            )
        """)

        # Plate Registry (Quick Access / Learning index)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plate_registry (
                plate_text      VARCHAR(50) PRIMARY KEY,
                citizen_id      VARCHAR(100),
                vehicle_id      VARCHAR(100),
                first_seen      DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen       DATETIME DEFAULT CURRENT_TIMESTAMP,
                sighting_count  INT DEFAULT 1,
                auto_generated  TINYINT(1) DEFAULT 1
            )
        """)

        # Users Table (New for Login & Roles)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id         INT AUTO_INCREMENT PRIMARY KEY,
                full_name       VARCHAR(255) NOT NULL,
                contact_no      VARCHAR(20) UNIQUE NOT NULL,
                professional_id VARCHAR(100),
                role            VARCHAR(50) DEFAULT 'Citizen',
                promotions      INT DEFAULT 0,
                red_cards       INT DEFAULT 0,
                warnings        INT DEFAULT 0,
                face_encoding   BLOB,
                profile_image   TEXT,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Sentinel AI: Sentience & Harmony Logic
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentience_harmony (
                id                INT AUTO_INCREMENT PRIMARY KEY,
                harmony_index     DOUBLE DEFAULT 100.0,
                justice_precision DOUBLE DEFAULT 100.0,
                last_audit        DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        return True

if __name__ == "__main__":
    print(f"Initializing MySQL database...")
    if DBManager.ensure_schema():
        print("MySQL Schema verified successfully.")
    else:
        print("Failed to setup MySQL schema.")
