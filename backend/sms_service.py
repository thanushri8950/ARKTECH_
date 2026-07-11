import os
from datetime import datetime, timedelta, timezone
from typing import Any

from config import settings
from utils.cache import cache


def _signature(alert_type: str, location: str, reason: str) -> str:
    return f"{alert_type}|{location}|{reason}".lower().strip()


def _cooldown_active(signature: str) -> bool:
    alert_state = cache.get("sms_alert_state", {})
    last_sent = alert_state.get(signature)
    if not last_sent:
        return False
    try:
        sent_at = datetime.fromisoformat(last_sent)
    except ValueError:
        return False
    return datetime.now(timezone.utc) - sent_at < timedelta(minutes=settings.sms_cooldown_minutes)


def _mark_sent(signature: str) -> None:
    alert_state = cache.get("sms_alert_state", {})
    alert_state[signature] = datetime.now(timezone.utc).isoformat()
    cache.set("sms_alert_state", alert_state)


def send_alert(field_id: str, condition: str, recommendation: str):
    return send_intelligent_alert(
        alert_type="Crop Stress",
        location=field_id,
        reason=condition,
        recommended_action=recommendation,
    )


def send_intelligent_alert(alert_type: str, location: str, reason: str, recommended_action: str) -> dict[str, Any]:
    signature = _signature(alert_type, location, reason)
    timestamp = datetime.now(timezone.utc).isoformat()
    alert_record = {
        "type": alert_type,
        "location": location,
        "reason": reason,
        "recommended_action": recommended_action,
        "timestamp": timestamp,
        "signature": signature,
    }

    if _cooldown_active(signature):
        alert_record["status"] = "cooldown"
        cache.append_unique_alert(alert_record)
        return {"sent": False, "skipped": True, "reason": "SMS cooldown active", "alert": alert_record}

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    to_number = os.getenv("FARMER_PHONE_NUMBER")

    if not all([account_sid, auth_token, from_number, to_number]):
        alert_record["status"] = "not_configured"
        cache.append_unique_alert(alert_record)
        return {"sent": False, "skipped": True, "reason": "Twilio is not configured", "alert": alert_record}

    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        message = (
            "ARKTECH ALERT\n"
            f"Type: {alert_type}\n"
            f"Location: {location}\n"
            f"Reason: {reason}\n"
            f"Action: {recommended_action}\n"
            f"Time: {timestamp}"
        )

        response = client.messages.create(body=message, from_=from_number, to=to_number)
        _mark_sent(signature)
        alert_record["status"] = "sent"
        alert_record["provider_sid"] = response.sid
        cache.append_unique_alert(alert_record)
        return {"sent": True, "sid": response.sid, "alert": alert_record}
    except Exception as exc:
        alert_record["status"] = "failed"
        alert_record["error"] = str(exc)
        cache.append_unique_alert(alert_record)
        return {"sent": False, "skipped": False, "reason": str(exc), "alert": alert_record}
