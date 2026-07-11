from datetime import datetime, timezone
from typing import Any

from flask import Flask, jsonify, request
try:
    from flask_cors import CORS
except ImportError:
    def CORS(_app):
        return _app

from advisory import build_crop_advisory
from config import settings
from prediction import predict_crop_stress
from services.irrigation import build_irrigation_advice
from services.pest import predict_pest_risk
from services.weather import get_weather
from sms_service import send_intelligent_alert
from utils.cache import cache


app = Flask(__name__)
CORS(app)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.get("/")
def index():
    return jsonify({
        "name": "ArkTech MVP API",
        "status": "running",
        "offline_only": settings.offline_only,
        "dashboard_frontend": "http://127.0.0.1:5173/",
        "endpoints": {
            "health": "/health",
            "predict": "POST /predict",
            "weather": "/weather?latitude=12.9716&longitude=77.5946",
            "pest": "POST /pest",
            "dashboard": "/dashboard",
            "sync": "POST /sync",
            "sms_status": "/sms/status",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def _payload() -> dict[str, Any]:
    return request.get_json(silent=True) or {}


def _float_or_none(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _field_location(payload: dict[str, Any]) -> tuple[float | None, float | None]:
    latitude = _float_or_none(payload.get("latitude"))
    longitude = _float_or_none(payload.get("longitude"))
    return latitude, longitude


def _error(message: str, status: int = 400):
    return jsonify({"error": message, "detail": message, "timestamp": datetime.now(timezone.utc).isoformat()}), status


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "offline_cache": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/weather")
def weather():
    latitude = _float_or_none(request.args.get("latitude"))
    longitude = _float_or_none(request.args.get("longitude"))
    return jsonify(get_weather(latitude, longitude))


@app.post("/pest")
def pest():
    payload = _payload()
    latitude, longitude = _field_location(payload)
    weather_data = get_weather(latitude, longitude, payload)
    return jsonify(predict_pest_risk(payload, weather_data))


@app.post("/predict")
def predict():
    payload = _payload()
    if not payload.get("field_id"):
        return _error("field_id is required.")

    latitude, longitude = _field_location(payload)
    weather_data = get_weather(latitude, longitude, payload)
    stress = predict_crop_stress(payload)
    pest = predict_pest_risk(payload, weather_data)
    irrigation = build_irrigation_advice(payload, stress["condition"], weather_data)
    advisory = build_crop_advisory(stress, irrigation, pest, weather_data)

    sms_result = {"sent": False, "skipped": True, "reason": "SMS not requested or not required"}
    if advisory["sms_required"] and payload.get("send_sms_if_critical"):
        sms_result = send_intelligent_alert(
            alert_type=_alert_type(advisory, weather_data, pest, irrigation),
            location=str(payload.get("field_id")),
            reason=advisory["condition"],
            recommended_action=advisory["recommendation"],
        )

    response = {
        "field_id": payload.get("field_id"),
        **stress,
        **advisory,
        "weather": weather_data,
        "pest": pest,
        "irrigation": irrigation,
        "offline": {
            "mode": bool(weather_data.get("offline_mode")),
            "sync_pending": cache.snapshot().get("sync_pending", False),
            "last_sync_time": cache.snapshot().get("last_sync_time"),
        },
        "sms_sent": bool(sms_result.get("sent")),
        "sms_error": None if sms_result.get("sent") or sms_result.get("skipped") else sms_result.get("reason"),
        "sms_status": sms_result,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    return jsonify(response)


@app.get("/dashboard")
def dashboard():
    snapshot = cache.snapshot()
    weather_data = snapshot.get("weather") or get_weather(settings.default_latitude, settings.default_longitude)
    return jsonify({
        "status": {
            "online": not bool(weather_data.get("offline_mode")),
            "offline_mode": bool(weather_data.get("offline_mode")),
            "sync_pending": snapshot.get("sync_pending", False),
            "last_sync_time": snapshot.get("last_sync_time"),
        },
        "weather": weather_data,
        "pest": snapshot.get("pest"),
        "irrigation": snapshot.get("irrigation"),
        "moisture": snapshot.get("moisture"),
        "recent_alerts": snapshot.get("alerts", []),
        "risk_timeline": _risk_timeline(snapshot),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    })


@app.post("/sync")
def sync():
    payload = _payload()
    latitude, longitude = _field_location(payload)
    weather_data = get_weather(latitude, longitude, payload)
    cache.set("sync_pending", bool(weather_data.get("offline_mode")))
    return jsonify({
        "synced": not bool(weather_data.get("offline_mode")),
        "sync_pending": bool(weather_data.get("offline_mode")),
        "weather": weather_data,
        "last_sync_time": cache.snapshot().get("last_sync_time"),
    })


@app.get("/sms/status")
def sms_status():
    import os

    required = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER", "FARMER_PHONE_NUMBER"]
    missing = [name for name in required if not os.getenv(name)]
    return jsonify({
        "configured": not missing,
        "missing": missing,
        "cooldown_minutes": settings.sms_cooldown_minutes,
        "message": "Twilio is ready." if not missing else "Twilio credentials are missing in the backend environment.",
    })


def _alert_type(advisory: dict[str, Any], weather: dict[str, Any], pest: dict[str, Any], irrigation: dict[str, Any]) -> str:
    if pest.get("risk_level") in {"HIGH", "CRITICAL"}:
        return "Pest Risk"
    if "Heavy Rain" in weather.get("events", []):
        return "Heavy Rain"
    if "Heatwave" in weather.get("events", []):
        return "Heatwave"
    if irrigation.get("urgency") == "CRITICAL":
        return "Urgent Irrigation"
    return advisory.get("condition", "Crop Stress")


def _risk_timeline(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    weather = snapshot.get("weather") or {}
    pest = snapshot.get("pest") or {}
    irrigation = snapshot.get("irrigation") or {}
    return [
        {"name": "Weather", "risk": weather.get("risk_level", "LOW")},
        {"name": "Pest", "risk": pest.get("risk_level", "LOW")},
        {"name": "Irrigation", "risk": irrigation.get("urgency", "LOW")},
    ]


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
