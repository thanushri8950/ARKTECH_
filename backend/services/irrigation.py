from typing import Any

from config import settings
from utils.cache import cache


def build_irrigation_advice(payload: dict[str, Any], condition: str, weather: dict[str, Any]) -> dict[str, Any]:
    moisture = float(payload.get("sensor_soil_moisture") or (float(payload.get("soil_moisture_index", 0.5)) * 100))
    current = weather.get("current", {})
    events = set(weather.get("events", []))
    forecast = weather.get("forecast", [])
    tomorrow_rain = float(forecast[1].get("rainfall_mm", 0)) if len(forecast) > 1 else 0.0

    reasons = []
    advice = "No Irrigation"
    urgency = "LOW"

    if moisture <= settings.critical_moisture_percent:
        advice = "Urgent Irrigation"
        urgency = "CRITICAL"
        reasons.append("Soil moisture is critically low.")
    elif moisture <= settings.low_moisture_percent:
        advice = "Moderate Irrigation"
        urgency = "HIGH"
        reasons.append("Soil moisture is below the safe threshold.")
    else:
        reasons.append("Soil moisture is within the acceptable range.")

    if "Heavy Rain" in events or tomorrow_rain >= settings.heavy_rain_mm:
        advice = "Delay Irrigation"
        urgency = "MEDIUM" if urgency != "CRITICAL" else "HIGH"
        reasons.append("Rain is expected soon.")
    elif "Heatwave" in events and moisture <= 45:
        advice = "Increase Irrigation"
        urgency = "HIGH"
        reasons.append("Heatwave conditions can increase crop water demand.")
    elif "Low Humidity" in events and moisture <= 45:
        advice = "Light Irrigation"
        urgency = "MEDIUM"
        reasons.append("Low humidity can dry the canopy and soil faster.")

    if "Severe" in condition and advice not in {"Delay Irrigation", "Increase Irrigation"}:
        advice = "Urgent Irrigation"
        urgency = "CRITICAL"
        reasons.append("AI model detected severe crop water stress.")

    result = {
        "status": advice,
        "urgency": urgency,
        "soil_moisture_percent": round(moisture, 2),
        "reason": " ".join(reasons),
        "recommended_action": _action_for(advice),
        "weather_factor": list(events),
        "rain_expected_mm": tomorrow_rain,
        "temperature_c": current.get("temperature_c"),
    }
    cache.set("latest_moisture", {"soil_moisture_percent": result["soil_moisture_percent"], "field_id": payload.get("field_id")})
    cache.set("latest_irrigation", result)
    return result


def _action_for(advice: str) -> str:
    return {
        "No Irrigation": "Continue monitoring; no irrigation is needed now.",
        "Light Irrigation": "Apply light irrigation and recheck soil moisture within 12 hours.",
        "Moderate Irrigation": "Apply moderate irrigation within the next irrigation window.",
        "Urgent Irrigation": "Irrigate within 6-12 hours unless heavy rain is confirmed.",
        "Delay Irrigation": "Avoid irrigation today and reassess after rainfall.",
        "Increase Irrigation": "Increase irrigation amount and avoid peak afternoon field operations.",
    }.get(advice, "Monitor field conditions and follow local agronomy guidance.")
