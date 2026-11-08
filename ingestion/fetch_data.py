import os
import re
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

def discover_all_active_stations(max_pages=15):
    """
    Discovers ALL active stations reporting telemetry in target metros.
    """
    print(" Discovering all active monitoring stations across target metros...")
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
                # Must have active telemetry
                if not loc.get("datetimeLast"):
                    continue

                name = loc.get("name") or ""
                locality = loc.get("locality") or ""
                city, local_area = parse_city_and_area(name, locality)

                if city:
                    # Filter for PM2.5 and PM10 sensors
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
            print(f"⚠️ Network warning: {e}")
            break

    print(f"✅ Discovered {len(active_stations)} active stations across Pune, Mumbai, Delhi, Bengaluru, Hyderabad, Solapur!\n")
    return active_stations

def fetch_latest_readings(sensor_id, limit=3):
    """
    Fetches the newest available readings (latest first).
    """
    url = f"{BASE_URL}/sensors/{sensor_id}/measurements"
    params = {
        "limit": limit,
        "order_by": "datetime",
        "sort_order": "desc"
    }
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=(5, 10))
        if res.status_code == 200:
            return res.json().get("results", [])
    except requests.exceptions.RequestException:
        pass
    return []

def run_extraction():
    stations = discover_all_active_stations()
    if not stations:
        print("⚠️ No active stations found.")
        return None

    print(f"��� Ingesting live telemetry across all {len(stations)} active stations...")
    rows = []
    current_ingest_time = datetime.now(timezone.utc).isoformat()

    for st in stations:
        for sensor in st["sensors"]:
            param = (sensor.get("parameter") or {}).get("name")
            sensor_id = sensor.get("id")

            readings = fetch_latest_readings(sensor_id, limit=3)
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
                        "units": (sensor.get("parameter") or {}).get("units"),
                        "measurement_value": float(val),
                        "measured_at_utc": dt_to,
                        "ingested_at_utc": current_ingest_time
                    })

    if not rows:
        print("⚠️ No live telemetry returned.")
        return None

    df = pd.DataFrame(rows)

    landing_dir = "data/landing"
    os.makedirs(landing_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    csv_file = f"{landing_dir}/openaq_raw_{timestamp}.csv"
    df.to_csv(csv_file, index=False)

    print(f"\n Extraction Complete!")
    print(f" Saved: {csv_file}")
    print(f" Total Records Extracted: {len(df)}")
    print(f"\n--- Station Count by City ---")
    print(df.groupby("city")["local_area"].nunique())
    return csv_file

if __name__ == "__main__":
    run_extraction()
