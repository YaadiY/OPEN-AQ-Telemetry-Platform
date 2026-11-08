import os
import time
import requests
import pandas as pd
from datetime import datetime, timezone
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
    """
    Extracts normalized canonical City AND Local Area (Neighborhood).
    Example: 'Dhankawadi, Pune - IITM' -> City: 'Pune', Local Area: 'Dhankawadi'
    """
    text = f"{station_name} {locality or ''}".lower()
    matched_city = None
    for keyword, canonical_name in TARGET_CITIES.items():
        if keyword in text:
            matched_city = canonical_name
            break

    if not matched_city:
        return None, None

    # Parse local area from station name: take part before comma or dash
    cleaned_name = station_name
    for sep in [",", "-", "_"]:
        if sep in cleaned_name:
            cleaned_name = cleaned_name.split(sep)[0]
    
    local_area = cleaned_name.strip()
    return matched_city, local_area

def discover_target_stations(max_pages=15):
    """
    Discovers active stations in target metros with PM2.5 / PM10 sensors.
    """
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
            print(f"⚠️ Discovery network warning: {e}")
            break

    print(f"✅ Discovered {len(active_stations)} target stations with active sensors.\n")
    return active_stations

def fetch_historical_days_for_sensor(sensor_id, max_records=1000):
    """
    Fetches pre-aggregated daily averages for a sensor.
    1 call pulls up to 1000 days (~2.7 years) of daily air quality history!
    """
    url = f"{BASE_URL}/sensors/{sensor_id}/days"
    params = {
        "limit": max_records,
        "page": 1
    }
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=(5, 20))
        if res.status_code == 200:
            return res.json().get("results", [])
        elif res.status_code == 429:
            print("⚠️ Rate limit hit. Backing off for 3 seconds...")
            time.sleep(3)
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Sensor {sensor_id} request error: {e}")
    return []

def run_historical_backfill():
    stations = discover_target_stations()
    if not stations:
        print("❌ No active stations found for backfill.")
        return None

    total_sensors = sum(len(s["sensors"]) for s in stations)
    print(f"🚀 Starting Historical Backfill across {len(stations)} stations ({total_sensors} sensors)...")
    print("   Querying /v3/sensors/{id}/days for multi-year daily telemetry...\n")

    rows = []
    current_ingest_time = datetime.now(timezone.utc).isoformat()
    processed_count = 0

    for st in stations:
        for sensor in st["sensors"]:
            sensor_id = sensor.get("id")
            param = (sensor.get("parameter") or {}).get("name")
            units = (sensor.get("parameter") or {}).get("units")

            processed_count += 1
            print(f"[{processed_count}/{total_sensors}] Fetching daily history for sensor {sensor_id} ({st['city']} - {st['local_area']} - {param})...")
            
            days = fetch_historical_days_for_sensor(sensor_id, max_records=1000)
            
            for d in days:
                val = d.get("value")
                period = d.get("period") or {}
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

            # Respectful polite delay to stay well within API limits
            time.sleep(0.15)

    if not rows:
        print("❌ No historical records retrieved.")
        return None

    df = pd.DataFrame(rows)
    print(f"\n📊 Extracted {len(df):,} total daily historical measurements across {len(stations)} stations!")

    # 1. Enforce strict types
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
    parquet_path = f"{bronze_dir}/openaq_historical_days.parquet"
    df.to_parquet(parquet_path, engine="pyarrow", compression="snappy", index=False)
    
    file_size_kb = os.path.getsize(parquet_path) / 1024
    print(f"💾 Saved Parquet: {parquet_path} ({file_size_kb:.1f} KB)")
    print(f"   Date range: {df['measured_at_utc'].min().date()} to {df['measured_at_utc'].max().date()}")

    # 3. Synchronize directly to GCS Bronze Lake
    if BUCKET_NAME:
        print(f"\n☁️ Uploading to GCS: gs://{BUCKET_NAME}/bronze/openaq_historical_days.parquet ...")
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob("bronze/openaq_historical_days.parquet")
        blob.upload_from_filename(parquet_path)
        print("✅ GCS Upload Complete!")

    return parquet_path

if __name__ == "__main__":
    run_historical_backfill()

