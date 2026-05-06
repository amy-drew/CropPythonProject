import pandas as pd
import numpy as np
import re
from rapidfuzz import process, fuzz
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import Input, Dense, Dropout, Add
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.losses import Huber
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

# --- Load Data ---
df = pd.read_csv('EcoCrop_DB.csv', encoding='latin1')
faostat_df = pd.read_csv('FAOSTAT_data_en_8-18-2025.csv', encoding='latin1')

column_types = df.dtypes

# Classify columns
numeric_cols = column_types[column_types != 'object'].index.tolist()
text_cols = column_types[column_types == 'object'].index.tolist()

# --- Clean Crop Names ---
def clean_crop_name(name):
    return re.sub(r'[^\w\s]', '', str(name).lower().strip())

faostat_df['CleanCrop'] = faostat_df['Item'].dropna().apply(clean_crop_name)
faostat_df['Value'] = pd.to_numeric(faostat_df['Value'], errors='coerce')
faostat_map = dict(zip(faostat_df['CleanCrop'], faostat_df['Value']))

df['CleanCrop'] = df['COMNAME'].dropna().apply(clean_crop_name)
phmax_map = dict(zip(df['CleanCrop'], df['PHMAX']))

# --- Fuzzy Matching ---
def find_best_match(name, choices):
    match, score, _ = process.extractOne(name, choices, scorer=fuzz.token_sort_ratio)
    return match if score >= 60 else None

def get_faostat_value(row):
    names = [n.strip() for n in str(row['COMNAME']).split(',')]
    for name in names:
        clean = clean_crop_name(name)
        match = find_best_match(clean, faostat_map.keys())
        if match:
            return faostat_map[match]
    return None

df['Value'] = df.apply(get_faostat_value, axis=1)

def get_phmax_value(row):
    names = [n.strip() for n in str(row['COMNAME']).split(',')]
    for name in names:
        clean = clean_crop_name(name)
        match = find_best_match(clean, phmax_map.keys())
        if match:
            return phmax_map[match]
    return np.nan

df['PHMAX'] = df['PHMAX'].fillna(df.apply(get_phmax_value, axis=1))

# --- Feature Enrichment ---
core_features = ['TMIN', 'TMAX', 'RMIN', 'RMAX', 'PHMIN', 'PHMAX','TOPMN','TOPMX', 'ROPMN','ROPMX']
extra_low = ['SAL', 'DRA', 'ABITOL', 'ABISUS']
extra_medium = ['PHOPMN', 'PHOPMX', 'CLIZ', 'CAT']
extra_high = ['PHYS', 'LIFO', 'LISPA']

for col in core_features + extra_low + extra_medium + extra_high + ['Value']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df[['CLIZ', 'CAT']] = df[['CLIZ', 'CAT']].fillna('Unknown')
df_encoded = pd.get_dummies(df[['CLIZ', 'CAT']], prefix=['CLIZ', 'CAT'])

df['non_null_features'] = df[core_features].notna().sum(axis=1)
filtered = df[df['non_null_features'] >= 5].dropna(subset=['Value'])

for col in core_features + extra_low + extra_medium + extra_high:
    if pd.api.types.is_numeric_dtype(filtered[col]):
        filtered[col] = filtered[col].fillna(filtered[col].median())

filtered['CLIZ'] = filtered['CLIZ'].fillna('Unknown')
filtered['CAT'] = filtered['CAT'].fillna('Unknown')
filtered = pd.get_dummies(filtered, columns=['CLIZ', 'CAT'], dummy_na=False)

X_encoded = df_encoded.loc[filtered.index]

# --- Categorize Yield ---
def categorize_yield(value):
    if value < 10000:
        return 'Low'
    elif value <= 30000:
        return 'Medium'
    else:
        return 'High'

filtered['YieldCategory'] = filtered['Value'].apply(categorize_yield)

# --- Model Builder ---
def build_model(category, input_dim):
    inputs = Input(shape=(input_dim,))
    if category == 'Low':
        x = Dense(128, activation='relu')(inputs)
        x = Dropout(0.5)(x)
        x = Dense(64, activation='relu')(x)
    elif category == 'Medium':
        x1 = Dense(128, activation='relu')(inputs)
        x2 = Dense(128, activation='relu')(x1)
        x = Add()([x1, x2])
    else:
        x = Dense(256, activation='relu')(inputs)
        x = Dense(128, activation='relu')(x)
        x = Dense(64, activation='relu')(x)
    output = Dense(1)(x)
    return Model(inputs, output)

# --- Training Loop ---
fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=True)

model_registry = {}
scaler_registry = {}
feature_registry = {}
encoder_registry = {}

for i, category in enumerate(['Low', 'Medium', 'High']):
    subset = filtered[filtered['YieldCategory'] == category]
    if len(subset) < 20:
        axes[i].set_title(f"{category} Yield")
        axes[i].text(0.5, 0.5, "Not enough data", ha='center', va='center')
        axes[i].axis('off')
        continue

    if category == 'Low':
        extra = extra_low
    elif category == 'Medium':
        extra = extra_medium
    else:
        extra = extra_high

    feature_set = core_features + extra
    available_features = [col for col in core_features + extra if col in subset.columns and not subset[col].isna().all()]
    X = pd.concat([subset[available_features], X_encoded.loc[subset.index]], axis=1)

    y = subset['Value'].values

    scaler_X = StandardScaler()
    scaler_y = StandardScaler()
    X_scaled = scaler_X.fit_transform(X.select_dtypes(include=[np.number]))
    y_scaled = scaler_y.fit_transform(y.reshape(-1, 1))
    X_numeric = X.select_dtypes(include=[np.number]).columns.tolist()
    X_categorical = X.select_dtypes(include=['object', 'category']).columns.tolist()
    # X = X.dropna(axis=1, how='all')
    preprocessor = ColumnTransformer(transformers=[
        ("num", Pipeline([
            ("imputer", SimpleImputer(strategy="mean")),
            ("scaler", StandardScaler())
        ]), X_numeric),
        
        ("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore"))
        ]), X_categorical)
    ])

    # Apply preprocessing
    X_preprocessed = preprocessor.fit_transform(X)
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_scaled, test_size=0.2, random_state=42)
    print("X_train contains NaNs:", np.isnan(X_train).any())
    print("y_train contains NaNs:", np.isnan(y_train).any())


    model = build_model(category, X_train.shape[1])
    model.compile(optimizer=Adam(0.001), loss=Huber())
    model.fit(X_train, y_train, epochs=100, batch_size=16, verbose=0)
    model.save(f'crop_model_{category}.h5')

    y_pred = scaler_y.inverse_transform(model.predict(X_test))
    y_test_inv = scaler_y.inverse_transform(y_test)

    rmse = np.sqrt(mean_squared_error(y_test_inv, y_pred))
    mae = mean_absolute_error(y_test_inv, y_pred)

    axes[i].scatter(y_test_inv, y_pred, alpha=0.6)
    axes[i].plot([min(y_test_inv), max(y_test_inv)], [min(y_test_inv), max(y_test_inv)], 'r--')
    axes[i].set_title(f"{category} Yield\nRMSE: {rmse:.1f}, MAE: {mae:.1f}")
    axes[i].set_xlabel("Actual Yield")
    axes[i].set_ylabel("Predicted Yield")
    axes[i].grid(True)
    
    for i, layer in enumerate(model.layers):
        if hasattr(layer, 'get_weights'):
            weights = layer.get_weights()
            for j, w in enumerate(weights):
                if np.isnan(w).any():
                    print(f"Layer {i} ({layer.name}) - weight set {j} contains NaNs")
                else:
                    print(f"Layer {i} ({layer.name}) - weight set {j} OK")


    model_registry[category] = model
    scaler_registry[category] = (scaler_X, scaler_y)
    feature_registry[category] = X.columns.tolist()
    encoder_registry[category] = X_encoded[X_encoded.columns.intersection(X.columns)]

plt.tight_layout()
plt.show()

# --- Heuristic Zone Classifier ---
def classify_zone_from_features(row):
    if row['PHMAX'] < 6.5 or row['TMAX'] < 20:
        return 'Low'
    elif row['PHMAX'] <= 7.5 and row['TMAX'] <= 28:
        return 'Medium'
    else:
        return 'High'

# --- Dynamic Prediction ---
def predict_dynamic(input_row):
    zone = classify_zone_from_features(input_row)
    model = model_registry[zone]
    scaler_X, scaler_y = scaler_registry[zone]
    feature_set = feature_registry[zone]
    encoder = encoder_registry[zone]

    row_df = pd.DataFrame([input_row])
    row_df[['CLIZ', 'CAT']] = row_df[['CLIZ', 'CAT']].fillna('Unknown')
    row_encoded = pd.get_dummies(row_df[['CLIZ', 'CAT']], prefix=['CLIZ', 'CAT'])

    for col in encoder.columns:
        if col not in row_encoded.columns:
            row_encoded[col] = 0
    row_encoded = row_encoded[encoder.columns]

    X_input = pd.concat([row_df[feature_set[:len(feature_set)-len(encoder.columns)]], row_encoded], axis=1)
    X_scaled = scaler_X.transform(X_input.select_dtypes(include=[np.number]))
    y_pred_scaled = model.predict(X_scaled)
    return scaler_y.inverse_transform(y_pred_scaled)[0][0]