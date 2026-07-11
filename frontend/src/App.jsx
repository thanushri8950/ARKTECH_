import { useEffect, useState } from "react";
import axios from "axios";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const TEST_CASES = {
  healthy: {
    field_id: "F001", ndvi: 0.72, ndwi: 0.25, vv: -12, vh: -19, vv_vh_ratio: 0.63,
    soil_moisture_index: 0.65, rainfall: 28, lst: 27, crop_stage: "vegetative",
    crop_type: "Rice", latitude: 12.9716, longitude: 77.5946, leaf_wetness: 42,
    sensor_soil_moisture: 68, sensor_temperature: 27, sensor_humidity: 55,
  },
  moderate: {
    field_id: "F002", ndvi: 0.44, ndwi: 0.07, vv: -14, vh: -21, vv_vh_ratio: 0.67,
    soil_moisture_index: 0.39, rainfall: 7, lst: 33, crop_stage: "flowering",
    crop_type: "Rice", latitude: 12.9716, longitude: 77.5946, leaf_wetness: 55,
    sensor_soil_moisture: 34, sensor_temperature: 33, sensor_humidity: 45,
  },
  severe: {
    field_id: "F003", ndvi: 0.25, ndwi: -0.08, vv: -15.4, vh: -22.1, vv_vh_ratio: 0.69,
    soil_moisture_index: 0.18, rainfall: 0, lst: 38, crop_stage: "flowering",
    crop_type: "Sugarcane", latitude: 12.9716, longitude: 77.5946, leaf_wetness: 32,
    sensor_soil_moisture: 16, sensor_temperature: 38, sensor_humidity: 40,
  },
};

const FIELD_LABELS = {
  field_id: "Field ID",
  crop_type: "Crop Type",
  latitude: "Latitude",
  longitude: "Longitude",
  crop_stage: "Crop Stage",
  ndvi: "NDVI",
  ndwi: "NDWI",
  vv: "SAR VV",
  vh: "SAR VH",
  vv_vh_ratio: "VV/VH Ratio",
  soil_moisture_index: "Soil Moisture Index",
  rainfall: "Rainfall (mm)",
  lst: "Land Surface Temp (°C)",
  sensor_soil_moisture: "Sensor: Soil Moisture (%)",
  sensor_temperature: "Sensor: Temperature (°C)",
  sensor_humidity: "Sensor: Humidity (%)",
  leaf_wetness: "Leaf Wetness (%)",
};

const SEVERITY_COLORS = {
  Normal: "#4C7A3D",
  Warning: "#C98A2C",
  Critical: "#B23A2E",
};

export default function App() {
  const [form, setForm] = useState(TEST_CASES.moderate);
  const [sendSms, setSendSms] = useState(false);
  const [result, setResult] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (key, value) => {
    const textKeys = ["field_id", "crop_stage", "crop_type"];
    setForm((prev) => ({ ...prev, [key]: textKeys.includes(key) ? value : parseFloat(value) }));
  };

  const loadCase = (caseName) => {
    setResult(null);
    setError(null);
    setForm({ ...TEST_CASES[caseName] });
  };

  const loadDashboard = async () => {
    try {
      const res = await axios.get(`${API_URL}/dashboard`);
      setDashboard(res.data);
    } catch {
      setDashboard((prev) => prev || { status: { offline_mode: true, sync_pending: true }, recent_alerts: [] });
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const runPrediction = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await axios.post(`${API_URL}/predict`, { ...form, send_sms_if_critical: sendSms });
      setResult(res.data);
      loadDashboard();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not reach the ARKTECH backend. Is it running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <span className="brand-mark">ARK</span>
          <span className="brand-rest">TECH</span>
        </div>
        <p className="tagline">Satellite-driven crop stress monitoring &amp; irrigation advisory</p>
      </header>

      <section className="stats-row">
        {[
          { label: "Monitored Fields", value: 30 },
          { label: "Healthy", value: 18, color: "#4C7A3D" },
          { label: "Moderate Stress", value: 8, color: "#C98A2C" },
          { label: "Critical", value: 4, color: "#B23A2E" },
        ].map((s) => (
          <div className="stat-card" key={s.label}>
            <div className="stat-value" style={{ color: s.color || "#2E4034" }}>{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </section>

      <section className="status-strip">
        <div>
          <span className={dashboard?.status?.offline_mode ? "dot danger" : "dot ok"} />
          {dashboard?.status?.offline_mode ? "Offline Mode" : "Online"}
        </div>
        <div>Sync: {dashboard?.status?.sync_pending ? "Pending" : "Current"}</div>
        <div>Last sync: {formatTime(dashboard?.status?.last_sync_time)}</div>
        <button onClick={loadDashboard}>Refresh</button>
      </section>

      <main className="main-grid">
        <section className="panel">
          <div className="panel-head">
            <h2>AI Prediction</h2>
            <div className="quickfill">
              <button onClick={() => loadCase("healthy")}>Load Healthy</button>
              <button onClick={() => loadCase("moderate")}>Load Moderate</button>
              <button onClick={() => loadCase("severe")}>Load Severe</button>
            </div>
          </div>

          <div className="form-grid">
            {Object.keys(FIELD_LABELS).map((key) => (
              <label key={key} className="field">
                <span>{FIELD_LABELS[key]}</span>
                {key === "crop_stage" ? (
                  <select value={form[key]} onChange={(e) => handleChange(key, e.target.value)}>
                    <option value="sowing">Sowing</option>
                    <option value="vegetative">Vegetative</option>
                    <option value="flowering">Flowering</option>
                  </select>
                ) : key === "crop_type" ? (
                  <select value={form[key]} onChange={(e) => handleChange(key, e.target.value)}>
                    <option value="Rice">Rice</option>
                    <option value="Sugarcane">Sugarcane</option>
                    <option value="Fallow">Fallow</option>
                  </select>
                ) : (
                  <input
                    type={key === "field_id" ? "text" : "number"}
                    step="0.01"
                    value={form[key]}
                    onChange={(e) => handleChange(key, e.target.value)}
                  />
                )}
              </label>
            ))}
          </div>

          <label className="checkbox-row">
            <input type="checkbox" checked={sendSms} onChange={(e) => setSendSms(e.target.checked)} />
            Send SMS if critical
          </label>

          <button className="run-btn" onClick={runPrediction} disabled={loading}>
            {loading ? "Running Edge AI…" : "RUN EDGE AI"}
          </button>

          {error && <p className="error-text">{error}</p>}
        </section>

        <section className="panel result-panel">
          <h2>Result</h2>
          {!result && !loading && <p className="empty-state">Run a prediction to see the crop advisory here.</p>}
          {result && (
            <div className="result-card" style={{ borderColor: SEVERITY_COLORS[result.severity] }}>
              <div className="result-top">
                <span className="condition" style={{ color: SEVERITY_COLORS[result.severity] }}>
                  {result.condition}
                </span>
                <span className="confidence">{result.confidence}% confidence</span>
              </div>
              <p className="recommendation">{result.recommendation}</p>
              <div className="result-meta">
                <span>Field: {result.field_id}</span>
                <span>Severity: {result.severity}</span>
                <span>AI model output: {result.ai_predicted_class}</span>
                <span>Model: {result.model_source}</span>
              </div>
              <div className="sms-status">{smsStatusText(result)}</div>
            </div>
          )}
        </section>
      </main>

      <section className="insight-grid">
        <Widget title="Weather">
          <Metric label="Risk" value={activeWeather(result, dashboard)?.risk_level || "LOW"} />
          <Metric label="Temperature" value={`${activeWeather(result, dashboard)?.current?.temperature_c ?? "--"} °C`} />
          <Metric label="Rain Probability" value={`${activeWeather(result, dashboard)?.current?.rain_probability_percent ?? "--"}%`} />
          <p className="mini-text">{activeWeather(result, dashboard)?.recommendations?.[0] || "Weather data will appear after sync."}</p>
        </Widget>

        <Widget title="Pest Risk">
          <Metric label="Risk" value={(result?.pest || dashboard?.pest)?.risk_level || "LOW"} />
          <Metric label="Possible Pest" value={(result?.pest || dashboard?.pest)?.possible_pests?.join(", ") || "Routine watch"} />
          <p className="mini-text">{(result?.pest || dashboard?.pest)?.recommended_action || "Run a prediction to generate a crop-specific pest advisory."}</p>
        </Widget>

        <Widget title="Irrigation">
          <Metric label="Status" value={(result?.irrigation || dashboard?.irrigation)?.status || "No data"} />
          <Metric label="Urgency" value={(result?.irrigation || dashboard?.irrigation)?.urgency || "LOW"} />
          <p className="mini-text">{(result?.irrigation || dashboard?.irrigation)?.reason || "Irrigation advice uses moisture, forecast, temperature, and crop stress."}</p>
        </Widget>
      </section>

      <section className="chart-grid">
        <div className="panel chart-panel">
          <h2>7 Day Forecast</h2>
          <ResponsiveContainer width="100%" height={230}>
            <AreaChart data={forecastData(activeWeather(result, dashboard))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Area dataKey="temperature" stroke="#B23A2E" fill="#F2C7BE" />
              <Area dataKey="humidity" stroke="#4C7A3D" fill="#CFE1C9" />
              <Area dataKey="rainfall" stroke="#2B6E8A" fill="#C8DFEA" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="panel chart-panel">
          <h2>Risk Timeline</h2>
          <ResponsiveContainer width="100%" height={230}>
            <BarChart data={riskData(result, dashboard)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis domain={[0, 4]} ticks={[1, 2, 3, 4]} />
              <Tooltip />
              <Bar dataKey="score" fill="#4C7A3D" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="panel alerts-panel">
        <h2>Recent Alerts</h2>
        {(dashboard?.recent_alerts || []).length === 0 ? (
          <p className="empty-state">No alerts have been generated yet.</p>
        ) : (
          <div className="alert-list">
            {dashboard.recent_alerts.slice(0, 5).map((alert) => (
              <div className="alert-item" key={`${alert.signature}-${alert.timestamp}`}>
                <strong>{alert.type}</strong>
                <span>{alert.location}</span>
                <span>{alert.reason}</span>
                <small>{formatTime(alert.timestamp)}</small>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function Widget({ title, children }) {
  return (
    <section className="panel widget">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function activeWeather(result, dashboard) {
  return result?.weather || dashboard?.weather;
}

function forecastData(weather) {
  return (weather?.forecast || []).map((day) => ({
    date: day.date?.slice(5),
    temperature: day.temperature_max_c,
    humidity: day.humidity_mean_percent,
    rainfall: day.rainfall_mm,
  }));
}

const RISK_SCORE = { LOW: 1, MEDIUM: 2, HIGH: 3, CRITICAL: 4, Normal: 1, Warning: 2, Critical: 4 };

function riskData(result, dashboard) {
  if (result) {
    return [
      { name: "Crop", score: RISK_SCORE[result.severity] || 1 },
      { name: "Weather", score: RISK_SCORE[result.weather?.risk_level] || 1 },
      { name: "Pest", score: RISK_SCORE[result.pest?.risk_level] || 1 },
      { name: "Water", score: RISK_SCORE[result.irrigation?.urgency] || 1 },
    ];
  }
  return (dashboard?.risk_timeline || []).map((item) => ({ name: item.name, score: RISK_SCORE[item.risk] || 1 }));
}

function formatTime(value) {
  if (!value) return "Not synced";
  return new Date(value).toLocaleString();
}

function smsStatusText(result) {
  if (!result.sms_required) return "No SMS required for this condition.";
  if (result.sms_sent) return "SMS alert sent to farmer.";
  if (!result.sms_status) return "SMS required, but no SMS status was returned.";
  if (result.sms_status.reason === "SMS not requested or not required") {
    return "SMS required. Enable the checkbox before running the prediction to send it.";
  }
  if (result.sms_status.reason) return `SMS not sent: ${result.sms_status.reason}.`;
  if (result.sms_error) return `SMS required but failed: ${result.sms_error}`;
  return "SMS required, but delivery status is unknown.";
}
