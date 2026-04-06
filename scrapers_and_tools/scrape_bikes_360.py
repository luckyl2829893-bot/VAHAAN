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
CSV_FILE = "bikes_detail_data.csv"
BASE_DIR = "ARG_360_Dataset_Bikes"

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Runs in background
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def get_bike_brand_model(bike_name):
    """Returns possible URL slugs for a bike."""
    parts = bike_name.lower().split(" ", 1)
    brand = parts[0]
    if len(parts) > 1:
        model_space = parts[1].replace(" ", "-")
        model_none = parts[1].replace(" ", "")
        return brand, [model_space, model_none]
    return brand, [""]

def download_bike_360(bike_name, driver):
    brand_raw, model_slugs = get_bike_brand_model(bike_name)
    
    # Try all possible slugs
    success = False
    for slug in model_slugs:
        url = f"https://www.bikedekho.com/{brand_raw}/{slug}"
        print(f"\n[>] Target Bike: {bike_name} | URL: {url}")
        
        try:
            driver.get(url)
            time.sleep(5)
            # Clear city selector or other popups
            webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            
            # Look for 360 View tab (multiple strategies)
            xpaths = [
                "//li[contains(., '360')]", 
                "//span[contains(text(), '360')]", 
                "//div[contains(text(), '360')]",
                "//*[contains(text(), '360') and contains(text(), 'View')]"
            ]
            target_tab = None
            for xp in xpaths:
                tabs = driver.find_elements(By.XPATH, xp)
                for tab in tabs:
                    if tab.is_displayed():
                        target_tab = tab
                        break
                if target_tab: break
            
            if target_tab:
                # Ensure visibility before click
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", target_tab)
                time.sleep(2)
                try:
                    target_tab.click()
                except:
                    driver.execute_script("arguments[0].click();", target_tab)
                
                print(f"    Switched to 360º view tab using XPATH: {xp}")
                time.sleep(5)
                
                # Active interaction click (usually an overlay in the center)
                body = driver.find_element(By.TAG_NAME, 'body')
                webdriver.ActionChains(driver).move_to_element(body).move_by_offset(0, -100).click().perform()
                print("    Attempted center-click activation...")
                time.sleep(5)
                
                # Spin to trigger network request
                webdriver.ActionChains(driver).drag_and_drop_by_offset(body, 200, 0).perform()
                success = True
                break
            else:
                print(f"    [?] No 360 tab with slug '{slug}'.")
        except Exception as e:
            print(f"    [!] Error with slug '{slug}': {e}")
            continue

    if not success:
        print(f"    [!] No 360 viewer. Attempting fallback (front/rear static images)...")
        try:
            # Look for static images in the gallery
            all_imgs = driver.find_elements(By.TAG_NAME, "img")
            
            # Directory setup
            brand_folder = brand_raw.capitalize()
            bike_folder = bike_name.replace(" ", "_").replace("/", "_")
            save_folder = os.path.join(BASE_DIR, brand_folder, bike_folder)
            if not os.path.exists(save_folder): os.makedirs(save_folder)

            found_fallback = 0
            # Define keywords for front and rear
            keywords = {"front": "front", "rear": "rear", "back": "rear"}
            
            for keyword, label in keywords.items():
                for img in all_imgs:
                    alt = (img.get_attribute("alt") or "").lower()
                    src = (img.get_attribute("src") or "").lower()
                    if keyword in alt or keyword in src:
                        # Grab the highest resolution available (often in 'data-src')
                        img_url = img.get_attribute("data-src") or img.get_attribute("src")
                        if img_url and img_url.startswith("http"):
                            resp = requests.get(img_url, timeout=5)
                            if resp.status_code == 200 and len(resp.content) > 5000:
                                with open(f"{save_folder}/angle_{label}.jpg", 'wb') as f:
                                    f.write(resp.content)
                                print(f"    [✓] Saved fallback: {label} view.")
                                found_fallback += 1
                                break # Move to next keyword
            if found_fallback == 0:
                print("    [!] No static fallback images found.")
        except Exception as fe:
            print(f"    [!] Fallback failed: {fe}")
        return

    print("    Scanning logs for image sequence...")
    # 3. NETWORK SPY: Sniff the frames base URL
    base_url = None
    for _ in range(15):
        logs = driver.get_log('performance')
        for entry in logs:
            try:
                log = json.loads(entry['message'])['message']
                if log.get('method') == 'Network.responseReceived':
                    url_found = log['params']['response'].get('url', '')
                    # Look for 360-view assets
                    if ('.jpg' in url_found.lower() or '.webp' in url_found.lower()) and \
                       ('/360views/' in url_found.lower() or 'exterior' in url_found.lower()):
                        # Strip index and extension to get the folder base
                        base_url = re.sub(r'(\d+|img_0_0_\d+)\.(jpg|png|webp).*', '', url_found)
                        break
            except: continue
        if base_url: break
        time.sleep(1)

    if not base_url:
        print(f"    [!] No 360 sequence detected for {bike_name}.")
        return

    # 4. DIRECTORY & DOWNLOAD
    brand_folder = brand_raw.capitalize()
    bike_folder = bike_name.replace(" ", "_").replace("/", "_")
    save_folder = os.path.join(BASE_DIR, brand_folder, bike_folder)
    if not os.path.exists(save_folder): os.makedirs(save_folder)

    print(f"    [✓] Base URL: {base_url}")
    print(f"    Downloading angles...")
    downloaded = 0
    # Try indices from 0 to 40 (Bikedekho frames are usually 1-36 or 0-35)
    for i in range(0, 41): 
        try:
            # Common naming permutations
            urls_to_try = [
                f"{base_url}{i}.jpg", 
                f"{base_url}img_0_0_{i}.jpg", 
                f"{base_url}{i+1}.jpg"
            ]
            for frame_url in urls_to_try:
                resp = requests.get(frame_url, timeout=5)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    with open(f"{save_folder}/angle_{downloaded:02d}.jpg", 'wb') as f:
                        f.write(resp.content)
                    downloaded += 1
                    break # Success for this angle
            if downloaded >= 36: break
        except: continue
    
    if downloaded > 10:
        print(f"    [✓] Successfully saved {downloaded} angles.")
    else:
        print(f"    [!] Download failed or insufficient frames found.")

if __name__ == "__main__":
    if not os.path.exists(BASE_DIR): os.makedirs(BASE_DIR)
    
    try:
        df = pd.read_csv(CSV_FILE)
        print(f"Ready to process {len(df)} bikes.")
    except Exception as e:
        print(f"Critical error reading CSV: {e}")
        exit()
    
    driver = setup_driver()
    try:
        for bike in df['Bike Name']:
            try:
                download_bike_360(bike, driver)
            except Exception as e:
                print(f"Error processing {bike}: {e}")
    finally:
        driver.quit()
        print("\n--- ALL VISUALS DOWNLOADED ---")
