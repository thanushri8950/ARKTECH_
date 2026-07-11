# ARKTECH_

ArkTech is an AI-driven crop monitoring MVP with crop stress prediction, weather-aware irrigation advice, pest risk prediction, offline cache support, and intelligent SMS alerting.

The default mode is offline-first and no-cloud: `OFFLINE_ONLY=true` and `USE_WEATHER_API=false`. Local/manual field values drive the advisory engine, and cached values keep the dashboard usable without internet. Set `USE_WEATHER_API=true` only when you intentionally want Open-Meteo weather enrichment.

## Backend

```bash
cd backend
python3 -m pip install -r requirements.txt
python3 app.py
```

The API runs on `http://127.0.0.1:8000`.

Key endpoints:

- `GET /health` - backend health check.
- `POST /predict` - crop stress, weather, pest, irrigation, offline, and SMS advisory response.
- `GET /weather?latitude=12.97&longitude=77.59` - Open-Meteo weather with cached fallback.
- `POST /pest` - rule-based pest risk prediction.
- `GET /dashboard` - dashboard snapshot from cached/latest data.
- `POST /sync` - refresh weather and sync status.

Runtime configuration lives in environment variables. Copy `backend/.env.example` and fill Twilio values when SMS delivery is needed.

Twilio checklist:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `FARMER_PHONE_NUMBER`

Check SMS readiness at `GET /sms/status`.

## Hardware Positioning

This MVP works without hardware by using satellite/model inputs plus manual sensor values. With hardware, use ESP32 for low-cost farm sensor nodes such as soil moisture, temperature, humidity, and pump relay telemetry. Use a PLC only for industrial-grade pump automation where rugged I/O, safety interlocks, and heavy electrical control are required.

## Frontend

```bash
cd frontend
npm ci
npm run dev
```

The dashboard calls the backend at `http://127.0.0.1:8000` and displays weather, pest risk, offline/sync status, irrigation status, recent alerts, and trend charts.
