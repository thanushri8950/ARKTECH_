"""
ARKTECH - Model Training
-------------------------
Trains an XGBoost classifier to predict crop stress from satellite-derived
features. Reads data/processed/arktech_training_data.csv and saves:
  - stress_model.json      (the trained model)
  - feature_columns.json   (which columns the model expects, in order)
  - label_encoder.pkl      (not needed for this label scheme, kept for future use)

Run with:
    python train_xgboost.py
"""

import json
import os

import joblib
import matplotlib
matplotlib.use("Agg")  # so it works with no display / on a server
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

DATA_PATH = "../data/processed/arktech_training_data.csv"
OUTPUTS_DIR = "../outputs"
os.makedirs(OUTPUTS_DIR, exist_ok=True)

data = pd.read_csv(DATA_PATH)

base_features = [
    "ndvi", "ndwi", "vv", "vh", "vv_vh_ratio",
    "soil_moisture_index", "rainfall", "lst",
]

data = pd.get_dummies(data, columns=["crop_stage"])

feature_columns = [
    c for c in data.columns
    if c.startswith("crop_stage_") or c in base_features
]

X = data[feature_columns]
y = data["stress_label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)

model = XGBClassifier(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="multi:softprob",
    eval_metric="mlogloss",
    random_state=42,
)

model.fit(X_train, y_train)

predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)
print("Accuracy:", round(accuracy, 3))
print()
print(classification_report(
    y_test, predictions,
    target_names=["Healthy", "Moderate", "Severe"],
))

cm = confusion_matrix(y_test, predictions)
print("Confusion matrix:\n", cm)

# Save confusion matrix image
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Healthy", "Moderate", "Severe"])
disp.plot(cmap="Greens")
plt.title("ARKTECH - Confusion Matrix")
plt.savefig(f"{OUTPUTS_DIR}/confusion_matrix.png", bbox_inches="tight")
plt.close()

# Save feature importance image
importances = model.feature_importances_
plt.figure(figsize=(8, 5))
plt.barh(feature_columns, importances, color="#4C7A3D")
plt.xlabel("Importance")
plt.title("ARKTECH - Feature Importance")
plt.tight_layout()
plt.savefig(f"{OUTPUTS_DIR}/feature_importance.png", bbox_inches="tight")
plt.close()

# Save metrics
metrics = {
    "accuracy": round(float(accuracy), 4),
    "n_train": int(len(X_train)),
    "n_test": int(len(X_test)),
    "features": feature_columns,
}
with open(f"{OUTPUTS_DIR}/model_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)

# Save model + feature list (these are what the backend loads)
model.save_model("stress_model.json")
with open("feature_columns.json", "w") as f:
    json.dump(feature_columns, f)

joblib.dump({"classes": [0, 1, 2], "labels": ["Healthy", "Moderate Water Stress", "Severe Water Stress"]}, "label_encoder.pkl")

print("\nSaved model files: stress_model.json, feature_columns.json, label_encoder.pkl")
print(f"Saved charts + metrics to: {OUTPUTS_DIR}/")
