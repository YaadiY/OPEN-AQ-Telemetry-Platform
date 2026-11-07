import os
import glob
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

def upload_bronze_parquet_to_gcs():
    if not BUCKET_NAME:
        print("❌ Error: GCS_BUCKET_NAME is not set in your .env file.")
        return

    print(f"Connecting to Google Cloud Storage (Bucket: '{BUCKET_NAME}')...")
    
    # 1. Initialize client using Application Default Credentials (ADC)
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)

    # 2. Find local Parquet files in data/bronze/
    local_files = glob.glob("data/bronze/*.parquet")
    if not local_files:
        print("⚠️ No parquet files found in data/bronze/. Run csv_to_parquet.py first.")
        return

    print(f"Found {len(local_files)} Parquet file(s) to upload.\n")

    # 3. Upload each file to GCS
    for file_path in local_files:
        file_name = os.path.basename(file_path)
        gcs_destination = f"bronze/{file_name}"
        blob = bucket.blob(gcs_destination)

        # Check if file already exists in GCS (Idempotency)
        if blob.exists():
            print(f"   ⏩ Skipping '{file_name}' (already exists in gs://{BUCKET_NAME}/{gcs_destination})")
            continue

        print(f"   ⬆️ Uploading '{file_name}' to gs://{BUCKET_NAME}/{gcs_destination}...")
        blob.upload_from_filename(file_path)
        print(f"   ✅ Upload complete: gs://{BUCKET_NAME}/{gcs_destination}")

    print(f"\nAll Bronze files synchronized with GCS Data Lake!")

if __name__ == "__main__":
    upload_bronze_parquet_to_gcs()
