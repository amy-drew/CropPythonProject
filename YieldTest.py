import requests
import pandas as pd
import numpy as np
from datetime import datetime
from tensorflow.keras.models import load_model
import matplotlib.pyplot as plt

# --- Load weights from Keras model ---
model = load_model("crop_model_Low.h5")

# Find the first Dense layer with weights
dense_layer = next(layer for layer in model.layers if hasattr(layer, 'kernel'))
layer_weights = dense_layer.get_weights()[0]  # shape: (num_features, num_units)
feature_weights = layer_weights.mean(axis=1)  # average across neurons
normalized_weights = feature_weights / np.linalg.norm(feature_weights)

# Map to feature names (including new ones)
features = ['TMIN', 'TMAX', 'RMIN', 'RMAX', 'PHMIN', 'PHMAX', 'TOPMN', 'TOPMX', 'ROPMN', 'ROPMX']
weights = dict(zip(features, normalized_weights))

print("Loaded weights from .h5 model:")
for k, v in weights.items():
    print(f"{k}: {v:.4f}")

# --- Realistic bounds from EcoCrop ---
bounds = {
    'TMIN': (0, 40), 'TMAX': (0, 45),
    'RMIN': (0, 2000), 'RMAX': (0, 2000),
    'PHMIN': (4.0, 9.0), 'PHMAX': (4.0, 9.0),
    'TOPMN': (4.0, 9.0), 'TOPMX': (4.0, 9.0),
    'ROPMN': (0, 2000), 'ROPMX': (0, 2000)
}

# --- Fixed crop factors ---
crop_factors = {
    "PHMIN": 6.0,
    "PHMAX": 7.5,
    "TOPMN": 5.5,
    "TOPMX": 8.0,
    "ROPMN": 400,
    "ROPMX": 1200
}

baseline_yield = 8590.4

def normalize(value, min_val, max_val):
    return max(0, min(1, (value - min_val) / (max_val - min_val)))

# --- Fetch weather data ---
latitude = 52.823471
longitude = -0.038671
start_date = "2022-10-01"
end_date = "2023-07-01"
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

if "daily" not in data:
    print("No weather data found.")
    exit()

# --- Prepare DataFrame ---
df = pd.DataFrame({
    "date": data["daily"]["time"],
    "temp_max": data["daily"]["temperature_2m_max"],
    "temp_min": data["daily"]["temperature_2m_min"],
    "rain_mm": data["daily"]["precipitation_sum"]
})
df["date"] = pd.to_datetime(df["date"])

# --- Weekly aggregation ---
df.set_index("date", inplace=True)
weekly = df.resample("W").agg({
    "temp_min": "mean",
    "temp_max": "mean",
    "rain_mm": "sum"
}).reset_index()

annual_rainfall = weekly["rain_mm"].sum()
weekly["rain_annual"] = annual_rainfall

# --- Yield estimation ---
weekly_scores = []

for idx, row in weekly.iterrows():
    weighted_sum = 0
    total_weight = 0

    for feat, weight in weights.items():
        if feat not in bounds:
            continue

        # Get value from weather or fixed crop factors
        if feat == "TMIN":
            val = row["temp_min"]
        elif feat == "TMAX":
            val = row["temp_max"]
        elif feat in ["RMIN", "RMAX"]:
            val = row["rain_mm"]
        else:
            val = crop_factors.get(feat, np.nan)

        if pd.isna(val):
            continue

        try:
            norm = normalize(val, *bounds[feat])
            weighted_sum += norm * weight
            total_weight += weight
        except Exception as e:
            print(f"Skipping {feat} due to error: {e}")

    weighted_score = weighted_sum / total_weight if total_weight > 0 else 0
    estimated_yield = baseline_yield * (0.5 + 0.5 * weighted_score)

    weekly_scores.append({
        "week_start": row["date"].strftime("%Y-%m-%d"),
        "weighted_score": round(weighted_score, 3),
        "estimated_yield": round(estimated_yield, 2)
    })

# --- Output ---
print(f"\nBaseline yield: {baseline_yield:.2f} kg/ha")

if weekly_scores:
    print(f"Predicted yield after 2022–2023: {weekly_scores[-1]['estimated_yield']:.2f} kg/ha\n")
    for i, ws in enumerate(weekly_scores, 1):
        print(f"Week {i}: Weighted Score = {ws['weighted_score']:.3f}, Yield = {ws['estimated_yield']:.2f} kg/ha")
    print("...")
    print(f"\nFinal weighted score: {weekly_scores[-1]['weighted_score']:.3f}")
else:
    print("No weekly scores computed.")

# --- Plot ---
weeks = [ws['week_start'] for ws in weekly_scores]
yields = [ws['estimated_yield'] for ws in weekly_scores]

plt.figure(figsize=(12, 6))
plt.plot(weeks, yields, marker='o')
plt.xticks(rotation=45)
plt.title("Estimated Weekly Yield")
plt.xlabel("Week Start")
plt.ylabel("Yield (kg/ha)")
plt.grid(True)
plt.tight_layout()
plt.show()
