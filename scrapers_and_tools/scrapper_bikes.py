import requests
from bs4 import BeautifulSoup
import csv
import os
import time
import re
from urllib.parse import urljoin

# --- HELPERS ---

def clean_price(price_str):
    """Turns '₹88,528*' or '₹ 1.10 Lakh' into a clean number."""
    if not price_str or "N/A" in str(price_str):
        return 0
    if 'Lakh' in str(price_str):
        nums = re.findall(r'[\d.]+', str(price_str))
        return int(float(nums[0]) * 100000) if nums else 0
    clean_num = re.sub(r'[^\d]', '', str(price_str))
    return int(clean_num) if clean_num else 0

# --- MAIN ENGINE ---

def scrape_bike_brand(brand_url, brand_name):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    }
    print(f"\n>>> SCRAPING BIKES: {brand_name.upper()}")
    
    try:
        response = requests.get(brand_url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
    except:
        print(f"Failed to reach {brand_name}")
        return

    csv_filename = "bikes_detail_data.csv"
    # Create folder for bike images
    folder_name = f"Bikes_{brand_name}"
    if not os.path.exists(folder_name): os.makedirs(folder_name)

    # Check if file exists to write header only once
    file_exists = os.path.isfile(csv_filename)

    with open(csv_filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Bike Name", "Image Path", "Specs", "Base Price", "Top Price", "Avg Price"])

        # Find the bike list (Image 13958a)
        bike_cards = soup.find_all('li', class_='gsc_col-xs-12')

        for card in bike_cards:
            try:
                # 1. Name Extraction from <h3> (Image 13958a)
                name_tag = card.find('h3')
                if not name_tag: continue
                bike_name = name_tag.get_text().strip()

                # Filter out 'Used' or 'Launch' indicators
                if any(x in bike_name.lower() for x in ["used", "vs", "compare"]):
                    continue

                # 2. Image and Link
                link_tag = card.find('a', href=True)
                model_link = urljoin("https://www.bikedekho.com", link_tag['href'])
                
                img_tag = card.find('img')
                img_path = f"{folder_name}/{bike_name.replace(' ', '_')}.jpg"
                if img_tag and img_tag.get('src'):
                    with open(img_path, 'wb') as f:
                        f.write(requests.get(img_tag['src']).content)

                # 3. Basic Specs (CC, Mileage from the icons)
                specs = " | ".join([s.get_text().strip() for s in card.find_all('span') if len(s.text) > 2])

                # 4. Deep Price Extraction (Images 1398c9 and 139967)
                base_on = top_on = 0
                try:
                    price_url = model_link.rstrip('/') + "/price-in-delhi"
                    p_resp = requests.get(price_url, headers=headers, timeout=10)
                    p_soup = BeautifulSoup(p_resp.text, 'html.parser')
                    
                    # Target the 'tfoot' logic which is identical to cars
                    price_footers = p_soup.find_all('tfoot', class_='onroadprice')
                    
                    if price_footers:
                        # Base price from first table (Image 1398c9)
                        base_td = price_footers[0].find('td', class_=re.compile(r'gsc_col-xs-4'))
                        base_on = clean_price(base_td.get_text()) if base_td else 0
                        
                        # Top price from last table (Image 139967)
                        top_td = price_footers[-1].find('td', class_=re.compile(r'gsc_col-xs-4'))
                        top_on = clean_price(top_td.get_text()) if top_td else 0
                except:
                    pass

                # Fallback to 'Onwards' price if deep page fails
                if base_on == 0:
                    onwards_div = card.find('div', class_='price')
                    if onwards_div:
                        base_on = top_on = clean_price(onwards_div.get_text())

                avg_on = (base_on + top_on) / 2 if base_on > 0 else "N/A"

                writer.writerow([bike_name, img_path, specs, base_on, top_on, avg_on])
                print(f"   [✓] {bike_name} | Avg: ₹{avg_on}")
                time.sleep(1)

            except Exception as e:
                continue

# --- BRANDS TO SCRAPE (From Image 139c71) ---

bike_brands = [
    ("https://www.bikedekho.com/honda-bikes", "Honda"),
    ("https://www.bikedekho.com/royal-enfield-bikes", "Royal-Enfield"),
    ("https://www.bikedekho.com/tvs-bikes", "TVS"),
    ("https://www.bikedekho.com/yamaha-bikes", "Yamaha"),
    ("https://www.bikedekho.com/hero-bikes", "Hero"),
    ("https://www.bikedekho.com/bajaj-bikes", "Bajaj"),
    ("https://www.bikedekho.com/ktm-bikes", "KTM"),
    ("https://www.bikedekho.com/suzuki-bikes", "Suzuki"),
    ("https://www.bikedekho.com/ola-electric-bikes", "Ola-Electric"),
    ("https://www.bikedekho.com/ather-energy-bikes", "Ather"),
    ("https://www.bikedekho.com/triumph-bikes", "Triumph"),
    ("https://www.bikedekho.com/bmw-motorrad-bikes", "BMW-Motorrad"),
    ("https://www.bikedekho.com/kawasaki-bikes", "Kawasaki")
]

for url, brand in bike_brands:
    scrape_bike_brand(url, brand)

print("\n--- BIKE DATASET COMPLETE ---")