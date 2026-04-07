import json
import pickle


import pandas as pd
from sklearn.ensemble        import RandomForestRegressor
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.linear_model    import LinearRegression, Ridge
from sklearn.metrics         import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

# Constants (from the notebook exactly) 
CANDIDATE_FEATURES = [
    "station_id", "hour", "month", "capacity",
    "avg_temp", "avg_humidity", "avg_pressure",
]
TARGET       = "num_bikes_available"
RANDOM_STATE = 42

# Load data 
df_raw = pd.read_csv("../notebooks/final_merged_data.csv", low_memory=False)
print(f"Loaded {len(df_raw):,} rows, {df_raw['station_id'].nunique()} stations")

# Feature engineering 
df = df_raw.copy()
df["avg_temp"]     = (df["max_air_temperature_celsius"]   + df["min_air_temperature_celsius"])   / 2
df["avg_humidity"] = (df["max_relative_humidity_percent"] + df["min_relative_humidity_percent"]) / 2
df["avg_pressure"] = (df["max_barometric_pressure_hpa"]   + df["min_barometric_pressure_hpa"])   / 2

keep = CANDIDATE_FEATURES + [TARGET]
df   = df[keep].dropna().reset_index(drop=True)

# Feature selection (SelectKBest, k=5) 
selector = SelectKBest(f_regression, k=5)
selector.fit(df[CANDIDATE_FEATURES], df[TARGET])

scores_df = pd.DataFrame({
    "feature" : CANDIDATE_FEATURES,
    "f_score" : selector.scores_,
    "selected": selector.get_support(),
}).sort_values("f_score", ascending=False)
print("\nSelectKBest results:")
print(scores_df.to_string(index=False))

# Forcing station_id into the final set regardless of F-score
selected = list(dict.fromkeys(
    ["station_id"] + scores_df[scores_df["selected"]]["feature"].tolist()
))
print(f"\nSelected features: {selected}")

# Train / test split
X = df[selected]
y = df[TARGET]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=RANDOM_STATE
)
print(f"\nTrain: {len(X_train):,}  |  Test: {len(X_test):,}")

# Train and compare models 
models = {
    "LinearRegression": LinearRegression(),
    "Ridge"           : Ridge(alpha=1.0),
    "RandomForest"    : RandomForestRegressor(n_estimators=100, random_state=RANDOM_STATE, n_jobs=True),
}

results = {}
print(f"\n{'Algorithm':<22}  {'MAE':>8}  {'R²':>8}")
print("-" * 44)

for name, model in models.items():
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    mae  = mean_absolute_error(y_test, pred)
    r2   = r2_score(y_test, pred)
    results[name] = {"model": model, "mae": mae, "r2": r2}
    print(f"{name:<22}  {mae:>8.4f}  {r2:>8.4f}")

# Pick best model (lowest MAE) 
best_name = min(results, key=lambda k: results[k]["mae"])
best      = results[best_name]
print(f"\nBest model: {best_name}  (MAE={best['mae']:.4f}, R²={best['r2']:.4f})")

# Save model 
with open("bike_model.pkl", "wb") as f:
    pickle.dump(best["model"], f)

with open("model_meta.json", "w") as f:
    json.dump({
        "best_model": best_name,
        "features"  : selected,
        "mae"       : round(best["mae"], 4),
        "r2"        : round(best["r2"],  4),
    }, f, indent=2)

print("\nbike_model.pkl  saved")
print("model_meta.json saved")

# Quick sanity check
with open("bike_model.pkl", "rb") as f:
    loaded = pickle.load(f)

sample = pd.DataFrame([{
    "station_id"  : 10,
    "capacity"    : 16,
    "hour"        : 9,
    "avg_humidity": 80.0,
    "avg_pressure": 1013.0,
    "avg_temp"    : 12.0,
}])[selected]

pred_bikes = max(0, round(float(loaded.predict(sample)[0])))
print(f"\nSanity check — Station 10 @ 09:00 → {pred_bikes} bikes predicted")
