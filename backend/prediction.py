import json
from pathlib import Path
from typing import Any


MODEL_DIR = Path(__file__).resolve().parents[1] / "model"
FEATURE_COLUMNS_PATH = MODEL_DIR / "feature_columns.json"
MODEL_PATH = MODEL_DIR / "stress_model.json"

LABELS = {
    0: "Healthy",
    1: "Moderate Water Stress",
    2: "Severe Water Stress",
}


def _load_feature_columns() -> list[str]:
    try:
        return json.loads(FEATURE_COLUMNS_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return [
            "ndvi",
            "ndwi",
            "vv",
            "vh",
            "vv_vh_ratio",
            "soil_moisture_index",
            "rainfall",
            "lst",
            "crop_stage_flowering",
            "crop_stage_sowing",
            "crop_stage_vegetative",
        ]


def _build_features(payload: dict[str, Any]) -> dict[str, float]:
    stage = str(payload.get("crop_stage", "vegetative")).lower()
    features = {}
    for column in _load_feature_columns():
        if column.startswith("crop_stage_"):
            features[column] = 1.0 if column == f"crop_stage_{stage}" else 0.0
        else:
            try:
                features[column] = float(payload.get(column, 0))
            except (TypeError, ValueError):
                features[column] = 0.0
    return features


def _heuristic_predict(payload: dict[str, Any]) -> dict[str, Any]:
    ndvi = float(payload.get("ndvi", 0.45))
    ndwi = float(payload.get("ndwi", 0.1))
    moisture_index = float(payload.get("soil_moisture_index", 0.4))
    sensor_moisture = float(payload.get("sensor_soil_moisture", moisture_index * 100))
    temperature = float(payload.get("sensor_temperature", payload.get("lst", 30)))
    rainfall = float(payload.get("rainfall", 0))

    score = 0
    if ndvi < 0.3:
        score += 2
    elif ndvi < 0.5:
        score += 1
    if ndwi < 0:
        score += 2
    elif ndwi < 0.12:
        score += 1
    if moisture_index < 0.25 or sensor_moisture < 22:
        score += 3
    elif moisture_index < 0.42 or sensor_moisture < 38:
        score += 1
    if temperature >= 37 and rainfall < 5:
        score += 1

    if score >= 5:
        predicted_class = 2
        confidence = 86
    elif score >= 2:
        predicted_class = 1
        confidence = 76
    else:
        predicted_class = 0
        confidence = 82

    return {
        "ai_predicted_class": predicted_class,
        "condition": LABELS[predicted_class],
        "confidence": confidence,
        "model_source": "heuristic-fallback",
    }


def _critical_sensor_override(payload: dict[str, Any]) -> dict[str, Any] | None:
    ndvi = float(payload.get("ndvi", 0.45))
    ndwi = float(payload.get("ndwi", 0.1))
    moisture_index = float(payload.get("soil_moisture_index", 0.4))
    sensor_moisture = float(payload.get("sensor_soil_moisture", moisture_index * 100))
    temperature = float(payload.get("sensor_temperature", payload.get("lst", 30)))
    rainfall = float(payload.get("rainfall", 0))

    extreme_water_stress = (
        sensor_moisture <= 20
        and moisture_index <= 0.25
        and ndvi <= 0.32
        and ndwi <= 0
    )
    hot_dry_stress = sensor_moisture <= 25 and temperature >= 37 and rainfall <= 2
    if extreme_water_stress or hot_dry_stress:
        return {
            "ai_predicted_class": 2,
            "condition": LABELS[2],
            "confidence": 94,
            "model_source": "xgboost+sensor-safety-override",
        }
    return None


def predict_crop_stress(payload: dict[str, Any]) -> dict[str, Any]:
    override = _critical_sensor_override(payload)
    if override:
        return override

    features = _build_features(payload)
    try:
        import xgboost as xgb

        model = xgb.XGBClassifier()
        model.load_model(str(MODEL_PATH))
        ordered = [[features[column] for column in _load_feature_columns()]]
        probabilities = model.predict_proba(ordered)[0]
        predicted_class = int(max(range(len(probabilities)), key=lambda index: probabilities[index]))
        return {
            "ai_predicted_class": predicted_class,
            "condition": LABELS.get(predicted_class, "Unknown Stress"),
            "confidence": round(float(probabilities[predicted_class]) * 100, 2),
            "model_source": "xgboost",
        }
    except Exception:
        return _heuristic_predict(payload)
