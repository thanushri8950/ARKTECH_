import { useState } from "react";
import axios from "axios";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const TEST_CASES = {
  healthy: {
    field_id: "F001", ndvi: 0.72, ndwi: 0.25, vv: -12, vh: -19, vv_vh_ratio: 0.63,
    soil_moisture_index: 0.65, rainfall: 28, lst: 27, crop_stage: "vegetative",
    sensor_soil_moisture: 68, sensor_temperature: 27, sensor_humidity: 55,
  },
  moderate: {
    field_id: "F002", ndvi: 0.44, ndwi: 0.07, vv: -14, vh: -21, vv_vh_ratio: 0.67,
    soil_moisture_index: 0.39, rainfall: 7, lst: 33, crop_stage: "flowering",
    sensor_soil_moisture: 34, sensor_temperature: 33, sensor_humidity: 45,
  },
  severe: {
    field_id: "F003", ndvi: 0.25, ndwi: -0.08, vv: -15.4, vh: -22.1, vv_vh_ratio: 0.69,
    soil_moisture_index: 0.18, rainfall: 0, lst: 38, crop_stage: "flowering",
    sensor_soil_moisture: 16, sensor_temperature: 38, sensor_humidity: 40,
  },
};

const FIELD_LABELS = {
  field_id: "Field ID",
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: key === "field_id" || key === "crop_stage" ? value : parseFloat(value) }));
  };

  const runPrediction = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await axios.post(`${API_URL}/predict`, { ...form, send_sms_if_critical: sendSms });
      setResult(res.data);
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

      <main className="main-grid">
        <section className="panel">
          <div className="panel-head">
            <h2>AI Prediction</h2>
            <div className="quickfill">
              <button onClick={() => setForm(TEST_CASES.healthy)}>Load Healthy</button>
              <button onClick={() => setForm(TEST_CASES.moderate)}>Load Moderate</button>
              <button onClick={() => setForm(TEST_CASES.severe)}>Load Severe</button>
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
              </div>
              <div className="sms-status">
                {result.sms_required
                  ? result.sms_sent
                    ? "✅ SMS alert sent to farmer"
                    : result.sms_error
                      ? `⚠️ SMS required but failed: ${result.sms_error}`
                      : "⚠️ SMS required (checkbox was off, so none was sent)"
                  : "No SMS required for this condition."}
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
