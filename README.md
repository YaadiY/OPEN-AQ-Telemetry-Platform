# 🌍 End-to-End Cloud Data Platform (OpenAQ Telemetry)

[![GCP](https://img.shields.io/badge/Google_Cloud-4285F4?style=flat&logo=google-cloud&logoColor=white)](https://cloud.google.com/)
[![Terraform](https://img.shields.io/badge/Terraform-844FBA?style=flat&logo=terraform&logoColor=white)](https://www.terraform.io/)
[![BigQuery](https://img.shields.io/badge/BigQuery-669DF6?style=flat&logo=google-cloud&logoColor=white)](https://cloud.google.com/bigquery)
[![dbt](https://img.shields.io/badge/dbt_Core-FF694B?style=flat&logo=dbt&logoColor=white)](https://www.getdbt.com/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)

An enterprise-grade, cloud-native ELT data platform designed to ingest, process, model, and visualize real-time air quality telemetry across major metropolitan hubs in India: **Pune, Mumbai, Delhi, Bengaluru, Hyderabad, and Solapur**.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph ExternalSources ["IoT Source Layer"]
        API["OpenAQ v3 Global REST API\n(/v3/locations & /v3/sensors)"]
    end

    subgraph ContainerizedIngestion ["Containerized Ingestion Service (Docker: python:3.12-slim)"]
        Script1["1. fetch_data.py\n(Station Discovery & JSON Flattening)"]
        Landing["data/landing/\n(Raw Quoted CSV: 42.6 KB)"]
        Script2["2. csv_to_parquet.py\n(Schema Validation & Snappy Compression)"]
        Bronze["data/bronze/\n(Columnar Parquet: 11.8 KB - 72.2% Saved)"]
        Script3["3. upload_to_gcs.py\n(Idempotent Sync via ADC)"]
        
        API -->|HTTPS with X-API-Key| Script1
        Script1 --> Landing
        Landing --> Script2
        Script2 --> Bronze
        Bronze --> Script3
    end

    subgraph GoogleCloudPlatform ["Google Cloud Platform (GCP Lakehouse)"]
        GCS[("Google Cloud Storage (Bronze Lake)\ngs://openaq-telemetry-bronze-acf803b4\n(Uniform Bucket Access, 30-Day Nearline Lifecycle)")]
        BQ_Ext[("BigQuery: Silver Staging\next_air_quality (External Table over *.parquet)")]
        dbt_stg["dbt Staging View: stg_openaq__air_quality\n(Parquet Epoch Decoding + Window Deduplication)"]
        dbt_marts["dbt Gold Marts (Star Schema)\n• dim_stations (25 stations)\n• dim_pollutants (PM2.5, PM10)\n• fct_air_quality_measurements (Partitioned by Date, Clustered by City, Pollutant)"]
        
        Script3 --> GCS
        GCS -->|Federated Wildcard URI: gs://.../*.parquet| BQ_Ext
        BQ_Ext --> dbt_stg
        dbt_stg --> dbt_marts
    end

    subgraph BusinessIntelligence ["BI & Reporting Layer"]
        Looker["Looker Studio Dashboard\n(Station Trends, City Comparisons, NAQI Metrics)"]
        dbt_marts -->|Direct BigQuery Connector| Looker
    end
```

---

## 🛠️ Tech Stack & Key Architectural Decisions

| Layer | Technology | Engineering Rationale |
| :--- | :--- | :--- |
| **Infrastructure as Code** | **Terraform** | Declarative cloud provisioning for GCS buckets and BigQuery datasets. Uniform Bucket-Level Access and 30-day Nearline lifecycle cost automation. |
| **Security & Auth** | **Application Default Credentials (ADC)** | Complying with GCP's `iam.disableServiceAccountKeyCreation` policy to eliminate static JSON private keys on developer machines. |
| **Data Lake (Bronze)** | **Google Cloud Storage (GCS)** | Immutable raw archive; batch loading from GCS to BigQuery is \$0.00 free vs \$0.05/GB BigQuery streaming. |
| **Ingestion Engine** | **Python 3.12 (`uv`)** | Two-stage decoupled ingestion (CSV $\rightarrow$ Parquet) achieving **72.2% storage reduction** using Snappy block compression. |
| **Containerization** | **Docker (Multi-Stage)** | Slim runtime image based on `python:3.12-slim` (~150 MB), isolating C-build tools from production. |
| **Data Warehouse** | **Google BigQuery** | Serverless columnar OLAP with daily table partitioning (`measurement_date`) and multi-column clustering (`city, pollutant`). |
| **Data Modeling** | **dbt Core (v1.12)** | Star schema modeling with window-based idempotent deduplication (`QUALIFY ROW_NUMBER()`) and **11 automated data tests**. |
| **BI & Analytics** | **Looker Studio** | Native BigQuery connection leveraging cluster-pruned sub-second queries for telemetry visualization. |

---

## 📊 Star Schema Dimensional Model

```
                     [ dim_stations ]
                   (Primary Key: station_id)
                   - station_name
                   - city (Pune, Mumbai, Delhi, Bengaluru, Hyderabad, Solapur)
                   - latitude, longitude
                   - total_sensors_tracked
                   - first_recorded_at, latest_recorded_at
                            │
                            │ (1:N)
                            ▼
           [ fct_air_quality_measurements ]
         (Primary Key: measurement_id - Farm Fingerprint)
         - Foreign Key: station_id
         - Foreign Key: sensor_id
         - city
         - pollutant (pm25, pm10)
         - measurement_value (µg/m³)
         - measured_at_utc (Timestamp)
         - measurement_date (Date)
         - ingested_at_utc (Timestamp)
         --------------------------------------------------
         PARTITION BY: measurement_date (Daily Partitioning)
         CLUSTER BY:   city, pollutant
                            ▲
                            │ (N:1)
                            │
                    [ dim_pollutants ]
                  (Primary Key: pollutant)
                  - display_name
                  - units (µg/m³)
                  - health_description
                  - who_annual_safe_limit_ugm3
```

---

## 🧪 Automated Data Quality Testing (11 Tests)

All models are continuously tested using dbt:

* **Uniqueness (3):** Primary key uniqueness on `dim_stations.station_id`, `dim_pollutants.pollutant`, and surrogate key `fct_air_quality_measurements.measurement_id`.
* **Not Null (5):** Strict enforcement on all IDs, measurements, and timestamps.
* **Referential Integrity (1):** Foreign key `relationships` test enforcing every measurement links to a valid station in `dim_stations`.
* **Accepted Values (1):** Ensures `pollutant` contains only `['pm25', 'pm10']`.

```text
Finished running 11 data tests in 6.59s.
Done. PASS=11 WARN=0 ERROR=0 SKIP=0 TOTAL=11
```

---

## 🚀 Reproduction & Setup Guide

### 1. Prerequisites
* Python 3.12 (`uv` recommended)
* Google Cloud SDK (`gcloud`)
* Terraform >= 1.5.0
* Docker & Docker Compose

### 2. Configure Environment & Credentials
```bash
# Clone the repository
git clone https://github.com/YaadiY/OPENAQ_GCP_Platform.git
cd OPENAQ_GCP_Platform

# Setup environment variables
cp .env.example .env
# Edit .env with your OPENAQ_API_KEY and GCP_PROJECT_ID

# Authenticate GCP via Application Default Credentials
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

### 3. Provision Cloud Infrastructure (Terraform)
```bash
cd terraform
terraform init
terraform plan
terraform apply
cd ..
```

### 4. Run Containerized Ingestion Pipeline (Docker)
```bash
docker compose up --build
```

### 5. Create BigQuery External Table & Run dbt
```bash
# Create BigQuery external table over GCS wildcard Parquet URIs
python ingestion/create_external_table.py

# Run and test dbt models
cd dbt
dbt debug --profiles-dir .
dbt run --profiles-dir .
dbt test --profiles-dir .
```

---

## 📚 Study Documentation & Interview Preparation

Comprehensive, self-contained study guides and interview playbooks are preserved in:
* **Architecture Guide:** [`C:\Users\yeleg\VS\Study_docs\openaq_gcp_platform_architecture_guide.md`](file:///C:/Users/yeleg/VS/Study_docs/openaq_gcp_platform_architecture_guide.md)
* **Interview Playbook (14 Questions with Junior vs. Senior Answers):** [`C:\Users\yeleg\VS\Study_docs\openaq_interview_playbook.md`](file:///C:/Users/yeleg/VS/Study_docs/openaq_interview_playbook.md)
