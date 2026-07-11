import os
from dataclasses import dataclass
from pathlib import Path


def _load_local_env() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


_load_local_env()


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    offline_only: bool = _bool_env("OFFLINE_ONLY", True)
    use_weather_api: bool = _bool_env("USE_WEATHER_API", False)
    weather_timeout_seconds: int = _int_env("WEATHER_TIMEOUT_SECONDS", 6)
    weather_cache_ttl_minutes: int = _int_env("WEATHER_CACHE_TTL_MINUTES", 180)
    sms_cooldown_minutes: int = _int_env("SMS_COOLDOWN_MINUTES", 45)
    default_latitude: float = _float_env("DEFAULT_LATITUDE", 12.9716)
    default_longitude: float = _float_env("DEFAULT_LONGITUDE", 77.5946)
    critical_moisture_percent: float = _float_env("CRITICAL_MOISTURE_PERCENT", 20)
    low_moisture_percent: float = _float_env("LOW_MOISTURE_PERCENT", 35)
    heatwave_temp_c: float = _float_env("HEATWAVE_TEMP_C", 38)
    heavy_rain_mm: float = _float_env("HEAVY_RAIN_MM", 35)
    strong_wind_kph: float = _float_env("STRONG_WIND_KPH", 45)
    high_humidity_percent: float = _float_env("HIGH_HUMIDITY_PERCENT", 85)
    low_humidity_percent: float = _float_env("LOW_HUMIDITY_PERCENT", 30)


settings = Settings()
