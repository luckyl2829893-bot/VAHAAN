import os
import time
import requests
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import json

# --- CONFIGURATION ---
CSV_FILE = "cars_details_data.csv"
BASE_DIR = "ARG_360_Dataset"

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Runs in background
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-notifications")
    # Enable performance logging to catch image URLs
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def get_brand_from_name(car_name):
    """Extracts the first word as brand, handles Maruti Suzuki special case."""
    name = car_name.lower()
    if name.startswith("maruti suzuki"):
        return "maruti", car_name[14:].strip()
    if name.startswith("mercedes-benz"):
        return "mercedes-benz", car_name[14:].strip()
    if name.startswith("land rover"):
        return "land-rover", car_name[11:].strip()
    
    parts = car_name.split(" ", 1)
    brand = parts[0].lower()
    model = parts[1] if len(parts) > 1 else ""
    return brand, model

def download_360(car_name, driver):
    # 1. CLEANING & URL GENERATION
    clean_name = car_name.replace("Used ", "").replace(" 2026", "").replace(" 2025", "").replace(" 2024", "").strip()
    brand_raw, model_raw = get_brand_from_name(clean_name)
    
    # Construct slug: brand-model-360-view
    model_slug = model_raw.lower().replace(" ", "-").replace("(", "").replace(")", "")
    url = f"https://www.cardekho.com/{brand_raw}-{model_slug}-360-view.htm"
    
    print(f"\n[>] Target: {car_name} | Brand: {brand_raw} | Model: {model_raw}")
    print(f"    URL: {url}")
    
    try:
        driver.get(url)
        time.sleep(3)
        
        # Step 0: Clear any popups (City Selector, etc.) 
        webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
        
        # 2. MULTI-STEP INTERACTION
        try:
            # Step A: Scroll to viewer
            driver.execute_script("window.scrollTo(0, 650);")
            time.sleep(2)

            # Step B: Click "Tap to Interact 360" or similar
            targets = [
                "//div[contains(text(), 'Tap to Interact')]",
                "//div[contains(text(), 'Experience 360')]",
                "//span[contains(text(), 'Interact')]",
                "//div[contains(@class, 'outer360')]"
            ]
            for t in targets:
                elements = driver.find_elements(By.XPATH, t)
                if elements:
                    driver.execute_script("arguments[0].click();", elements[0])
                    print("    Activated primary viewer...")
                    time.sleep(4)
                    break
            
            # Step C: Final "CLICK TO INTERACT" overlay
            interact_overlay = driver.find_elements(By.XPATH, "//div[contains(text(), 'CLICK TO INTERACT')]")
            if interact_overlay:
                driver.execute_script("arguments[0].click();", interact_overlay[0])
                print("    Activated gallery overlay...")
                time.sleep(4)
                
            # Step D: Force interaction to trigger frame requests
            webdriver.ActionChains(driver).drag_and_drop_by_offset(driver.find_element(By.TAG_NAME, 'body'), 150, 0).perform()
        except:
            pass

        print("    Scanning logs for image sequence...")
        # 3. LOG SCANNING with Retry
        base_url = None
        for _ in range(15):
            logs = driver.get_log('performance')
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    if log.get('method') == 'Network.responseReceived':
                        url_found = log['params']['response'].get('url', '')
                        if 'exterior' in url_found.lower() and 'img_0_0_' in url_found.lower():
                            base_url = re.sub(r'img_0_0_\d+\.(jpg|png|webp).*', '', url_found)
                            break
                except: continue
            if base_url: break
            time.sleep(1)

        if not base_url:
            print(f"    [!] No 360 pattern found for {car_name}.")
            return

        # 4. DIRECTORY & DOWNLOAD
        brand_folder = brand_raw.capitalize()
        car_folder = car_name.replace(" ", "_").replace("/", "_")
        save_folder = os.path.join(BASE_DIR, brand_folder, car_folder)
        if not os.path.exists(save_folder): os.makedirs(save_folder)

        print(f"    [✓] Base URL found. Downloading 36 angles...")
        downloaded = 0
        for i in range(36):
            try:
                frame_url = f"{base_url}img_0_0_{i}.jpg"
                img_data = requests.get(frame_url, timeout=10).content
                if len(img_data) > 1000: 
                    with open(f"{save_folder}/angle_{i:02d}.jpg", 'wb') as f:
                        f.write(img_data)
                    downloaded += 1
            except: continue
        
        if downloaded > 10:
            print(f"    [✓] Saved {downloaded} angles to {save_folder}")
        else:
            print(f"    [!] Download failed or insufficient frames.")
                
    except Exception as e:
        print(f"    [!] Error: {e}")

if __name__ == "__main__":
    if not os.path.exists(BASE_DIR): os.makedirs(BASE_DIR)
    
    df = pd.read_csv(CSV_FILE)
    
    # Filter for valid cars only
    df = df[~df['Specs'].str.contains("Launch|Expected", na=False)]
    df = df[~df['Car Name'].str.contains("View All|Get On-Road|Used", na=False)]
    
    print(f"Ready to process {len(df)} cars.")
    
    driver = setup_driver()
    try:
        # Start with a few for demo, user can interrupt or let it run
        for car in df['Car Name']:
            download_360(car, driver)
    finally:
        driver.quit()
        print("\n--- ALL VISUALS DOWNLOADED ---")
