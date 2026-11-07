import os
import requests
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("OPENAQ_API_KEY")
BASE_URL = "https://api.openaq.org/v3"
HEADERS = {
    "X-API-Key": API_KEY,
    "Accept": "application/json"
}
TARGET_CITIES = {
    "delhi": "Delhi",
    "mumbai": "Mumbai",
    "pune": "Pune",
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
    "hyderabad": "Hyderabad",
    "solapur": "Solapur"
}
def identify_city(station_name, locality):
    text = f"{station_name} {locality}".lower()
    for keyword, canonical_name in TARGET_CITIES.items():
        if keyword in text:
            return canonical_name
    return None
def fetch_target_stations(max_pages=5):
    print("🔍 Discovering stations across Pune, Mumbai, Delhi, Bengaluru, Hyderabad, Solapur...")
    matched_stations = []
    for page in range(1, max_pages + 1):
        params = {
            "iso": "IN",
            "limit": 100,
            "page": page
        }
        try:
            res = requests.get(f"{BASE_URL}/locations", headers=HEADERS, params=params, timeout=(5, 15))
            if res.status_code != 200:
                break
            locations = res.json().get("results", [])
            if not locations:
                break
            for loc in locations:
                name = loc.get("name") or ""
                locality = loc.get("locality") or ""
                city = identify_city(name, locality)
                
                if city:
                    matched_stations.append({
                        "station_id": loc.get("id"),
                        "station_name": name,
                        "city": city,
                        "latitude": (loc.get("coordinates") or {}).get("latitude"),
                        "longitude": (loc.get("coordinates") or {}).get("longitude"),
                        "sensors": loc.get("sensors", [])
                    })
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error while scanning locations: {e}")
            break
    print(f"✅ Found {len(matched_stations)} matching stations in target cities.")
    return matched_stations
def fetch_measurements(sensor_id, limit=5):
    url = f"{BASE_URL}/sensors/{sensor_id}/measurements"
    params = {"limit": limit}
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=(5, 10))
        if res.status_code == 200:
            return res.json().get("results", [])
    except requests.exceptions.RequestException:
        pass
    return []
def run_extraction(max_stations=25, measurements_per_sensor=5):
    stations = fetch_target_stations()
    if not stations:
        print("⚠️ No stations found.")
        return None
    stations_to_process = stations[:max_stations]
    print(f"🚀 Extracting telemetry for {len(stations_to_process)} stations...")
    rows = []
    current_ingest_time = datetime.now(timezone.utc).isoformat()
    for st in stations_to_process:
        for sensor in st["sensors"]:
            param = (sensor.get("parameter") or {}).get("name")
            sensor_id = sensor.get("id")
            if param in ["pm25", "pm10"]:
                readings = fetch_measurements(sensor_id, limit=measurements_per_sensor)
                for r in readings:
                    val = r.get("value")
                    period = r.get("period") or {}
                    dt_to = (period.get("datetimeTo") or {}).get("utc")
                    if val is not None and dt_to is not None:
                        rows.append({
                            "station_id": st["station_id"],
                            "station_name": st["station_name"],
                            "city": st["city"],
                            "latitude": st["latitude"],
                            "longitude": st["longitude"],
                            "sensor_id": sensor_id,
                            "pollutant": param,
                            "units": (sensor.get("parameter") or {}).get("units"),
                            "measurement_value": float(val),
                            "measured_at_utc": dt_to,
                            "ingested_at_utc": current_ingest_time
                        })
    if not rows:
        print("⚠️ No telemetry extracted.")
        return None
    df = pd.DataFrame(rows)
    # Save to Landing Zone (CSV)
    landing_dir = "data/landing"
    os.makedirs(landing_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    csv_file = f"{landing_dir}/openaq_raw_{timestamp}.csv"
    # Export cleanly quoted CSV
    df.to_csv(csv_file, index=False)
    print(f"\n🎉 Step 1 Complete: Raw CSV Saved!")
    print(f"📄 CSV Location: {csv_file}")
    print(f"📊 Total Records: {len(df)}")
    print(f"📁 File Size: {os.path.getsize(csv_file)} bytes")
    return csv_file
if __name__ == "__main__":
    run_extraction()