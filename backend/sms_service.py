"""
ARKTECH - SMS Service (Twilio)
---------------------------------
Sends a critical-condition alert to the farmer's phone via Twilio.
Only called when advisory.py flags sms_required = True.
"""

import os

from twilio.rest import Client


def send_alert(field_id: str, condition: str, recommendation: str):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    to_number = os.getenv("FARMER_PHONE_NUMBER")

    if not all([account_sid, auth_token, from_number, to_number]):
        raise RuntimeError(
            "Twilio is not configured. Fill in backend/.env with your "
            "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, "
            "and FARMER_PHONE_NUMBER."
        )

    client = Client(account_sid, auth_token)

    message = (
        f"ARKTECH ALERT\n\n"
        f"Field: {field_id}\n"
        f"Condition: {condition}\n\n"
        f"Recommendation:\n{recommendation}"
    )

    response = client.messages.create(body=message, from_=from_number, to=to_number)
    return response.sid
