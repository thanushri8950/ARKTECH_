from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from config import settings
from utils.cache import cache


RISK_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _risk_max(levels: list[str]) -> str:
    if not levels:
        return "LOW"
    return max(levels, key=lambda item: RISK_ORDER[item])


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_offline_weather(latitude: float, longitude: float, reason: str, local_observation: dict[str, Any] | None = None) -> dict[str, Any]:
    local = local_observation or {}
    cached = cache.get("latest_weather")
    if cached and not local:
        cached["source"] = "cache"
        cached["offline_mode"] = True
        cached["message"] = reason
        return cached

    temperature = _safe_float(local.get("sensor_temperature"), _safe_float(local.get("lst"), 30.0))
    humidity = _safe_float(local.get("sensor_humidity"), 60.0)
    rainfall = _safe_float(local.get("rainfall"), 0.0)
    wind_speed = _safe_float(local.get("wind_speed_kph"), 8.0)
    current = {
        "temperature_c": temperature,
        "humidity_percent": humidity,
        "rainfall_mm": rainfall,
        "rain_probability_percent": 70.0 if rainfall >= 12 else 25.0,
        "wind_speed_kph": wind_speed,
        "pressure_hpa": 1010.0,
        "uv_index": 8.0 if temperature >= settings.heatwave_temp_c else 6.0,
    }
    today = datetime.now(timezone.utc).date()
    forecast = []
    for offset in range(7):
        day_rain = max(0.0, rainfall * (0.65 if offset else 1.0) - offset)
        day_temp = temperature + (1.5 if offset == 1 and temperature >= 36 else 0)
        forecast.append({
            "date": (today + timedelta(days=offset)).isoformat(),
            "rainfall_mm": round(day_rain, 2),
            "rain_probability_percent": 75.0 if day_rain >= 12 else 25.0,
            "temperature_max_c": round(day_temp, 2),
            "temperature_min_c": round(max(5.0, day_temp - 8), 2),
            "humidity_mean_percent": humidity,
            "wind_speed_max_kph": wind_speed,
            "uv_index_max": current["uv_index"],
        })

    weather = _analyze_weather(latitude, longitude, {"current": {}, "hourly": {}, "daily": {
        "time": [day["date"] for day in forecast],
        "precipitation_sum": [day["rainfall_mm"] for day in forecast],
        "precipitation_probability_max": [day["rain_probability_percent"] for day in forecast],
        "temperature_2m_max": [day["temperature_max_c"] for day in forecast],
        "temperature_2m_min": [day["temperature_min_c"] for day in forecast],
        "relative_humidity_2m_mean": [day["humidity_mean_percent"] for day in forecast],
        "wind_speed_10m_max": [day["wind_speed_max_kph"] for day in forecast],
        "uv_index_max": [day["uv_index_max"] for day in forecast],
    }})
    weather["current"] = current
    weather["source"] = "offline-local"
    weather["offline_mode"] = True
    weather["message"] = reason
    cache.set("latest_weather", weather)
    return weather


def _default_weather(latitude: float, longitude: float, reason: str) -> dict[str, Any]:
    cached = cache.get("latest_weather")
    if cached:
        cached["source"] = "cache"
        cached["offline_mode"] = True
        cached["message"] = reason
        return cached

    weather = {
        "latitude": latitude,
        "longitude": longitude,
        "current": {
            "temperature_c": 30.0,
            "humidity_percent": 60.0,
            "rainfall_mm": 0.0,
            "rain_probability_percent": 20.0,
            "wind_speed_kph": 8.0,
            "pressure_hpa": 1010.0,
            "uv_index": 6.0,
        },
        "forecast": [],
        "events": [],
        "risk_level": "LOW",
        "recommendations": ["Use local sensor readings until weather data refreshes."],
        "source": "fallback",
        "offline_mode": True,
        "message": reason,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    cache.set("latest_weather", weather)
    return weather


def _analyze_weather(latitude: float, longitude: float, payload: dict[str, Any]) -> dict[str, Any]:
    daily = payload.get("daily", {})
    hourly = payload.get("hourly", {})
    current_raw = payload.get("current", {})

    forecast = []
    for index, day in enumerate(daily.get("time", [])[:7]):
        forecast.append({
            "date": day,
            "rainfall_mm": _safe_float(daily.get("precipitation_sum", [0])[index]),
            "rain_probability_percent": _safe_float(daily.get("precipitation_probability_max", [0])[index]),
            "temperature_max_c": _safe_float(daily.get("temperature_2m_max", [0])[index]),
            "temperature_min_c": _safe_float(daily.get("temperature_2m_min", [0])[index]),
            "humidity_mean_percent": _safe_float(daily.get("relative_humidity_2m_mean", [0])[index]),
            "wind_speed_max_kph": _safe_float(daily.get("wind_speed_10m_max", [0])[index]),
            "uv_index_max": _safe_float(daily.get("uv_index_max", [0])[index]),
        })

    today = forecast[0] if forecast else {}
    tomorrow = forecast[1] if len(forecast) > 1 else today
    current = {
        "temperature_c": _safe_float(current_raw.get("temperature_2m"), today.get("temperature_max_c", 30.0)),
        "humidity_percent": _safe_float(today.get("humidity_mean_percent"), 60.0),
        "rainfall_mm": _safe_float(today.get("rainfall_mm"), 0.0),
        "rain_probability_percent": _safe_float(today.get("rain_probability_percent"), 0.0),
        "wind_speed_kph": _safe_float(current_raw.get("wind_speed_10m"), today.get("wind_speed_max_kph", 0.0)),
        "pressure_hpa": _safe_float(hourly.get("surface_pressure", [1010])[0] if hourly.get("surface_pressure") else 1010),
        "uv_index": _safe_float(today.get("uv_index_max"), 0.0),
    }

    events = []
    risks = []
    recommendations = []

    if _safe_float(tomorrow.get("rainfall_mm")) >= settings.heavy_rain_mm:
        events.append("Heavy Rain")
        risks.append("HIGH")
        recommendations.append("Delay irrigation because heavy rain is expected within 24 hours.")
    elif _safe_float(tomorrow.get("rainfall_mm")) >= 12:
        events.append("Moderate Rain")
        risks.append("MEDIUM")
        recommendations.append("Reduce irrigation and recheck field moisture after rainfall.")

    if max(current["temperature_c"], _safe_float(tomorrow.get("temperature_max_c"))) >= settings.heatwave_temp_c:
        events.append("Heatwave")
        risks.append("HIGH")
        recommendations.append("Increase irrigation frequency and avoid fertilizer application during peak heat.")

    if max(current["wind_speed_kph"], _safe_float(tomorrow.get("wind_speed_max_kph"))) >= settings.strong_wind_kph:
        events.append("Strong Wind")
        risks.append("MEDIUM")
        recommendations.append("Avoid spraying pesticides or foliar nutrients during strong winds.")

    if current["humidity_percent"] >= settings.high_humidity_percent:
        events.append("Extreme Humidity")
        risks.append("MEDIUM")
        recommendations.append("Inspect leaves for fungal disease symptoms.")

    if current["humidity_percent"] <= settings.low_humidity_percent:
        events.append("Low Humidity")
        risks.append("MEDIUM")
        recommendations.append("Monitor evapotranspiration and consider light irrigation.")

    if current["temperature_c"] <= 6:
        events.append("Cold Wave")
        risks.append("HIGH")
        recommendations.append("Protect sensitive crops from cold stress.")

    weather = {
        "latitude": latitude,
        "longitude": longitude,
        "current": current,
        "forecast": forecast,
        "events": events,
        "risk_level": _risk_max(risks),
        "recommendations": recommendations or ["Weather conditions are suitable for routine crop operations."],
        "source": "open-meteo",
        "offline_mode": False,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    cache.set("latest_weather", weather)
    return weather


def get_weather(latitude: float | None = None, longitude: float | None = None, local_observation: dict[str, Any] | None = None) -> dict[str, Any]:
    lat = latitude if latitude is not None else settings.default_latitude
    lon = longitude if longitude is not None else settings.default_longitude
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return _default_weather(settings.default_latitude, settings.default_longitude, "Invalid coordinates; using cached weather.")
    if settings.offline_only or not settings.use_weather_api:
        return _build_offline_weather(lat, lon, "Offline-first local weather estimate; no cloud API used.", local_observation)

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,wind_speed_10m",
        "hourly": "surface_pressure",
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "precipitation_probability_max",
            "relative_humidity_2m_mean",
            "wind_speed_10m_max",
            "uv_index_max",
        ]),
        "timezone": "auto",
        "forecast_days": 7,
    }
    try:
        response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=settings.weather_timeout_seconds)
        response.raise_for_status()
        return _analyze_weather(lat, lon, response.json())
    except requests.RequestException as exc:
        return _default_weather(lat, lon, f"Weather API unavailable: {exc.__class__.__name__}.")
