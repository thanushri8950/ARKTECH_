from typing import Any


SEVERITY_BY_CLASS = {
    0: "Normal",
    1: "Warning",
    2: "Critical",
}


def build_crop_advisory(prediction: dict[str, Any], irrigation: dict[str, Any], pest: dict[str, Any], weather: dict[str, Any]) -> dict[str, Any]:
    predicted_class = int(prediction.get("ai_predicted_class", 1))
    severity = SEVERITY_BY_CLASS.get(predicted_class, "Warning")
    condition = prediction.get("condition", "Crop Stress")

    recommendation_parts = []
    if predicted_class == 0:
        recommendation_parts.append("Crop condition is stable. Continue routine monitoring.")
    elif predicted_class == 1:
        recommendation_parts.append("Moderate stress detected. Check irrigation uniformity and inspect crop canopy.")
    else:
        recommendation_parts.append("Severe moisture stress detected. Prioritize field inspection and water management.")

    recommendation_parts.append(irrigation.get("recommended_action", "Follow the irrigation plan."))
    if weather.get("risk_level") in {"HIGH", "CRITICAL"}:
        recommendation_parts.append(weather.get("recommendations", ["Review weather risks before field operations."])[0])
    if pest.get("risk_level") in {"HIGH", "CRITICAL"}:
        recommendation_parts.append(pest.get("recommended_action", "Scout for pest symptoms."))

    sms_required = (
        severity == "Critical"
        or irrigation.get("urgency") == "CRITICAL"
        or weather.get("risk_level") == "CRITICAL"
        or pest.get("risk_level") in {"HIGH", "CRITICAL"}
        or "Heatwave" in weather.get("events", [])
        or "Heavy Rain" in weather.get("events", [])
    )

    return {
        "condition": condition,
        "severity": severity,
        "recommendation": " ".join(recommendation_parts),
        "sms_required": sms_required,
    }
