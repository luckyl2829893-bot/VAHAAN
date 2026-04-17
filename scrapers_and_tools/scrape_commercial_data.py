import pandas as pd
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--window-size=1920,1080")
    # Crucial for avoiding bot-detection on brand pages
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def clean_price_to_num(price_text):
    try:
        nums = re.findall(r"[-+]?\d*\.\d+|\d+", price_text.replace(",", ""))
        multiplier = 10000000 if "Cr" in price_text else 100000
        if not nums: return 0, 0
        base = float(nums[0]) * multiplier
        top = float(nums[1]) * multiplier if len(nums) > 1 else base
        return int(base), int(top)
    except: return 0, 0

def scrape_brand_fleet(url, brand_name):
    print(f"\n[>] Sniping {brand_name} Fleet from {url}...")
    driver = setup_driver()
    data = []
    
    try:
        driver.get(url)
        # Give extra time for React/Next.js components to mount
        time.sleep(5) 

        # Scroll to ensure "All Models" section loads
        for _ in range(6):
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(1)

        # BROAD SELECTOR: Find all H3 tags that usually represent model names
        # Then we find their closest common container
        wait = WebDriverWait(driver, 10)
        names = driver.find_elements(By.TAG_NAME, "h3")
        
        print(f"    [!] Detected {len(names)} potential models. Filtering...")

        for name_elem in names:
            try:
                model_name = name_elem.text.strip()
                # Skip generic section headers
                if not model_name or any(x in model_name for x in ["Price List", "Popular", "Upcoming", "Latest", "Comparisons"]):
                    continue
                
                # Move up to the container to find price and specs
                # Usually, name, price, and specs are siblings in a div
                container = name_elem.find_element(By.XPATH, "./ancestor::div[contains(@class, 'gsc_col') or contains(@class, 'model-card') or contains(@class, 'content')][1]")
                
                try:
                    price_text = container.find_element(By.XPATH, ".//*[contains(@class, 'price') or contains(text(), '₹')]").text
                except:
                    price_text = "0"
                
                try:
                    spec_list = container.find_elements(By.TAG_NAME, "span")
                    specs = " | ".join([s.text for s in spec_list if len(s.text) > 3])
                except:
                    specs = ""

                base_p, top_p = clean_price_to_num(price_text)
                avg_p = (base_p + top_p) / 2
                
                # Format: Image Path -> Brand/Model_Name.jpg
                img_path = f"{brand_name}/{model_name.replace(' ', '_')}.jpg"

                data.append({
                    "Car Name": f"{brand_name} {model_name}",
                    "Image Path": img_path,
                    "Specs": specs,
                    "Base On-Road": base_p,
                    "Top On-Road": top_p,
                    "Average On-Road": avg_p
                })
                print(f"       [✓] {model_name} | ₹{avg_p:,.0f}")
                
            except:
                continue
                
    finally:
        driver.quit()
    return data

if __name__ == "__main__":
    brand_urls = {
        "Tata": "https://trucks.cardekho.com/en/brands/tata.html",
        "Mahindra": "https://trucks.cardekho.com/en/brands/mahindra.html",
        "Eicher": "https://trucks.cardekho.com/en/brands/eicher.html",
        "Bharat-Benz": "https://trucks.cardekho.com/en/brands/bharat-benz.html",
        "Ashok-Leyland": "https://trucks.cardekho.com/en/brands/ashok-leyland.html",
        "Force": "https://trucks.cardekho.com/en/brands/force.html",
        "Isuzu": "https://trucks.cardekho.com/en/brands/isuzu.html",
        "Euler": "https://trucks.cardekho.com/en/brands/euler.html"
    }

    all_data = []
    for brand, url in brand_urls.items():
        results = scrape_brand_fleet(url, brand)
        all_data.extend(results)

    if all_data:
        df = pd.DataFrame(all_data).drop_duplicates(subset=["Car Name"])
        df.to_csv("ARG_Master_Fleet_2026.csv", index=False)
        print(f"\n[DONE] {len(df)} vehicles saved to ARG_Master_Fleet_2026.csv")
    else:
        print("\n[FAIL] Still 0 results. Site may be blocking Headless mode. Try commenting out the headless option.")
