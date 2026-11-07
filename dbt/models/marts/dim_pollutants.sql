select
    'pm25' as pollutant,
    'Particulate Matter < 2.5 µm' as display_name,
    'µg/m³' as units,
    'Fine inhalable particles that penetrate deep into lungs and bloodstream' as health_description,
    15.0 as who_annual_safe_limit_ugm3
union all
select
    'pm10' as pollutant,
    'Particulate Matter < 10 µm' as display_name,
    'µg/m³' as units,
    'Inhalable coarse particles originating from dust, construction, and traffic' as health_description,
    45.0 as who_annual_safe_limit_ugm3
