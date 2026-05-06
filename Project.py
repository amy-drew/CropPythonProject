import streamlit as st
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import re
from rapidfuzz import process, fuzz
import numpy as np
from tensorflow.keras.models import load_model
import matplotlib.pyplot as plt
import seaborn as sns


# Load EcoCrop dataset
crops = pd.read_csv(r'EcoCrop_DB.csv', encoding='latin1')
yields = pd.read_csv(r'FAOSTAT_data_en_8-18-2025.csv', encoding='latin1')

# Plant Recommender
def run_plant_finder():
    with st.form("my_form"):
        slider_val = st.slider('Soil PH', min_value=1.0, step=0.1, max_value=14.0, format="%0.1f")
        radio_text = st.radio('Soil Texture:', ['Light','Medium','Heavy'])
        radio_scale = st.radio('Production Scale:', ['Small','Large','Either'])
        postcode = st.text_input('Postcode:')
        submitted = st.form_submit_button("Submit", type="primary")

        if submitted:
            with st.spinner(text='In progress'):
                time.sleep(3)
                st.success('Done')
            # Weather API
            url = f"https://api.postcodes.io/postcodes/{postcode}"
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                result = data.get("result")
                if result:
                    latitude = result["latitude"]
                    longitude = result["longitude"]
                else:
                    raise ValueError("No result found for this postcode.")
            else:
                    raise Exception(f"API error: {response.status_code} - {response.text}")
            today = datetime.today().date()
            last_year = today - timedelta(days=365)

            # Format as ISO strings
            start_date = last_year.strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")

            # API request
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date,
                "end_date": end_date,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "Europe/London"
            }
            response = requests.get(url, params=params)
            data = response.json()

            # Check if 'daily' exists before processing
            if "daily" in data:
               df = pd.DataFrame({
                "date": data["daily"]["time"],
                "temp_max": data["daily"]["temperature_2m_max"],
                "temp_min": data["daily"]["temperature_2m_min"],
                "rain_mm": data["daily"]["precipitation_sum"]
            })

            # Convert date and calculate daily mean temperature
            df["date"] = pd.to_datetime(df["date"])
            df["temp_mean"] = (df["temp_max"] + df["temp_min"]) / 2

            # Overall averages
            average_temp = df["temp_mean"].mean()
            average_rainfall = df["rain_mm"].mean()
            average_rainfall_annual = average_rainfall * 365

            # Monthly aggregation
            df.set_index("date", inplace=True)
            monthly_avg_temp = df["temp_mean"].resample("M").mean()
            monthly_total_rainfall = df["rain_mm"].resample("M").sum()

            hemisphere = "South"
            if latitude > 0:
                hemisphere = "North"

            if hemisphere == "North":
                high_sun_months = [4, 5, 6, 7, 8, 9]
                low_sun_months = [10, 11, 12, 1, 2, 3]
            if hemisphere == "South":
                low_sun_months = [4, 5, 6, 7, 8, 9]
                high_sun_months = [10, 11, 12, 1, 2, 3]
            
            high_sun_total = monthly_total_rainfall[monthly_total_rainfall.index.month.isin(high_sun_months)].sum()
            low_sun_total = monthly_total_rainfall[monthly_total_rainfall.index.month.isin(low_sun_months)].sum()
            total = high_sun_total + low_sun_total
            if total == 0:
                seasonality = 140
            high_sun_ratio = high_sun_total /total
            if high_sun_ratio >= 0.7:
                seasonality = 280
            elif high_sun_ratio >= 0.3:
                seasonality = 140
            else:
                seasonality = 0
            desert_threshold = average_temp * 20
            desert_threshold = desert_threshold + seasonality


            climate = ""

            # Polar climates (Group E)
            if monthly_avg_temp.mean() < 10:
                if monthly_avg_temp.mean() < 0:
                    climate = "EF"  # Icecap
                else:
                    climate = "ET"  # Tundra

            # Arid climates (Group B)
            elif average_rainfall_annual < 890:
                if average_rainfall_annual < desert_threshold:
                    climate = "BW"  # Desert
                else:
                    climate = "BS"  # Steppe

            # Tropical climates (Group A)
            elif average_temp > 18:
                driest_month_rain = monthly_total_rainfall.min()
                if driest_month_rain < 60:
                    if average_rainfall_annual < 100 * driest_month_rain:
                        climate = "AM"  # Monsoon
                    else:
                        climate = "AW"  # Tropical wet & dry
                else:
                    climate = "AF"  # Tropical wet

            # Continental climates (Group D)
            elif monthly_avg_temp.min() < -3 and monthly_avg_temp.max() > 10:
                high_sun_rain = monthly_total_rainfall[monthly_total_rainfall.index.month.isin(high_sun_months)]
                low_sun_rain = monthly_total_rainfall[monthly_total_rainfall.index.month.isin(low_sun_months)]
                if high_sun_rain.max() > 10 * low_sun_rain.min():
                    climate = "DW"  # Dry winter
                else:
                    climate = "DF"  # Wet all year

            # Temperate climates (Group C)
            elif monthly_avg_temp.min() > -3 and monthly_avg_temp.min() < 18 and monthly_avg_temp.mean() > 10:
                low_sun_rain = monthly_total_rainfall[monthly_total_rainfall.index.month.isin(low_sun_months)]
                high_sun_rain = monthly_total_rainfall[monthly_total_rainfall.index.month.isin(high_sun_months)]
                if low_sun_rain.max() > 3 * high_sun_rain.min():
                    climate = "CS"  # Dry summer
                else:
                    climate = "CF"  # Wet all year



            edible_keywords = ["vegetables", "fruits & nuts", "cereals & pseudocereals"]

            filtered = crops[
                (crops["PHOPMN"] <= slider_val) & (crops["PHOPMX"] >= slider_val) &
                (crops["TEXT"].str.lower().str.contains(radio_text.lower())) &
                (crops["TOPMN"] <= average_temp) & (crops["TOPMX"] >= average_temp) &
                (crops["ROPMN"] <= average_rainfall_annual) & (crops["ROPMX"] >= average_rainfall_annual) &
                (crops["CAT"].apply(lambda x: isinstance(x, str) and any(keyword in x.lower() for keyword in edible_keywords))) &
                (crops["CLIZ"].str.lower().str.contains(climate.lower()))
            ]

            # Apply PLAT filter only if 'Either' is not selected
            if radio_scale.lower() != "either":
                filtered = filtered[
                    filtered["PLAT"].str.lower().str.contains(radio_scale.lower())
                ]




            # Show results
            if not filtered.empty:
                st.subheader("Suitable Crops for Your Conditions")
                # Create a simplified results table
                results = filtered[["ScientificName", "COMNAME"]].copy()

                # Drop rows with missing or empty common names
                results = results[results["COMNAME"].notna() & (results["COMNAME"].str.strip() != "")]

                # Extract only the first common name
                results["CommonName"] = results["COMNAME"].str.split(",").str[0].str.strip()

                # Display only ScientificName and CommonName
                st.subheader("🌱 Suitable Crops for Your Conditions")
                st.dataframe(results[["ScientificName", "CommonName"]])

            else:
                st.warning("No crops match your current conditions. Try adjusting your inputs.")

# Plant yields
def run_plant_yields():
    # File to store crop records
    DATA_FILE = "crop_records.csv"

    # Ensure the file exists
    if not os.path.exists(DATA_FILE):
        # Create an empty DataFrame with the correct columns
        empty_df = pd.DataFrame(columns=["CropID", "Crop", "Planting Date", "Last Update", "Estimated Yield"])
        empty_df.to_csv(DATA_FILE, index=False)

    # Load existing data
    crop_df = pd.read_csv(DATA_FILE)
    
    # Form to add a new crop record
    st.header("🌾 Crop Tracker")
    with st.form("add_crop",clear_on_submit=True):

        def clean_name(name):
            if pd.isna(name):
                return None
            name = str(name)
            name = re.sub(r'<[^>]+>', '', name)  # Remove HTML tags
            name = name.split(',')[0].strip()    # Take first name before comma
            return name
        
        edible_keywords = ["vegetables", "fruits & nuts", "cereals & pseudocereals"]
        filteredcrops = crops[(crops["CAT"].apply(lambda x: isinstance(x, str) and any(keyword in x.lower() for keyword in edible_keywords)))]
        crop_name = sorted(
            filteredcrops['COMNAME']
            .dropna()
            .apply(clean_name)
            .dropna()
            .map(str.strip)
            .map(str.title)
            .unique()
            .tolist()
        )
        crop_name.append("")
        cropamount =len(crop_name) - 1
        # Create dropdown
        selected_crop = st.selectbox("Select Crop Name", options=crop_name, index=cropamount)
        planting_date = st.date_input("Planting Date", value=datetime.today())
        col1, col2 = st.columns([2, 1])
        location = st.text_input("Plot Postcode")
        with col1:
            plot_size = st.number_input("Plot Size", min_value=0.0, step=0.1)

        with col2:
            unit = st.selectbox("Unit", ["ft²", "m²", "km²", "acres", "hectares"])
        submitted = st.form_submit_button("Add Record", type="primary")

        if submitted:
            if selected_crop != "" and plot_size != 0:
                yields['CleanCrop'] = yields['Item'].dropna().apply(lambda x: re.sub(r'[^\w\s]', '', str(x).lower().strip()))
                def find_best_match(name, choices):
                    match, score, _ = process.extractOne(name, choices, scorer=fuzz.token_sort_ratio)
                    return match if score > 80 else None

                # Yield lookup function
                def get_estimated_yield(clean_name, category, faostat_df):
                    category_defaults = {
                        "vegetables": 2500,
                        "fruits & nuts": 3000,
                        "cereals & pseudocereals": 5000
                    }
                    match = find_best_match(clean_name, faostat_df['CleanCrop'].tolist())
                    if match:
                        row = faostat_df[faostat_df['CleanCrop'] == match]
                        if not row.empty and 'Value' in row.columns:
                            return row['Value'].values[0], match
                    if category and category.lower() in category_defaults:
                        return category_defaults[category.lower()], None
                    return 2500, None

            
                cleaned_crop = re.sub(r'[^\w\s]', '', selected_crop.lower().strip())

                crop_row = filteredcrops[filteredcrops['COMNAME'].apply(clean_name).str.lower().str.strip() == selected_crop.lower().strip()]
                crop_category = crop_row['CAT'].values[0] if not crop_row.empty else None
                crop_id = crop_row['CropID'].values[0] if not crop_row.empty and 'CropID' in crop_row.columns else None

                estimated_yield, faostat_match = get_estimated_yield(cleaned_crop, crop_category, yields)
                def convert_to_hectares(size, unit):
                    unit = unit.lower()
                    if unit in ["m²", "sqm", "square meters"]:
                        return size / 10_000
                    elif unit in ["acres"]:
                        return size * 0.404686
                    elif unit in ["ft²", "sqft", "square feet"]:
                        return size * 0.000092903
                    elif unit in ["km²", "sqkm", "square kilometers"]:
                        return size * 100
                    elif unit in ["ha", "hectares"]:
                        return size  # already in hectares
                plotsizeha = convert_to_hectares(plot_size,unit)
                estimated_yield = estimated_yield*plotsizeha
                estimated_yield = str(round(estimated_yield,2)) + "Kg"
                
                new_record = {
                    "CropID": crop_id,
                    "Crop": selected_crop,
                    "Planting Date": planting_date.strftime("%Y-%m-%d"),
                    "Last Update": datetime.today().strftime("%Y-%m-%d"),
                    "Estimated Yield": estimated_yield if estimated_yield else "N/A",
                    "Old Estimate": "N/A",
                    "Difference": "N/A",
                    "Postcode": location if location else "N/A"
                }
                
                crop_df = pd.concat([crop_df, pd.DataFrame([new_record])], ignore_index=True)
                crop_df.to_csv(DATA_FILE, index=False)
                st.rerun()
            else:
                st.toast("Please set a value for all items")
            

    # Display crop records
    st.subheader("📋 Crop Records")
    display_cols = ["Crop", "Planting Date", "Last Update", "Estimated Yield", "Old Estimate", "Difference"]
    cropsplanted = st.dataframe(crop_df[display_cols], hide_index=True, on_select="rerun", selection_mode="multi-row")

     
    
    # --- Load models and extract weights ---
    model_paths = {
        "Low": "crop_model_Low.h5",
        "Medium": "crop_model_Medium.h5",
        "High": "crop_model_High.h5"
    }

    model_weights_map = {}
    model_features = ['TMIN', 'TMAX', 'RMIN', 'RMAX', 'PHMIN', 'PHMAX', 'TOPMN', 'TOPMX', 'ROPMN', 'ROPMX']
    feature_bounds = {
        'TMIN': (0, 40), 'TMAX': (0, 45),
        'RMIN': (0, 2000), 'RMAX': (0, 2000),
        'PHMIN': (4.0, 9.0), 'PHMAX': (4.0, 9.0),
        'TOPMN': (4.0, 9.0), 'TOPMX': (4.0, 9.0),
        'ROPMN': (0, 2000), 'ROPMX': (0, 2000)
    }

    for category, path in model_paths.items():
        model = load_model(path)
        dense_layer = next(layer for layer in model.layers if hasattr(layer, 'kernel'))
        layer_weights = dense_layer.get_weights()[0]
        feature_weights = layer_weights.mean(axis=1)
        normalized_weights = feature_weights / np.linalg.norm(feature_weights)
        model_weights_map[category] = dict(zip(model_features, normalized_weights))

    # --- Utility functions ---
    def get_lat_lon_from_postcode(postcode):
        url = f"https://api.postcodes.io/postcodes/{postcode}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            result = data.get("result")
            if result:
                return result["latitude"], result["longitude"]
        return 51.5074, -0.1278  # Default: London

    def predict_yield_for_crop(crop_name, baseline_yield, crops, weekly_env):
        crop_row = crops[crops['COMNAME'].str.split(',').str[0].str.strip().str.lower() == crop_name.lower()]
        if crop_row.empty or weekly_env.empty:
            return baseline_yield

        crop_row = crop_row.iloc[0]
        yield_category = crop_row.get("YIELDCAT", "Low")
        model_weights = model_weights_map.get(yield_category, model_weights_map["Low"])
        crop_factors = {feat: crop_row.get(feat, None) for feat in model_weights.keys()}

        total_score = 0
        total_weight = 0

        for _, week in weekly_env.iterrows():
            weighted_sum = 0
            weight_sum = 0

            for feat, weight in model_weights.items():
                if feat in ["TMIN", "TMAX"]:
                    val = week.get("temp", None)
                elif feat in ["RMIN", "RMAX"]:
                    val = week.get("rain", None)
                else:
                    val = crop_factors.get(feat, None)

                if val is None or pd.isna(val):
                    continue

                min_val, max_val = feature_bounds.get(feat, (0, 1))
                norm = max(0, min(1, (val - min_val) / (max_val - min_val)))

                weighted_sum += norm * weight
                weight_sum += abs(weight)

            week_score = weighted_sum / weight_sum if weight_sum > 0 else 0
            total_score += week_score
            total_weight += 1

        avg_score = total_score / total_weight if total_weight > 0 else 0
        predicted_yield = baseline_yield * (0.5 + 0.5 * avg_score)
        return predicted_yield
    
    # Ensure columns exist
    for col in ["Old Estimate", "Difference"]:
        if col not in crop_df.columns:
            crop_df[col] = "N/A"
    
    today = datetime.today().date()
    updated = False
    
    for idx, row in crop_df.iterrows():
        try:
            last_update = datetime.strptime(str(row["Last Update"]), "%Y-%m-%d").date()
        except Exception:
            continue

        days_since_update = (today - last_update).days
        if days_since_update >= 7:
            try:
                baseline_yield = float(str(row["Estimated Yield"]).replace("Kg", "").strip())
            except Exception:
                continue

            postcode = row.get("Postcode", None) if "Postcode" in row else None
            if postcode and isinstance(postcode, str) and postcode.strip():
                latitude, longitude = get_lat_lon_from_postcode(postcode.strip())
            else:
                latitude, longitude = 51.5074, -0.1278  # Default: London

            end_date = today.strftime("%Y-%m-%d")
            start_date = (today - timedelta(days=6)).strftime("%Y-%m-%d")
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date,
                "end_date": end_date,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "Europe/London"
            }

            response = requests.get(url, params=params)
            data = response.json()

            if "daily" in data:
                temps = [
                    (tmax + tmin) / 2
                    for tmax, tmin in zip(data["daily"]["temperature_2m_max"], data["daily"]["temperature_2m_min"])
                    if tmax is not None and tmin is not None
                ]
                rains = [r for r in data["daily"]["precipitation_sum"] if r is not None]

                if temps and rains:
                    weekly_env = pd.DataFrame({'temp': temps, 'rain': rains})
                else:
                    weekly_env = pd.DataFrame({'temp': [20]*7, 'rain': [50]*7})  # fallback
            else:
                weekly_env = pd.DataFrame({'temp': [20]*7, 'rain': [50]*7})  # fallback

            predicted_yield = predict_yield_for_crop(row["Crop"], baseline_yield, crops, weekly_env)
            old_estimate = row["Estimated Yield"]
            crop_df.at[idx, "Old Estimate"] = old_estimate
            crop_df.at[idx, "Estimated Yield"] = str(round(predicted_yield, 2)) + "Kg"

            try:
                diff = float(predicted_yield) - baseline_yield
            except Exception:
                diff = "N/A"

            crop_df.at[idx, "Difference"] = round(diff, 2) if diff != "N/A" else "N/A"
            crop_df.at[idx, "Last Update"] = today.strftime("%Y-%m-%d")
            updated = True

    
    if updated:
        crop_df.to_csv(DATA_FILE, index=False)

    # Use st.form() to create a form context
    with st.form(key='delete_form'):
       col1, col2 = st.columns(2)
    with col1:
        manual_update = st.form_submit_button("Manual Update Yields")
    with col2:
        delete = st.form_submit_button("Delete", type="primary")
    if manual_update:
        # Run the yield update logic regardless of date
        updated = False
        for idx, row in crop_df.iterrows():
            try:
                baseline_yield = float(str(row["Estimated Yield"]).replace("Kg", "").strip())
            except Exception:
                continue

            postcode = row.get("Postcode", None) if "Postcode" in row else None
            if postcode and isinstance(postcode, str) and postcode.strip():
                latitude, longitude = get_lat_lon_from_postcode(postcode.strip())
            else:
                latitude, longitude = 51.5074, -0.1278  # Default: London

            end_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
            start_date = (today - timedelta(days=6)).strftime("%Y-%m-%d")
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date,
                "end_date": end_date,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "Europe/London"
            }
            response = requests.get(url, params=params)
            data = response.json()
            if "daily" in data:
                temps = [
                    (tmax + tmin) / 2
                    for tmax, tmin in zip(data["daily"]["temperature_2m_max"], data["daily"]["temperature_2m_min"])
                    if tmax is not None and tmin is not None
                ]
                rains = [
                    r for r in data["daily"]["precipitation_sum"]
                    if r is not None
                ]
                temps = temps[-7:]
                rains = rains[-7:]
                weekly_env = pd.DataFrame({
                    'temp': temps,
                    'rain': rains
                })
            else:
                weekly_env = pd.DataFrame({
                    'temp': [20]*7,
                    'rain': [50]*7
                })
            predicted_yield = predict_yield_for_crop(row["Crop"], baseline_yield, crops, weekly_env)
            old_estimate = row["Estimated Yield"]
            crop_df.at[idx, "Old Estimate"] = old_estimate
            crop_df.at[idx, "Estimated Yield"] = str(round(predicted_yield, 2)) + "Kg"
            try:
                diff = float(str(predicted_yield)) - float(str(baseline_yield))
            except Exception:
                diff = "N/A"
            crop_df.at[idx, "Difference"] = round(diff, 2) if diff != "N/A" else "N/A"
            crop_df.at[idx, "Last Update"] = today.strftime("%Y-%m-%d")
            updated = True
        if updated:
            crop_df.to_csv(DATA_FILE, index=False)
            st.success("Manual yield update complete!")
            st.rerun()

    if delete:
        selected_indices = cropsplanted.selection.rows
        crop_df = crop_df.drop(index=selected_indices).reset_index(drop=True)
        crop_df.to_csv(DATA_FILE, index=False)
        st.success(f"Deleted {len(selected_indices)} record(s)")
        st.rerun()

def run_plant_prices():
    st.header("💰 Plant Prices")

    # --- Load data ---
    crop_df = pd.read_csv("crop_records.csv")
    eu_df = pd.read_excel("CropPrices2.xlsx")

    # --- Normalize and fuzzy match crops ---
    crop_names = [c.strip().lower() for c in crop_df["Crop"].dropna()]
    eu_products = [p.strip().lower() for p in eu_df["Product Description"].dropna().unique()]

    matched_products = {}
    for crop in crop_names:
        match, score, _ = process.extractOne(crop, eu_products)
        original_match = next((p for p in eu_df["Product Description"].unique() if p.strip().lower() == match), None)
        matched_products[crop] = original_match

    # --- Static exchange rates ---
    exchange_rates = {
        "EUR": 1.00,
        "USD": 1.14,     # EUR to USD
        "GBP": 0.85,     # EUR to GBP
        "JPY": 160.00,   # EUR to JPY
        "INR": 91.00     # EUR to INR
    }


    selected_crop = st.selectbox("Choose a crop:", crop_names)
    selected_currency = st.selectbox("Convert to currency:", list(exchange_rates.keys()))
    rate = exchange_rates[selected_currency]

    # --- Display results ---
    if selected_crop:
        matched_product = matched_products.get(selected_crop)
        if matched_product:
            filtered_df = eu_df[eu_df["Product Description"] == matched_product].copy()
            avg_price_eur = filtered_df["Market Price"].mean()
            converted_price = avg_price_eur * rate
            yield_row = crop_df[crop_df["Crop"].str.lower() == selected_crop.lower()]

            # Extract the yield value safely
            if not yield_row.empty:
                raw_yield = str(yield_row["Estimated Yield"].values[0])  # Convert to string
                clean_yield = raw_yield.replace("Kg", "").strip()        # Remove 'kg' and whitespace
                yield1 = float(clean_yield)                              # Convert to float for calculation
            else:
                st.warning(f"No yield data found for crop: {selected_crop}")
                yield1 = 0

            # Filter product row
            filtered_product = eu_df[eu_df["Product Description"].str.lower() == matched_product.lower()]

            # Extract unit safely
            if not filtered_product.empty:
                unit = str(filtered_product["Unit"].values[0])
            else:
                st.warning(f"No unit found for product: {matched_product}")
                unit = "unknown"

            # Calculate estimated value
            if "100" in unit:
                estimated_value = (yield1 / 100) * converted_price
                unit1 = "100 KG"
            else:
                estimated_value = (yield1 / 1000) * converted_price
                unit1 = "1 tonne"
                        

            st.metric(
                label=f"Average price for {unit1} of {matched_product} in {selected_currency}",
                value=f"{converted_price:.2f} {selected_currency}"
            )

            st.metric(
                label=f"Estimated value of your yield ({yield1} Kg) in {selected_currency}",
                value=f"{estimated_value:.2f} {selected_currency}"
            )

            st.caption(f"Using static rate: 1 EUR = {rate:.2f} {selected_currency}")

            # --- Prepare data for line chart ---
            filtered_df["Year/Month"] = pd.to_datetime(filtered_df["Year/Month"], errors="coerce")
            filtered_df.sort_values("Year/Month", inplace=True)
            chart_df = filtered_df[["Year/Month", "Market Price"]].dropna()
            chart_df.set_index("Year/Month", inplace=True)

            # --- Plot line chart ---
            st.line_chart(chart_df)
        else:
            st.warning("No matching product found in EU dataset.")


def run_crop_database():
    categories = ['fruits', 'vegetables', 'cereals']

    def load_and_prepare_data():
        crops_df = pd.read_csv('EcoCrop_DB.csv', encoding='latin1')

        # Filter by category keywords
        crops_df = crops_df[
            crops_df['CAT'].apply(
                lambda x: any(keyword in str(x).lower() for keyword in categories)
            )
        ]

        # Clean crop names
        crops_df['COMNAME'] = crops_df['COMNAME'].apply(
            lambda x: x.split(',')[0].strip() if isinstance(x, str) else 'Unknown'
        )

        # Define features
        core_features = ['TMIN', 'TMAX', 'RMIN', 'RMAX', 'PHMIN', 'PHMAX']
        text_features = ['ScientificName']
        categorical_features = ['CLIZ', 'CAT', 'PHYS', 'LIFO']

        # Convert core features to numeric
        for col in core_features:
            crops_df[col] = pd.to_numeric(crops_df[col], errors='coerce')

        # Fill missing categorical values
        for col in categorical_features + text_features:
            crops_df[col] = crops_df[col].fillna('Unknown')

        # Select and rename columns
        display_columns = ['COMNAME'] + text_features + core_features + categorical_features
        explorer_df = crops_df[display_columns].copy()

        explorer_df.columns = [
            'Crop Name', 'Scientific Name', 'Min Temp (°C)', 'Max Temp (°C)', 'Min Rainfall (mm)',
            'Max Rainfall (mm)', 'Min Soil pH', 'Max Soil pH', 'Climate Zone',
            'Category', 'Physiology', 'Life Form'
    ]

        return explorer_df.dropna(subset=['Crop Name']).reset_index(drop=True)

    # Load data
    df_explorer = load_and_prepare_data()

    # Extract unique climate zones for filtering
    all_climates = df_explorer['Climate Zone'].dropna().apply(lambda x: [zone.strip().lower() for zone in str(x).split(',')])
    unique_climates = sorted(set(zone for sublist in all_climates for zone in sublist))

    # Streamlit UI
    st.header("Crop Database Explorer")

    with st.form("explorer_filter_form"):
        st.subheader("Filter Options")

        col1, col2 = st.columns(2)

        with col1:
            selected_zones = st.multiselect(
                "Filter by Climate Zone (CLIZ)",
                options=unique_climates,
                default=[]
            )

        with col2:
            selected_categories = st.multiselect(
                "Filter by Category (CAT)",
                options=categories,
                default=[]
            )

        min_val, max_val = float(df_explorer['Max Temp (°C)'].min()), float(df_explorer['Max Temp (°C)'].max())
        temp_range = st.slider(
            "Filter by Max Temperature (°C)",
            min_value=min_val,
            max_value=max_val,
            value=(min_val, max_val)
        )

        submitted = st.form_submit_button("Apply Filters", type="primary")

    filtered_df = df_explorer

    if submitted:
        min_temp, max_temp = temp_range
        
        if selected_zones:
            filtered_df = filtered_df[
                filtered_df['Climate Zone'].apply(
                    lambda x: any(zone in str(x).lower() for zone in selected_zones)
                )
            ]
        if selected_categories:
            filtered_df = filtered_df[
                filtered_df['Category'].apply(
                    lambda x: any(keyword.lower() in str(x).lower() for keyword in selected_categories)
                )
            ]
        
        filtered_df = filtered_df[
            (filtered_df['Max Temp (°C)'] >= min_temp) &
            (filtered_df['Max Temp (°C)'] <= max_temp)
        ]
    filtered_df = filtered_df.sort_values(by='Crop Name')
    st.write(f"#### Displaying **{len(filtered_df)}** of **{len(df_explorer)}** crops")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    st.subheader("Detailed Crop View")
    filtered_df['Display Name'] = filtered_df.apply(
        lambda row: row['Scientific Name'] if row['Crop Name'].lower() == 'unknown' else row['Crop Name'],
        axis=1
    )
    if not filtered_df.empty:
        selected_display_name = st.selectbox(
            "Select a crop from the table above to see its detailed growing conditions:",
            options=filtered_df['Display Name']
        )
        
        crop_details = filtered_df[
            filtered_df['Display Name'] == selected_display_name
        ].iloc[0]
        st.write(f"##### Scientific Name: **{crop_details['Scientific Name']}**")

        st.write(f"##### Optimal Conditions for: **{crop_details['Crop Name']}**")

        col1, col2, col3 = st.columns(3)
        col1.metric("Temperature Range", f"{crop_details['Min Temp (°C)']} – {crop_details['Max Temp (°C)']} °C")
        col2.metric("Annual Rainfall", f"{crop_details['Min Rainfall (mm)']} – {crop_details['Max Rainfall (mm)']} mm")
        col3.metric("Soil pH Range", f"{crop_details['Min Soil pH']} – {crop_details['Max Soil pH']}")

        st.info(f"""
        - **Climate Zone (CLIZ):** {crop_details['Climate Zone']}
        - **Category (CAT):** {crop_details['Category']}
        - **Physiology (PHYS):** {crop_details['Physiology']}
        - **Life Form (LIFO):** {crop_details['Life Form']}
        """)
    else:
        st.warning("No crops match the current filters. Please adjust your selection")


if "selected_tab" not in st.session_state:
    st.session_state.selected_tab = "Plant Finder"

# Create tab-like buttons
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🌱 Plant Finder"):
        st.session_state.selected_tab = "Plant Finder"

with col2:
    if st.button("📈 Plant Yields"):
        st.session_state.selected_tab = "Plant Yields"

with col3:
    if st.button("💰 Plant Prices"):
        st.session_state.selected_tab = "Plant Prices"

with col4:
    if st.button("📚 Crop Database"):
        st.session_state.selected_tab = "Crop Database"

# Run logic based on selected tab
if st.session_state.selected_tab == "Plant Finder":
    run_plant_finder()

elif st.session_state.selected_tab == "Plant Yields":
    run_plant_yields()

elif st.session_state.selected_tab == "Plant Prices":
    run_plant_prices()

elif st.session_state.selected_tab == "Crop Database":
    run_crop_database()