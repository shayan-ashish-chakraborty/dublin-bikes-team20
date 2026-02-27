import os
import requests
import traceback
import datetime
import time
import json
from sqlalchemy import create_engine
from dotenv import load_dotenv
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("current_weather.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def hourly_to_db(text, in_engine):

    data = json.loads(text)

    forecasts = data.get("list", [])

    print("Number of forecast entries:", len(forecasts))

    for item in forecasts:

        dt = datetime.datetime.fromtimestamp(item.get("dt"))
        future_dt = dt   # for forecast, dt itself is future

        main = item.get("main", {})
        wind = item.get("wind", {})
        weather = item.get("weather", [{}])[0]

        rain_3h = None
        snow_3h = None

        if "rain" in item and "3h" in item["rain"]:
            rain_3h = item["rain"]["3h"]

        if "snow" in item and "3h" in item["snow"]:
            snow_3h = item["snow"]["3h"]

        vals = (
            dt,
            future_dt,
            main.get("feels_like"),
            main.get("humidity"),
            main.get("pressure"),
            main.get("temp"),
            weather.get("id"),
            wind.get("speed"),
            wind.get("gust"),
            rain_3h,
            snow_3h
        )

        in_engine.execute("""
            INSERT INTO hourly
            (dt, future_dt, feels_like, humidity, pressure,
             temp, weather_id, wind_speed, wind_gust,
             rain_3h, snow_3h)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                feels_like = VALUES(feels_like),
                humidity = VALUES(humidity),
                pressure = VALUES(pressure),
                temp = VALUES(temp),
                wind_speed = VALUES(wind_speed),
                wind_gust = VALUES(wind_gust),
                rain_3h = VALUES(rain_3h),
                snow_3h = VALUES(snow_3h);
        """, vals)

def data_config():
    if os.path.exists("var.env"):
        load_dotenv(dotenv_path="var.env")

    USER = os.getenv("DB_USER")
    PASSWORD = os.getenv("DB_PASSWORD")
    PORT = os.getenv("DB_PORT")
    DB = os.getenv("DB_NAME_WEATHER")
    URI = os.getenv("DB_HOST")

    connection_string = f"mysql+pymysql://{USER}:{PASSWORD}@{URI}:{PORT}/{DB}"

    engine = create_engine(connection_string, echo=True)
    return engine

def hourly_weather_to_db(engine):
    logger.info("Program started")

    try:
        r = requests.get(
            os.getenv('FORECAST_WEATHER_URI'),
            params={
                "q": os.getenv('CITY'),
                "appid": os.getenv('OPENWEATHER_API_KEY'),
                "units": "metric"
            }
        )
        logger.info(r)
        hourly_to_db(r.text, engine)
    except:
        logger.info(traceback.format_exc())


