"""
ARKTECH - Sample Data Generator
--------------------------------
Creates a realistic synthetic training dataset so you can test the ENTIRE
pipeline (training -> backend -> dashboard) today, without waiting on
real Google Earth Engine exports.

Once you have your real arktech_gee_data.csv from Earth Engine, you will
run clean_and_label.py on that instead, and this file becomes unnecessary.

Run with:
    python generate_sample_data.py
"""

import numpy as np
import pandas as pd

np.random.seed(42)

STAGES = ["sowing", "vegetative", "flowering"]
N_FIELDS = 30
N_DATES = 5

rows = []
field_id_counter = 1

for field_num in range(N_FIELDS):
    field_id = f"F{field_id_counter:03d}"
    field_id_counter += 1

    lat = 12.45 + np.random.uniform(-0.15, 0.15)
    lon = 76.90 + np.random.uniform(-0.15, 0.15)

    # each field has an underlying "health tendency" so data isn't pure noise
    field_health = np.random.choice(["good", "average", "poor"], p=[0.4, 0.35, 0.25])

    for date_num in range(N_DATES):
        stage = STAGES[min(date_num // 2, len(STAGES) - 1)]
        date = pd.Timestamp("2026-06-01") + pd.Timedelta(days=date_num * 12)

        # base values depend on field health tendency
        if field_health == "good":
            ndvi_base, moisture_base = 0.65, 0.55
        elif field_health == "average":
            ndvi_base, moisture_base = 0.45, 0.38
        else:
            ndvi_base, moisture_base = 0.25, 0.20

        # stage adjustment (sowing naturally has lower NDVI)
        stage_adj = {"sowing": -0.15, "vegetative": 0.10, "flowering": 0.05}[stage]

        ndvi = np.clip(ndvi_base + stage_adj + np.random.normal(0, 0.05), 0.05, 0.95)
        ndwi = np.clip(ndvi * 0.4 + np.random.normal(0, 0.05), -0.3, 0.5)
        vv = -14 + np.random.normal(0, 2)
        vh = -21 + np.random.normal(0, 2)
        vv_vh_ratio = round(vv / vh, 3)
        soil_moisture_index = np.clip(moisture_base + np.random.normal(0, 0.06), 0.02, 0.9)
        rainfall = max(0, np.random.exponential(8) if field_health != "poor" else np.random.exponential(2))
        lst = np.random.normal(31, 4) + (5 if field_health == "poor" else 0)

        # ----- Stage-aware proxy labeling logic -----
        if stage == "sowing":
            healthy_ndvi_min = 0.20
        elif stage == "vegetative":
            healthy_ndvi_min = 0.50
        else:  # flowering
            healthy_ndvi_min = 0.45

        if ndvi >= healthy_ndvi_min and soil_moisture_index >= 0.50:
            label = 0  # Healthy
        elif ndvi < 0.30 and soil_moisture_index < 0.25:
            label = 2  # Severe
        elif ndvi < healthy_ndvi_min or soil_moisture_index < 0.40:
            label = 1  # Moderate
        else:
            label = 0

        rows.append({
            "field_id": field_id,
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "date": date.strftime("%Y-%m-%d"),
            "crop_stage": stage,
            "ndvi": round(ndvi, 3),
            "ndwi": round(ndwi, 3),
            "vv": round(vv, 2),
            "vh": round(vh, 2),
            "vv_vh_ratio": vv_vh_ratio,
            "soil_moisture_index": round(soil_moisture_index, 3),
            "rainfall": round(rainfall, 1),
            "lst": round(lst, 1),
            "stress_label": label,
        })

df = pd.DataFrame(rows)
df.to_csv("../data/processed/arktech_training_data.csv", index=False)

print(f"Generated {len(df)} rows.")
print(df["stress_label"].value_counts().rename({0: "Healthy", 1: "Moderate", 2: "Severe"}))
print("\nSaved to: data/processed/arktech_training_data.csv")
