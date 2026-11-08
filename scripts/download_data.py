# Downloads the raw data for The Fifth Season (Lahore smog project).
# Run from the repo folder:  python scripts/download_data.py
# Needs internet only, no extra packages.
import gzip, os, re, urllib.request

BUCKET = "https://openaq-data-archive.s3.amazonaws.com"
LOCATION = 8664  # U.S. Consulate Lahore monitor on OpenAQ
PM_DIR = "data/raw/openaq_8664"
WX_DIR = "data/raw/weather"
os.makedirs(PM_DIR, exist_ok=True)
os.makedirs(WX_DIR, exist_ok=True)


def get(url):
    return urllib.request.urlopen(url, timeout=60).read()


# 1. PM2.5: OpenAQ keeps one gzipped CSV per day, grouped by year and month
files = 0
for year in range(2019, 2026):
    for month in range(1, 13):
        prefix = f"records/csv.gz/locationid={LOCATION}/year={year}/month={month:02d}/"
        listing = get(f"{BUCKET}/?list-type=2&prefix={prefix}").decode()
        for key in re.findall(r"<Key>(.*?)</Key>", listing):
            path = os.path.join(PM_DIR, os.path.basename(key)[:-3])  # drop .gz
            if not os.path.exists(path):
                with open(path, "wb") as f:
                    f.write(gzip.decompress(get(f"{BUCKET}/{key}")))  # unzip so Prep can read it
            files += 1
    print(year, "done, files so far:", files)

# 2. Hourly weather for the same place and period (ERA5 via Open-Meteo)
weather_url = (
    "https://archive-api.open-meteo.com/v1/archive"
    "?latitude=31.56&longitude=74.336"
    "&start_date=2019-05-23&end_date=2025-03-04"
    "&hourly=temperature_2m,relative_humidity_2m,precipitation,"
    "wind_speed_10m,wind_direction_10m,boundary_layer_height"
    "&timezone=Asia%2FKarachi&format=csv"
)
with open(os.path.join(WX_DIR, "lahore_weather_hourly.csv"), "wb") as f:
    f.write(get(weather_url))

print("Done:", files, "PM2.5 daily files + 1 weather file")
