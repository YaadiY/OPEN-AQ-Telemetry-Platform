terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Provider connects using your local Application Default Credentials (ADC)
provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Google Cloud Storage (Bronze Data Lake Bucket)
resource "google_storage_bucket" "bronze_bucket" {
  name          = var.gcs_bucket_name
  location      = var.region
  force_destroy = true # Allows easy tear-down during dev/testing

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30 # Automatically manages storage costs for older files
    }
    action {
      type = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
}

# 2. BigQuery Dataset: Raw / Staging Layer
resource "google_bigquery_dataset" "raw_dataset" {
  dataset_id                  = var.bq_raw_dataset
  friendly_name               = "OpenAQ Raw Staging"
  description                 = "Staging dataset for raw OpenAQ telemetry loaded from GCS"
  location                    = var.region
  delete_contents_on_destroy  = true
}

# 3. BigQuery Dataset: Gold / Marts Layer
resource "google_bigquery_dataset" "marts_dataset" {
  dataset_id                  = var.bq_marts_dataset
  friendly_name               = "OpenAQ Analytical Marts"
  description                 = "Gold dimensional star-schema models transformed by dbt"
  location                    = var.region
  delete_contents_on_destroy  = true
}
