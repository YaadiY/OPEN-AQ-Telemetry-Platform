import os
import json
import requests
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("OPENAQ_API_KEY")
BASE_URL = "https://api.openaq.org/v3"
headers = {
    "X-API-Key": API_KEY,
    "Accept": "application/json"
}
def find_active_sensor_and_inspect():
    """
    1. Finds the most recently updated station with active sensors.
    2. Fetches live measurements from that active sensor.
    """
    print("1. Searching for an actively reporting monitoring station...")
    locations_url = f"{BASE_URL}/locations"
    
    # Sort descending by ID to get the newest, actively transmitting stations
    params = {
        "limit": 5,
        "order_by": "id",
        "sort_order": "desc"
    }
    try:
        res = requests.get(locations_url, headers=headers, params=params, timeout=(5, 10))
        res.raise_for_status()
        locations = res.json().get("results", [])
        active_sensor_id = None
        active_sensor_name = None
        station_name = None
        # Loop through stations to find one with active datetimeLast and sensors
        for loc in locations:
            sensors = loc.get("sensors", [])
            last_reported = loc.get("datetimeLast")
            
            if last_reported and sensors:
                active_sensor_id = sensors[0].get("id")
                active_sensor_name = sensors[0].get("name")
                station_name = loc.get("name")
                print(f"   Found active station: '{station_name}'")
                print(f"   Last reported: {last_reported.get('utc')}")
                print(f"   Selected active sensor ID: {active_sensor_id} ({active_sensor_name})\n")
                break
        if not active_sensor_id:
            print("⚠️ No active sensors found in the sample.")
            return
        # 2. Fetch measurements for this confirmed active sensor
        print(f"2. Fetching real telemetry from sensor {active_sensor_id}...")
        measurements_url = f"{BASE_URL}/sensors/{active_sensor_id}/measurements"
        m_res = requests.get(measurements_url, headers=headers, params={"limit": 1}, timeout=(5, 10))
        m_res.raise_for_status()
        measurements = m_res.json().get("results", [])
        if measurements:
            print(f"✅ Successfully extracted live telemetry!\n")
            print("--- Live Measurement Payload (JSON) ---")
            print(json.dumps(measurements[0], indent=2))
        else:
            print("⚠️ Sensor has metadata but no recent measurements.")
    except requests.exceptions.RequestException as e:
        print(f"❌ API Request failed: {e}")
if __name__ == "__main__":
    find_active_sensor_and_inspect()