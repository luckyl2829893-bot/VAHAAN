import pandas as pd
import re

def standardize_bike_specs(spec_str):
    if not spec_str or pd.isna(spec_str):
        return ""
    
    # Check for Electric indicators
    if any(x in spec_str.lower() for x in ["kw", "hr", "electric", "battery"]):
        # Try to find range if present (usually looks like '181 km')
        range_match = re.search(r'(\d+(\.\d+)?\s*km)', spec_str)
        if range_match:
            return f"Electric{range_match.group(1)}"
        return "Electric"
    
    # Check for Petrol/CNG indicators (usually kmpl)
    mileage_match = re.search(r'(\d+(\.\d+)?\s*kmpl)', spec_str, re.IGNORECASE)
    if mileage_match:
        return f"Petrol{mileage_match.group(1)}"
    
    # Fallback to CC if available
    cc_match = re.search(r'(\d+(\.\d+)?\s*cc)', spec_str, re.IGNORECASE)
    if cc_match:
        return f"Petrol{cc_match.group(1)}"
        
    return "Petrol"

def restructure_bikes():
    input_file = "bikes_detail_data.csv"
    output_file = "bikes_detail_data_fixed.csv"
    
    df = pd.read_csv(input_file)
    
    # 1. Rename Columns
    df.columns = ["Bike Name", "Image Path", "Specs", "Base On-Road", "Top On-Road", "Average On-Road"]
    
    # 2. Fix Specs
    df['Specs'] = df['Specs'].apply(standardize_bike_specs)
    
    # 3. Clean Names (Remove Launch indicators)
    df = df[~df['Specs'].str.contains("Alert Me|Jan,|Apr,|May,|Jun,", na=False)]
    df = df[df['Base On-Road'] > 0]
    
    # 4. Save
    df.to_csv(output_file, index=False)
    print(f"Restructured data saved to {output_file}")

if __name__ == "__main__":
    restructure_bikes()
