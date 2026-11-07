with source_data as (
    select * from {{ source('openaq_source', 'ext_air_quality') }}
),

deduplicated as (
    select
        cast(station_id as int64) as station_id,
        trim(station_name) as station_name,
        trim(city) as city,
        cast(latitude as float64) as latitude,
        cast(longitude as float64) as longitude,
        cast(sensor_id as int64) as sensor_id,
        lower(trim(pollutant)) as pollutant,
        trim(units) as units,
        cast(measurement_value as float64) as measurement_value,
        
        -- Convert Parquet INT64 (nanoseconds) into BigQuery Timestamp
        timestamp_micros(div(cast(measured_at_utc as int64), 1000)) as measured_at_utc,
        date(timestamp_micros(div(cast(measured_at_utc as int64), 1000))) as measurement_date,
        timestamp_micros(div(cast(ingested_at_utc as int64), 1000)) as ingested_at_utc

    from source_data
    where measurement_value is not null
      and measured_at_utc is not null

    -- Idempotent deduplication: Keep the latest ingested record
    qualify row_number() over (
        partition by station_id, sensor_id, measured_at_utc 
        order by ingested_at_utc desc
    ) = 1
)

select * from deduplicated
