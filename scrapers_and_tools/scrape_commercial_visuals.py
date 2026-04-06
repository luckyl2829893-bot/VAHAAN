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
from selenium.webdriver.common.keys import Keys
import json

# --- CONFIGURATION ---
DATA_FILES = ["trucks_detail_data.csv", "buses_detail_data.csv", "three_wheelers_detail_data.csv"]
BASE_DIR = "ARG_Commercial_Dataset"

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def get_commercial_url(name, category):
    slug = name.lower().replace(" ", "-").replace("(", "").replace(")", "").replace(".", "")
    if category == "Bus":
        return f"https://buses.cardekho.com/en/buses/{slug}"
    return f"https://trucks.cardekho.com/en/trucks/{slug}"

def download_commercial_images(name, category, driver):
    url = get_commercial_url(name, category)
    print(f"\n[>] Target: {name} ({category})")
    print(f"    URL: {url}")
    
    try:
        driver.get(url)
        time.sleep(5)
        webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        
        # 1. TRY 360 ACTIVATION (JUST IN CASE)
        found_360 = False
        try:
            tabs = driver.find_elements(By.XPATH, "//*[contains(text(), '360')]")
            if tabs:
                driver.execute_script("arguments[0].click();", tabs[0])
                time.sleep(3)
                # Interaction
                body = driver.find_element(By.TAG_NAME, 'body')
                webdriver.ActionChains(driver).move_to_element(body).click().perform()
                time.sleep(5)
                found_360 = True
                print("    [✓] 360 Viewer active!")
        except: pass

        # 2. IF 360 FOUND, SNIFF LOGS
        base_url = None
        if found_360:
            logs = driver.get_log('performance')
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    if log.get('method') == 'Network.responseReceived':
                        url_found = log['params']['response'].get('url', '')
                        if ('.jpg' in url_found.lower()) and ('360' in url_found.lower()):
                            base_url = re.sub(r'(\d+|img_0_0_\d+)\.(jpg|png|webp).*', '', url_found)
                            break
                except: continue

        # 4. DIRECTORY SETUP
        vehicle_folder = name.replace(" ", "_").replace("/", "_")
        save_folder = os.path.join(BASE_DIR, category, vehicle_folder)
        if not os.path.exists(save_folder): os.makedirs(save_folder)

        # 5. DOWNLOAD LOGIC
        if base_url:
            print(f"    [✓] Base URL: {base_url}")
            # Similar to cars/bikes
            downloaded = 0
            for i in range(0, 36):
                f_url = f"{base_url}img_0_0_{i}.jpg"
                try:
                    r = requests.get(f_url, timeout=5)
                    if r.status_code == 200:
                        with open(f"{save_folder}/angle_{i:02d}.jpg", 'wb') as f:
                            f.write(r.content)
                        downloaded += 1
                except: continue
            if downloaded > 10: return
            
        # 6. FALLBACK: STATIC IMAGES
        print("    [!] No 360 found. Capturing static fallback images...")
        try:
            # Click the 'Pictures' or 'Gallery' tab
            gallery_tab = driver.find_elements(By.XPATH, "//li[contains(., 'Pictures')] | //span[contains(text(), 'Pictures')]")
            if gallery_tab:
                driver.execute_script("arguments[0].click();", gallery_tab[0])
                time.sleep(3)
            
            all_imgs = driver.find_elements(By.TAG_NAME, "img")
            saved = 0
            # Target labels
            targets = {"front": "front", "rear": "rear", "side": "side"}
            for keyword, label in targets.items():
                for img in all_imgs:
                    alt = (img.get_attribute("alt") or "").lower()
                    src = (img.get_attribute("src") or "").lower()
                    if keyword in alt or keyword in src:
                        img_url = img.get_attribute("data-src") or img.get_attribute("src")
                        if img_url and img_url.startswith("http"):
                            resp = requests.get(img_url, timeout=5)
                            if resp.status_code == 200 and len(resp.content) > 5000:
                                with open(f"{save_folder}/angle_{label}.jpg", 'wb') as f:
                                    f.write(resp.content)
                                print(f"    [✓] Saved static: {label}")
                                saved += 1
                                break
            if saved == 0:
                # Last resort: just save the first 3 images found
                for i, img in enumerate(all_imgs[:3]):
                    img_url = img.get_attribute("src")
                    if img_url and img_url.startswith("http"):
                        r = requests.get(img_url, timeout=5)
                        with open(f"{save_folder}/angle_{i}.jpg", 'wb') as f:
                            f.write(r.content)
                print(f"    [✓] Saved {min(len(all_imgs), 3)} generic images.")
                
        except Exception as e:
            print(f"    [!] Fallback failed: {e}")

if __name__ == "__main__":
    if not os.path.exists(BASE_DIR): os.makedirs(BASE_DIR)
    
    driver = setup_driver()
    try:
        for csv_file in DATA_FILES:
            if not os.path.exists(csv_file): continue
            df = pd.read_csv(csv_file)
            print(f"\n--- Processing {csv_file} ({len(df)} units) ---")
            for _, row in df.iterrows():
                download_commercial_images(row['Vehicle Name'], row['Category'], driver)
    finally:
        driver.quit()
        print("\n--- COMMERCIAL DATASET COMPLETE ---")
