import json
from prediction import predict_crop_stress
payload = {
    "field_id": "F003", "ndvi": 0.25, "ndwi": -0.08, "vv": -15.4, "vh": -22.1, "vv_vh_ratio": 0.69,
    "soil_moisture_index": 0.18, "rainfall": 0, "lst": 38, "crop_stage": "flowering",
    "crop_type": "Sugarcane", "latitude": 12.9716, "longitude": 77.5946, "leaf_wetness": 32,
    "sensor_soil_moisture": 16, "sensor_temperature": 38, "sensor_humidity": 40
}
print(predict_crop_stress(payload))
