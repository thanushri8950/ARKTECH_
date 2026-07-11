import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonCache:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read_all(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_all(self, data: dict[str, Any]) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2, default=str))
        tmp_path.replace(self.path)

    def get(self, key: str, default: Any = None) -> Any:
        return self._read_all().get(key, default)

    def set(self, key: str, value: Any) -> None:
        data = self._read_all()
        data[key] = value
        data["last_sync_time"] = datetime.now(timezone.utc).isoformat()
        self._write_all(data)

    def append_unique_alert(self, alert: dict[str, Any], limit: int = 50) -> None:
        data = self._read_all()
        alerts = data.get("recent_alerts", [])
        signature = alert.get("signature")
        if signature and any(item.get("signature") == signature for item in alerts[:5]):
            return
        data["recent_alerts"] = [alert, *alerts][:limit]
        data["last_sync_time"] = datetime.now(timezone.utc).isoformat()
        self._write_all(data)

    def snapshot(self) -> dict[str, Any]:
        data = self._read_all()
        return {
            "last_sync_time": data.get("last_sync_time"),
            "sync_pending": bool(data.get("sync_pending", False)),
            "weather": data.get("latest_weather"),
            "moisture": data.get("latest_moisture"),
            "irrigation": data.get("latest_irrigation"),
            "pest": data.get("latest_pest"),
            "alerts": data.get("recent_alerts", []),
            "farmer": data.get("farmer_information", {}),
        }


cache = JsonCache(Path(__file__).resolve().parents[1] / "data" / "offline_cache.json")
