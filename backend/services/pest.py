from datetime import datetime, timezone
from typing import Any

from utils.cache import cache


RISK_SCORE_LEVELS = [(8, "CRITICAL"), (5, "HIGH"), (3, "MEDIUM"), (0, "LOW")]


def _risk_from_score(score: int) -> str:
    for minimum, level in RISK_SCORE_LEVELS:
        if score >= minimum:
            return level
    return "LOW"


def predict_pest_risk(payload: dict[str, Any], weather: dict[str, Any]) -> dict[str, Any]:
    crop_type = str(payload.get("crop_type") or "Rice").strip().lower()
    stage = str(payload.get("crop_stage") or "vegetative").strip().lower()
    current = weather.get("current", {})

    temperature = float(payload.get("sensor_temperature") or current.get("temperature_c") or payload.get("lst") or 30)
    humidity = float(payload.get("sensor_humidity") or current.get("humidity_percent") or 60)
    rainfall = float(payload.get("rainfall") or current.get("rainfall_mm") or 0)
    soil_moisture = float(payload.get("sensor_soil_moisture") or 50)
    leaf_wetness = float(payload.get("leaf_wetness") or min(100, humidity * 0.75 + rainfall))

    score = 0
    reasons = []
    pests = []
    actions = []

    if humidity >= 80 and temperature >= 27 and leaf_wetness >= 65:
        score += 4
        reasons.append("High humidity, warm temperature, and leaf wetness increase fungal infection risk.")
        pests.extend(["Rice Blast", "Brown Spot"] if crop_type == "rice" else ["Red Rot"])
        actions.append("Inspect leaves and stems early in the morning; remove infected residue if symptoms appear.")

    if rainfall >= 30:
        score -= 1
        reasons.append("Heavy rain can temporarily reduce active pest movement.")
        actions.append("Avoid spraying during rain; reassess after the crop canopy dries.")

    if temperature >= 34 and humidity <= 55:
        score += 3
        reasons.append("Hot and dry conditions increase borer activity.")
        pests.extend(["Stem Borer"] if crop_type == "rice" else ["Early Shoot Borer", "Top Borer"])
        actions.append("Check field borders and young shoots for bore holes or dead hearts.")

    if stage in {"sowing", "vegetative"} and soil_moisture < 35:
        score += 2
        reasons.append("Low soil moisture during early growth weakens crop resistance.")
        actions.append("Stabilize soil moisture before applying preventive treatments.")

    if not pests:
        if crop_type == "sugarcane":
            pests = ["Early Shoot Borer"]
        elif crop_type == "fallow":
            pests = ["Weed-hosted pest buildup"]
        else:
            pests = ["Stem Borer"]

    if not actions:
        actions = ["Continue weekly scouting and keep field records updated."]

    prediction = {
        "crop_type": crop_type.title(),
        "growth_stage": stage,
        "risk_level": _risk_from_score(max(0, score)),
        "possible_pests": sorted(set(pests)),
        "reason": " ".join(reasons) or "Current environmental conditions do not indicate elevated pest pressure.",
        "recommended_action": " ".join(actions),
        "preventive_measures": [
            "Maintain balanced irrigation.",
            "Remove crop residues that host pests.",
            "Use chemical control only after field inspection confirms symptoms.",
        ],
        "last_prediction": datetime.now(timezone.utc).isoformat(),
    }
    cache.set("latest_pest", prediction)
    return prediction
