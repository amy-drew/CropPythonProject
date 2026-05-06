import requests
import pandas as pd
import time

# --- Step 1: Get all fruit & vegetable products ---
product_url = "https://www.ec.europa.eu/agrifood/api/fruitandvegetables/products"
product_response = requests.get(product_url)

if product_response.status_code != 200:
    raise Exception("Failed to fetch product list")

product_list = product_response.json()
print(f"Found {len(product_list)} products")

# --- Step 2: Query prices for each product across the EU ---
results = []

for product in product_list:
    product_name = product.get("name")
    product_code = product.get("code")

    # API endpoint for prices
    price_url = "https://www.ec.europa.eu/agrifood/api/fruitandvegetables/prices"
    params = {
        "memberStateCodes": "EU",  # Aggregate EU-level data
        "products": product_name,
        "years": "2025"
    }

    response = requests.get(price_url, params=params)
    if response.status_code != 200:
        print(f"Failed to fetch prices for {product_name}")
        continue

    data = response.json()
    prices = [record.get("price") for record in data.get("records", []) if record.get("price") is not None]

    if prices:
        avg_price = sum(prices) / len(prices)
        results.append({
            "Product": product_name,
            "Code": product_code,
            "Average Price (EUR/kg)": round(avg_price, 2),
            "Data Points": len(prices)
        })
    else:
        results.append({
            "Product": product_name,
            "Code": product_code,
            "Average Price (EUR/kg)": "N/A",
            "Data Points": 0
        })

    time.sleep(0.5)  # Be polite to the server

# --- Step 3: Save to CSV ---
df = pd.DataFrame(results)
df.to_csv("EU_Fruit_Veg_Average_Prices_2025.csv", index=False)
print("Saved results to EU_Fruit_Veg_Average_Prices_2025.csv")
