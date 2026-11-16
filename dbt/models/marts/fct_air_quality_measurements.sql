{{ config(
    materialized = 'table',
    partition_by = {
      "field": "measurement_date",
      "data_type": "date",
      "granularity": "day"
    },
    cluster_by = ["city", "local_area", "pollutant"]
) }}
with stg as (
    select * from {{ ref('stg_openaq__air_quality') }}
)
select
    farm_fingerprint(concat(cast(station_id as string), '-', cast(sensor_id as string), '-', cast(measured_at_utc as string))) as measurement_id,
    station_id,
    sensor_id,
    city,
    local_area,
    latitude,
    longitude,
    pollutant,
    measurement_value,
    measured_at_utc,
    measurement_date,
    ingested_at_utc
from stg
