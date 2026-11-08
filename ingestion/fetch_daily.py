import os
import time
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()

API_KEY = os.getenv("OPENAQ_API_KEY")
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
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

def parse_city_and_area(station_name, locality):
    text = f"{station_name} {locality or ''}".lower()
    matched_city = None
    for keyword, canonical_name in TARGET_CITIES.items():
        if keyword in text:
            matched_city = canonical_name
            break

    if not matched_city:
        return None, None

    cleaned_name = station_name
    for sep in [",", "-", "_"]:
        if sep in cleaned_name:
            cleaned_name = cleaned_name.split(sep)[0]
    
    local_area = cleaned_name.strip()
    return matched_city, local_area

def discover_active_stations(max_pages=15):
    print("🔍 Discovering active monitoring stations across target metros...")
    active_stations = []

    for page in range(1, max_pages + 1):
        params = {
            "iso": "IN",
            "limit": 100,
            "page": page,
            "order_by": "id",
            "sort_order": "desc"
        }
        try:
            res = requests.get(f"{BASE_URL}/locations", headers=HEADERS, params=params, timeout=(5, 15))
            if res.status_code != 200:
                break
            locations = res.json().get("results", [])
            if not locations:
                break

            for loc in locations:
                if not loc.get("datetimeLast"):
                    continue

                name = loc.get("name") or ""
                locality = loc.get("locality") or ""
                city, local_area = parse_city_and_area(name, locality)

                if city:
                    target_sensors = [
                        s for s in loc.get("sensors", [])
                        if (s.get("parameter") or {}).get("name") in ["pm25", "pm10"]
                    ]

                    if target_sensors:
                        active_stations.append({
                            "station_id": loc.get("id"),
                            "station_name": name,
                            "city": city,
                            "local_area": local_area,
                            "latitude": (loc.get("coordinates") or {}).get("latitude"),
                            "longitude": (loc.get("coordinates") or {}).get("longitude"),
                            "sensors": target_sensors
                        })
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Discovery network error: {e}")
            break

    print(f"✅ Discovered {len(active_stations)} active stations.")
    return active_stations

def fetch_recent_measurements(sensor_id, hours=48, limit=100):
    """
    Pulls measurements within the last `hours` window.
    Strictly filters datetime_from to bypass OpenAQ v3 sort trap.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"{BASE_URL}/sensors/{sensor_id}/measurements"
    params = {
        "datetime_from": cutoff,
        "limit": limit
    }
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=(5, 15))
        if res.status_code == 200:
            return res.json().get("results", [])
    except requests.exceptions.RequestException:
        pass
    return []

def run_daily_batch(hours_window=48):
    start_time = time.time()
    stations = discover_active_stations()
    if not stations:
        print("❌ No active stations found.")
        return None

    total_sensors = sum(len(s["sensors"]) for s in stations)
    print(f"📡 Running Daily Ingestion across {len(stations)} stations ({total_sensors} sensors)...")
    print(f"   Window: Last {hours_window} hours (Sliding overlap window)\n")

    rows = []
    current_ingest_time = datetime.now(timezone.utc).isoformat()

    for st in stations:
        for sensor in st["sensors"]:
            sensor_id = sensor.get("id")
            param = (sensor.get("parameter") or {}).get("name")
            units = (sensor.get("parameter") or {}).get("units")

            readings = fetch_recent_measurements(sensor_id, hours=hours_window, limit=100)
            for r in readings:
                val = r.get("value")
                period = r.get("period") or {}
                dt_to = (period.get("datetimeTo") or {}).get("utc")

                if val is not None and dt_to is not None:
                    rows.append({
                        "station_id": st["station_id"],
                        "station_name": st["station_name"],
                        "city": st["city"],
                        "local_area": st["local_area"],
                        "latitude": st["latitude"],
                        "longitude": st["longitude"],
                        "sensor_id": sensor_id,
                        "pollutant": param,
                        "units": units,
                        "measurement_value": float(val),
                        "measured_at_utc": dt_to,
                        "ingested_at_utc": current_ingest_time
                    })

            time.sleep(0.05)

    if not rows:
        print("⚠️ No telemetry returned in this window.")
        return None

    df = pd.DataFrame(rows)
    print(f"\n📊 Extracted {len(df):,} fresh telemetry readings.")

    # 1. Enforce schema
    df["station_id"] = df["station_id"].astype("int64")
    df["sensor_id"] = df["sensor_id"].astype("int64")
    df["city"] = df["city"].astype(str)
    df["local_area"] = df["local_area"].fillna("Unknown").astype(str)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["measurement_value"] = pd.to_numeric(df["measurement_value"], errors="coerce")
    df["measured_at_utc"] = pd.to_datetime(df["measured_at_utc"], utc=True)
    df["ingested_at_utc"] = pd.to_datetime(df["ingested_at_utc"], utc=True)

    df = df.sort_values(by="measured_at_utc", ascending=False).reset_index(drop=True)

    # 2. Save directly to Bronze Parquet
    bronze_dir = "data/bronze"
    os.makedirs(bronze_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    parquet_path = f"{bronze_dir}/openaq_daily_{timestamp}.parquet"
    df.to_parquet(parquet_path, engine="pyarrow", compression="snappy", index=False)

    file_size_kb = os.path.getsize(parquet_path) / 1024
    print(f"💾 Saved Parquet: {parquet_path} ({file_size_kb:.1f} KB)")

    # 3. Upload to GCS
    if BUCKET_NAME:
        print(f"☁️ Uploading to GCS: gs://{BUCKET_NAME}/bronze/openaq_daily_{timestamp}.parquet ...")
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(f"bronze/openaq_daily_{timestamp}.parquet")
        blob.upload_from_filename(parquet_path)
        print("✅ GCS Upload Complete!")

    elapsed = round(time.time() - start_time, 2)
    print(f"⏱️ Daily Batch Completed in {elapsed}s\n")
    return parquet_path

if __name__ == "__main__":
    run_daily_batch()

