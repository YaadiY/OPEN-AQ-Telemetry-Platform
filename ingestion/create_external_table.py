import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
DATASET_ID = "openaq_raw"
TABLE_NAME = "ext_air_quality"

def create_bigquery_external_table():
    client = bigquery.Client(project=PROJECT_ID)
    
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_NAME}"
    gcs_uri = f"gs://{BUCKET_NAME}/bronze/*.parquet"
    
    print(f"Creating External Table in BigQuery: {table_id}")
    print(f"Source Wildcard URI: {gcs_uri}...")

    # Standard BigQuery DDL for Parquet External Table
    ddl_query = f"""
    CREATE OR REPLACE EXTERNAL TABLE `{table_id}`
    OPTIONS (
      format = 'PARQUET',
      uris = ['{gcs_uri}']
    );
    """
    
    job = client.query(ddl_query)
    job.result() # Wait for DDL completion
    print("✅ External Table successfully created!")

    # Run a test query to verify federated scanning across all Parquet files
    test_query = f"""
    SELECT 
      city,
      pollutant,
      COUNT(*) as total_readings,
      ROUND(AVG(measurement_value), 2) as avg_value,
      MIN(measured_at_utc) as earliest_reading,
      MAX(measured_at_utc) as latest_reading
    FROM `{table_id}`
    GROUP BY city, pollutant
    ORDER BY city, pollutant;
    """
    
    print("\n Executing Federated SQL Query directly across GCS Parquet files...")
    query_job = client.query(test_query)
    results = query_job.to_dataframe()
    
    print("\n Federated Query Results (Live from GCS):")
    print(results.to_string(index=False))

if __name__ == "__main__":
    create_bigquery_external_table()
