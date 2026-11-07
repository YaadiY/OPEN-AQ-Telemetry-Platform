with stg as (
    select * from {{ ref('stg_openaq__air_quality') }}
)

select
    station_id,
    station_name,
    city,
    latitude,
    longitude,
    count(distinct sensor_id) as total_sensors_tracked,
    min(measured_at_utc) as first_recorded_at,
    max(measured_at_utc) as latest_recorded_at
from stg
group by station_id, station_name, city, latitude, longitude
