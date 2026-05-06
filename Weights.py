import pandas as pd
import numpy as np
import re
from rapidfuzz import process, fuzz
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from sklearn.ensemble import StackingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb

# --- Fuzzy matching helpers ---
def clean_crop_name(name):
    return re.sub(r'[^\w\s]', '', str(name).lower().strip())

def find_best_match(name, choices):
    match, score, _ = process.extractOne(name, choices, scorer=fuzz.token_sort_ratio)
    return match if score >= 60 else None

# --- Load datasets ---
df = pd.read_csv(r'EcoCrop_DB.csv', encoding='latin1')
faostat_df = pd.read_csv(r'FAOSTAT_data_en_8-18-2025.csv', encoding='latin1')

# --- Clean crop names ---
faostat_df['CleanCrop'] = faostat_df['Item'].dropna().apply(clean_crop_name)
faostat_df['Value'] = pd.to_numeric(faostat_df['Value'], errors='coerce')
faostat_map = dict(zip(faostat_df['CleanCrop'], faostat_df['Value']))

def get_faostat_value(row):
    names = [n.strip() for n in str(row['COMNAME']).split(',')]
    for name in names:
        clean = clean_crop_name(name)
        match = find_best_match(clean, faostat_map.keys())
        if match:
            return faostat_map[match]
    return None

df['Value'] = df.apply(get_faostat_value, axis=1)

# --- Feature setup ---
features = ['TMIN', 'TMAX', 'RMIN', 'RMAX', 'PHMIN', 'PHMAX', 'PHOTO']
target = 'Value'

for col in features + [target]:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df['non_null_features'] = df[features].notna().sum(axis=1)
filtered = df[df['non_null_features'] >= 5].dropna(subset=[target])

for col in features:
    filtered[col] = filtered[col].fillna(filtered[col].median())

X = filtered[features]
y = filtered[target]

print(f"Training data shape after relaxed filtering: {X.shape}")
if len(filtered) == 0:
    print("No data available for training.")
    exit()

# --- Ensemble stacking setup ---
estimators = [
    ('xgb', xgb.XGBRegressor(objective='reg:squarederror')),
    ('rf', RandomForestRegressor(n_estimators=100)),
]
stack_model = StackingRegressor(
    estimators=estimators,
    final_estimator=LinearRegression()
)

# --- Train/test split and model training ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
stack_model.fit(X_train, y_train)

# --- Evaluation ---
y_pred = stack_model.predict(X_test)
rmse = mean_squared_error(y_test, y_pred) ** 0.5
print(f"Stacked RMSE: {rmse:.2f}")

# --- Feature importances from base models
xgb_model = stack_model.named_estimators_['xgb']
importances = xgb_model.feature_importances_
weights = dict(zip(features, importances))

print("Feature importances from XGBoost:")
for feature, weight in weights.items():
    print(f"{feature}: {weight:.4f}")

# --- Save weights
pd.DataFrame([weights]).to_csv("stacked_feature_weights.csv", index=False)
print("Saved stacked_feature_weights.csv")
