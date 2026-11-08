# Data dictionary

One row per hour, Pakistan time (UTC+5), May 2019 – Feb 2025.

| Column | Type | Unit | Description |
| --- | --- | --- | --- |
| Datetime | Date & Time | | Hour of the reading, Pakistan time |
| PM25 | Number | µg/m³ | Hourly mean PM2.5; empty when the monitor had no valid reading |
| temperature_2m | Number | °C | Air temperature at 2 m |
| relative_humidity_2m | Number | % | Relative humidity at 2 m |
| precipitation | Number | mm | Rain in that hour |
| wind_speed_10m | Number | km/h | Wind speed at 10 m |
| wind_direction_10m | Number | ° | Direction the wind comes from |
| boundary_layer_height | Number | m | Height of the layer the air can mix through; low values trap pollution |
| Season | String | | Smog (Oct–Jan), Spring (Feb–Mar), Pre-monsoon heat (Apr–Jun), Monsoon (Jul–Sep) |
| Hour of Day | Number | | 0–23 |
| Smog Year | Number | | Year the smog season starts (Oct 2024 – Jan 2025 = 2024) |
| AQI Category | String | | EPA 2024 category from Good to Hazardous |
| WHO Multiple | Number | × | PM25 ÷ 15 |
| Stagnation Flag | String | | Stagnant if wind < 5 km/h and boundary layer < 300 m, else Ventilated |
| Data Status | String | | Valid, Imputed, Suspect or Missing |
