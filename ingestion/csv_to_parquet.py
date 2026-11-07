import os
import glob
import pandas as pd

def convert_latest_csv_to_parquet():
    landing_dir = "data/landing"
    bronze_dir = "data/bronze"
    os.makedirs(bronze_dir, exist_ok=True)

    # 1. Locate the latest raw CSV
    csv_files = glob.glob(f"{landing_dir}/*.csv")
    if not csv_files:
        print("❌ No CSV files found in data/landing/. Run extract_to_csv.py first.")
        return None

    latest_csv = max(csv_files, key=os.path.getmtime)
    print(f" Reading raw CSV: {latest_csv}")

    # 2. Read CSV
    df = pd.read_csv(latest_csv)
    raw_size = os.path.getsize(latest_csv)

    # 3. Schema Enforcement (Type Casting)
    print("⚙️ Enforcing schema and datatypes...")
    df["station_id"] = df["station_id"].astype("int64")
    df["sensor_id"] = df["sensor_id"].astype("int64")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["measurement_value"] = pd.to_numeric(df["measurement_value"], errors="coerce")
    
    # Enforce UTC Timestamps
    df["measured_at_utc"] = pd.to_datetime(df["measured_at_utc"], utc=True)
    df["ingested_at_utc"] = pd.to_datetime(df["ingested_at_utc"], utc=True)

    # Sort descending by measurement time
    df = df.sort_values(by="measured_at_utc", ascending=False).reset_index(drop=True)

    # 4. Write to Parquet in Bronze Layer
    base_name = os.path.basename(latest_csv).replace("openaq_raw_", "openaq_clean_").replace(".csv", ".parquet")
    parquet_path = f"{bronze_dir}/{base_name}"

    df.to_parquet(parquet_path, engine="pyarrow", compression="snappy", index=False)
    parquet_size = os.path.getsize(parquet_path)

    # 5. Display comparison
    compression_ratio = (1 - (parquet_size / raw_size)) * 100
    print(f"\n��� Step 2 Complete: Parquet Serialization Done!")
    print(f"��� Parquet Location: {parquet_path}")
    print(f"��� Raw CSV Size:     {raw_size} bytes")
    print(f"��� Parquet Size:     {parquet_size} bytes")
    print(f"⚡ Storage Saved:    {compression_ratio:.1f}%")
    print(f"\n--- Parquet Schema ---")
    print(df.dtypes)
    return parquet_path

if __name__ == "__main__":
    convert_latest_csv_to_parquet()
