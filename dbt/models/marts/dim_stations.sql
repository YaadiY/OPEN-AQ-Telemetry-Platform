with stg as (
    select * from {{ ref('stg_openaq__air_quality') }}
),
ranked_stations as (
    select
        station_id,
        station_name,
        city,
        local_area,
        latitude,
        longitude,
        row_number() over (
            partition by station_id 
            order by measured_at_utc desc, ingested_at_utc desc
        ) as rn
    from stg
),
station_aggregates as (
    select
        station_id,
        count(distinct sensor_id) as total_sensors_tracked,
        min(measured_at_utc) as first_recorded_at,
        max(measured_at_utc) as latest_recorded_at
    from stg
    group by station_id
)
select
    r.station_id,
    r.station_name,
    r.city,
    r.local_area,
    r.latitude,
    r.longitude,
    a.total_sensors_tracked,
    a.first_recorded_at,
    a.latest_recorded_at
from ranked_stations r
join station_aggregates a on r.station_id = a.station_id
where r.rn = 1
