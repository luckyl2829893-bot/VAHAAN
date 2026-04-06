# import requests
# from bs4 import BeautifulSoup
# import csv
# import os
# import time
# import re
# from urllib.parse import urljoin

# # --- HELPERS ---

# def clean_price(price_str):
#     """Turns '₹16.50 Lakh' or '₹16,50,433' into a clean number."""
#     if not price_str or "Coming Soon" in str(price_str) or "N/A" in str(price_str):
#         return 0
    
#     # Handle 'Lakh' format
#     if 'Lakh' in str(price_str):
#         num = re.findall(r'[\d.]+', str(price_str))
#         return int(float(num[0]) * 100000) if num else 0
    
#     # Handle standard number format
#     clean_num = re.sub(r'[^\d]', '', str(price_str))
#     return int(clean_num) if clean_num else 0

# def get_fallback_price(card_soup):
#     """Grabs price from the brand page card if the deep page fails."""
#     price_div = card_soup.find('div', class_='price')
#     if price_div:
#         prices = re.findall(r'[\d.]+', price_div.text)
#         # If it's a range like '13.49 - 24.34 Lakh'
#         if len(prices) >= 2:
#             return int(float(prices[0]) * 100000), int(float(prices[1]) * 100000)
#         elif len(prices) == 1:
#             return int(float(prices[0]) * 100000), int(float(prices[0]) * 100000)
#     return 0, 0

# # --- MAIN ENGINE ---

# def scrape_brand_deep(brand_url, brand_name):
#     headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
#     print(f"\n>>> PROCESSING: {brand_name}")
    
#     try:
#         response = requests.get(brand_url, headers=headers)
#         soup = BeautifulSoup(response.text, 'html.parser')
#     except:
#         return

#     csv_filename = f"{brand_name}_final_data.csv"
#     if not os.path.exists(brand_name): os.makedirs(brand_name)

#     with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
#         writer = csv.writer(file)
#         writer.writerow(["Car Name", "Image Path", "Specs", "Base On-Road", "Top On-Road", "Average On-Road"])

#         car_cards = soup.find_all('li', class_='gsc_col-xs-12')

#         for card in car_cards:
#             try:
#                 name_tag = card.find('a')
#                 if not name_tag or " vs " in name_tag.text.lower(): continue
                
#                 car_name = name_tag.text.strip()
#                 model_link = urljoin("https://www.cardekho.com", name_tag['href'])
                
#                 # Get Specs (CC or Battery for EVs)
#                 specs = "N/A"
#                 dotlist = card.find('div', class_='dotlist')
#                 if dotlist: specs = dotlist.text.strip()

#                 # Get Image
#                 img_tag = card.find('img')
#                 img_path = f"{brand_name}/{car_name.replace(' ', '_')}.jpg"
#                 if img_tag and img_tag.get('src'):
#                     with open(img_path, 'wb') as f: f.write(requests.get(img_tag['src']).content)

#                 # --- PRICE EXTRACTION ---
#                 base_on = top_on = 0
                
#                 # Step 1: Try Deep Page
#                 try:
#                     price_url = model_link + "/price-in-new-delhi"
#                     p_resp = requests.get(price_url, headers=headers, timeout=10)
#                     if p_resp.status_code == 200:
#                         p_soup = BeautifulSoup(p_resp.text, 'html.parser')
                        
#                         # Look for any table with prices
#                         price_cells = p_soup.find_all('td', class_=re.compile(r'gsc_col'))
#                         all_prices = [clean_price(c.text) for c in price_cells if clean_price(c.text) > 50000]
                        
#                         if all_prices:
#                             base_on = min(all_prices)
#                             top_on = max(all_prices)
#                 except:
#                     pass

#                 # Step 2: Fallback to Main Page Card if Deep Page failed
#                 if base_on == 0:
#                     base_on, top_on = get_fallback_price(card)

#                 avg = (base_on + top_on) / 2 if base_on > 0 else "N/A"

#                 writer.writerow([car_name, img_path, specs, base_on, top_on, avg])
#                 print(f"   [✓] {car_name} | Avg: {avg}")
#                 time.sleep(1) # Delay to prevent blocking

#             except Exception as e:
#                 print(f"   [!] Error with {car_name}")

# # --- EXECUTION ---
# brands = [
#     ("https://www.cardekho.com/cars/Mahindra", "Mahindra"),
#     ("https://www.cardekho.com/cars/maruti-suzuki-cars", "Maruti-Suzuki"),
#     ("https://www.cardekho.com/cars/Hyundai", "Hyundai"),
#     ("https://www.cardekho.com/cars/Porsche", "Porsche"),
#     ("https://www.cardekho.com/cars/Lamborghini", "Lamborghini"),
#     ("https://www.cardekho.com/cars/BMW", "BMW"),
#     ("https://www.cardekho.com/cars/Kia", "Kia"),
#     ("https://www.cardekho.com/cars/Mercedes-Benz", "Mercedes-Benz"),
#     ("https://www.cardekho.com/cars/Audi", "Audi"),
#     ("https://www.cardekho.com/cars/Volvo", "Volvo"),
#     ("https://www.cardekho.com/cars/Land-Rover", "Land-Rover"),
#     ("https://www.cardekho.com/cars/Skoda", "Skoda")
# ]
# for url, name in brands:
#     scrape_brand_deep(url, name)
# # --- EXECUTION BLOCK ---

# print("\n--- ALL DATA COLLECTED SUCCESSFULLY ---")



 # for maruti suzuki 
import requests
from bs4 import BeautifulSoup
import csv
import os
import time
import re
from urllib.parse import urljoin

def clean_price(price_str, original_str=""):
    """Turns '₹6,47,483*' or '₹ 5.79 Lakh' into a clean number."""
    if not price_str or "N/A" in str(price_str):
        return 0
    
    # Check for 'Lakh' in the specific string or the context string
    has_lakh = 'Lakh' in str(price_str) or 'Lakh' in str(original_str)
    
    if has_lakh:
        # Extract the decimal number (e.g., 5.79 from '5.79 Lakh')
        nums = re.findall(r'[\d.]+', str(price_str))
        if nums:
            # If we found 5.79, it becomes 579,000
            # Some strings might be '579' already if re.sub was used, 
            # but re.findall with [\d.]+ will keep the dot.
            val = float(nums[0])
            # If the value is already large (e.g. 579000), don't multiply again
            if val < 5000:
                return int(val * 100000)
            return int(val)
    
    # Standard cleanup for the deep table values or absolute numbers
    clean_num = re.sub(r'[^\d]', '', str(price_str))
    return int(clean_num) if clean_num else 0

def scrape_brand_final(brand_url, brand_name):
    # Professional headers to stop the "Nothing Scraped" issue
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    }
    print(f"\n>>> STARTING: {brand_name.upper()}")
    
    try:
        response = requests.get(brand_url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
    except:
        print(f"Failed to reach {brand_name}")
        return

    csv_filename = f"{brand_name}_data.csv"
    if not os.path.exists(brand_name): os.makedirs(brand_name)

    # Use a set to prevent duplicates if the page reloads items
    seen_cars = set()

    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Car Name", "Image Path", "Specs", "Base On-Road", "Top On-Road", "Avg On-Road"])

        # Target the <li> elements from your Image 04f31f
        car_cards = soup.find_all('li', class_='gsc_col-xs-12')

        for card in car_cards:
            try:
                # 1. FIND CAR NAME (Avoiding the "Get On-Road" button text)
                name_tag = card.find('h3') or card.find('a', title=True)
                if not name_tag: continue
                
                car_name = name_tag.get_text().strip()
                
                # Check for buttons or "Used" cars
                if any(x in car_name.lower() for x in ["price", "offer", "vs", "used", "view all"]):
                    continue
                
                if car_name in seen_cars: continue
                seen_cars.add(car_name)

                # 2. URL & IMAGE
                link_tag = card.find('a', href=True)
                model_link = urljoin("https://www.cardekho.com", link_tag['href'])
                
                img_tag = card.find('img')
                img_path = f"{brand_name}/{car_name.replace(' ', '_')}.jpg"
                if img_tag and img_tag.get('src'):
                    with open(img_path, 'wb') as f:
                        f.write(requests.get(img_tag['src']).content)

                # 3. SPECS (Captures CC, BHP, Safety from the 'dotlist')
                specs = " | ".join([s.get_text().strip() for s in card.find_all('span')])

                # 4. DEEP PRICE EXTRACTION (Images 04f6c1 and 04f9cb)
                base_on = top_on = 0
                
                try:
                    # Construct Delhi price page
                    price_url = model_link.rstrip('/') + "/price-in-new-delhi"
                    p_resp = requests.get(price_url, headers=headers, timeout=10)
                    p_soup = BeautifulSoup(p_resp.text, 'html.parser')
                    
                    # Target the 'tfoot' with class 'onroadprice' from your screenshots
                    price_footers = p_soup.find_all('tfoot', class_='onroadprice')
                    
                    if price_footers:
                        base_td = price_footers[0].find('td', class_=re.compile(r'gsc_col-xs-4'))
                        base_on = clean_price(base_td.get_text()) if base_td else 0
                        
                        top_td = price_footers[-1].find('td', class_=re.compile(r'gsc_col-xs-4'))
                        top_on = clean_price(top_td.get_text()) if top_td else 0
                except:
                    pass

                # Fallback to main card price if deep link fails
                if base_on == 0:
                    main_p_div = card.find('div', class_='price')
                    if main_p_div:
                        p_text = main_p_div.get_text()
                        # Pass p_text as context so clean_price knows it's 'Lakh'
                        base_on = clean_price(p_text.split('-')[0], original_str=p_text)
                        top_on = clean_price(p_text.split('-')[-1], original_str=p_text)

                avg_on = (base_on + top_on) / 2 if base_on > 0 else "N/A"

                writer.writerow([car_name, img_path, specs, base_on, top_on, avg_on])
                print(f"   [✓] {car_name} saved successfully.")
                time.sleep(1.5) # Critical delay to stop blocking

            except Exception as e:
                print(f"   [!] Error with a car listing: {e}")

# EXECUTION: This list covers ~90% of Indian road volume
targets = [
    ("https://www.cardekho.com/maruti-suzuki-cars", "Maruti"),
  
]

for url, brand in targets:
    scrape_brand_final(url, brand)