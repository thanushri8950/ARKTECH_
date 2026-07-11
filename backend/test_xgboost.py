import json
import xgboost as xgb
from prediction import _build_features, _load_feature_columns, MODEL_PATH

payload = {
    "field_id": "F003", "ndvi": 0.25, "ndwi": -0.08, "vv": -15.4, "vh": -22.1, "vv_vh_ratio": 0.69,
    "soil_moisture_index": 0.18, "rainfall": 0, "lst": 38, "crop_stage": "flowering",
    "crop_type": "Sugarcane", "latitude": 12.9716, "longitude": 77.5946, "leaf_wetness": 32,
    "sensor_soil_moisture": 16, "sensor_temperature": 38, "sensor_humidity": 40
}

features = _build_features(payload)
model = xgb.XGBClassifier()
model.load_model(str(MODEL_PATH))
ordered = [[features[column] for column in _load_feature_columns()]]
probabilities = model.predict_proba(ordered)[0]
predicted_class = int(max(range(len(probabilities)), key=lambda index: probabilities[index]))
print("With ndwi = -0.08:", predicted_class)

payload["ndwi"] = 0.08
features = _build_features(payload)
ordered = [[features[column] for column in _load_feature_columns()]]
probabilities = model.predict_proba(ordered)[0]
predicted_class = int(max(range(len(probabilities)), key=lambda index: probabilities[index]))
print("With ndwi = 0.08:", predicted_class)

