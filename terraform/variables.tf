variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
  default     = "project-acf803b4-e926-4de8-aa7"
}

variable "region" {
  description = "GCP Region for resources"
  type        = string
  default     = "asia"
}

variable "gcs_bucket_name" {
  description = "Globally unique name of the Bronze GCS Bucket"
  type        = string
  default     = "openaq-telemetry-bronze-acf803b4"
}

variable "bq_raw_dataset" {
  description = "BigQuery dataset for raw and staging data"
  type        = string
  default     = "openaq_raw"
}

variable "bq_marts_dataset" {
  description = "BigQuery dataset for dbt dimensional marts"
  type        = string
  default     = "openaq_marts"
}
