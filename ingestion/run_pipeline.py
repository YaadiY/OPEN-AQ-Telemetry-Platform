import sys
import time
from datetime import datetime, timezone

from fetch_data import run_extraction
from csv_to_parquet import convert_latest_csv_to_parquet
from upload_to_gcs import upload_bronze_parquet_to_gcs

def main():
    start_time = time.time()
    print("=" * 65)
    print(f" OPENAQ DATA PIPELINE STARTED: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 65)

    try:
        # Stage 1: Extraction from OpenAQ API to Landing CSV
        print("\n[STAGE 1/3] Extracting telemetry from OpenAQ API...")
        csv_file = run_extraction(max_stations=25, measurements_per_sensor=5)
        if not csv_file:
            print("❌ Pipeline aborted: Extraction failed.")
            sys.exit(1)

        # Stage 2: Schema validation, typing, and Parquet serialization
        print("\n[STAGE 2/3] Converting raw CSV to strongly-typed Parquet...")
        parquet_file = convert_latest_csv_to_parquet()
        if not parquet_file:
            print("❌ Pipeline aborted: Parquet conversion failed.")
            sys.exit(1)

        # Stage 3: Synchronize with GCS Data Lake
        print("\n[STAGE 3/3] Uploading Parquet to Google Cloud Storage...")
        upload_bronze_parquet_to_gcs()

        elapsed = round(time.time() - start_time, 2)
        print("\n" + "=" * 65)
        print(f" PIPELINE COMPLETED SUCCESSFULLY IN {elapsed}s")
        print("=" * 65)

    except Exception as e:
        print(f"\n❌ Pipeline failed with unexpected exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
