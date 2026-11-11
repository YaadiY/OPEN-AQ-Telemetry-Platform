# 📖 OpenAQ Telemetry Platform - Data Dictionary

This document outlines the schema, data types, constraints, and descriptions for all tables in the **BigQuery Data Marts layer (`openaq_marts`)**.

---

## 1. Fact Table: `fct_air_quality_measurements`

* **Materialization:** Table
* **Partitioning:** Daily on `measurement_date`
* **Clustering:** `city`, `local_area`, `pollutant`
* **Volume:** 287,600+ records (2016–2026)

| Column Name | Data Type | Constraint | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- |
| `measurement_id` | `INT64` | **Primary Key** | Surrogate key generated via `FARM_FINGERPRINT(concat(station_id, '-', sensor_id, '-', measured_at_utc))` | `-58492049182948291` |
| `station_id` | `INT64` | **Foreign Key** | References `dim_stations.station_id` | `12238734` |
| `sensor_id` | `INT64` | Not Null | OpenAQ unique sensor identifier | `54219` |
| `city` | `STRING` | Clustered | Canonical city name | `"Delhi"`, `"Mumbai"`, `"Pune"` |
| `local_area` | `STRING` | Clustered | Canonical neighborhood/locality parsed from station text | `"Anand Vihar"`, `"Dhankawadi"` |
| `pollutant` | `STRING` | Clustered | Pollutant parameter code (`pm25` or `pm10`) | `"pm25"`, `"pm10"` |
| `measurement_value` | `FLOAT64` | Not Null | Recorded pollutant concentration in $\mu\text{g/m}^3$ | `84.32` |
| `measured_at_utc` | `TIMESTAMP` | Not Null | Exact UTC timestamp of telemetry reading | `2026-11-09 18:30:00 UTC` |
| `measurement_date` | `DATE` | Partition Key | Date portion of `measured_at_utc` used for partition pruning | `2026-11-09` |
| `ingested_at_utc` | `TIMESTAMP` | Not Null | UTC timestamp when the pipeline extracted this record | `2026-11-10 08:48:16 UTC` |

---

## 2. Dimension Table: `dim_stations`

* **Materialization:** Table
* **Total Rows:** 173 unique monitoring stations

| Column Name | Data Type | Constraint | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- |
| `station_id` | `INT64` | **Primary Key** | Unique OpenAQ station identifier | `8172` |
| `station_name` | `STRING` | Not Null | Full official station designation | `"Anand Vihar, Delhi - DPCC"` |
| `city` | `STRING` | Not Null | Normalized metropolitan jurisdiction | `"Delhi"` |
| `local_area` | `STRING` | Not Null | Parsed micro-neighborhood / locality | `"Anand Vihar"` |
| `latitude` | `FLOAT64` | Valid Coordinate | Decimal GPS latitude | `28.6476` |
| `longitude` | `FLOAT64` | Valid Coordinate | Decimal GPS longitude | `77.3158` |
| `total_sensors_tracked` | `INT64` | $\ge 1$ | Count of distinct sensors active on this station | `2` |
| `first_recorded_at` | `TIMESTAMP` | Not Null | Earliest recorded telemetry timestamp in platform history | `2016-01-30 18:30:00 UTC` |
| `latest_recorded_at` | `TIMESTAMP` | Not Null | Most recent recorded telemetry timestamp | `2026-11-10 08:30:00 UTC` |

---

## 3. Dimension Table: `dim_pollutants`

* **Materialization:** Table
* **Total Rows:** 2 rows (`pm25`, `pm10`)

| Column Name | Data Type | Constraint | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- |
| `pollutant` | `STRING` | **Primary Key** | Parameter code (`pm25`, `pm10`) | `"pm25"` |
| `display_name` | `STRING` | Not Null | Human-readable scientific designation | `"Particulate Matter < 2.5 µm"` |
| `units` | `STRING` | Not Null | Standard measurement unit | `"µg/m³"` |
| `health_description` | `STRING` | Description | Epidemiological risk summary | `"Fine inhalable particles..."` |
| `who_annual_safe_limit_ugm3` | `FLOAT64` | WHO Standard | World Health Organization annual safety threshold | `5.0` (PM2.5) / `15.0` (PM10) |
| `cpcb_24h_safe_limit_ugm3` | `FLOAT64` | Indian Standard | Central Pollution Control Board 24h safety limit | `60.0` (PM2.5) / `100.0` (PM10) |
