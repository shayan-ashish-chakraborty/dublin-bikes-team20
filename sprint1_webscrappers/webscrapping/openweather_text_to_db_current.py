import os
import requests
import json
import traceback
from sqlalchemy import create_engine
from datetime import datetime
import time
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


def current_to_db(text, in_engine):

    data = json.loads(text)

    # Convert the timestamps
    dt = datetime.fromtimestamp(data.get('dt'))
    sunrise = datetime.fromtimestamp(data.get('sys').get('sunrise'))
    sunset = datetime.fromtimestamp(data.get('sys').get('sunset'))

    rain_1h = None
    snow_1h = None

    if "rain" in data and "1h" in data["rain"]:
        rain_1h = data["rain"]["1h"]

    if "snow" in data and "1h" in data["snow"]:
        snow_1h = data["snow"]["1h"]    

    vals = (
        dt,
        data["main"]["feels_like"],
        data["main"]["humidity"],
        data["main"]["pressure"],
        sunrise,
        sunset,
        data["main"]["temp"],
        data["weather"][0]["id"],
        data["wind"]["speed"],
        data["wind"].get("gust"),
        rain_1h,
        snow_1h
    )

    in_engine.execute("""
        INSERT INTO current
        (dt, feels_like, humidity, pressure, sunrise, sunset,
         temp, weather_id, wind_speed, wind_gust,
         rain_1h, snow_1h)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s)
        ON DUPLICATE KEY UPDATE
            feels_like = VALUES(feels_like),
            humidity = VALUES(humidity),
            pressure = VALUES(pressure),
            temp = VALUES(temp),
            wind_speed = VALUES(wind_speed),
            wind_gust = VALUES(wind_gust),
            rain_1h = VALUES(rain_1h),
            snow_1h = VALUES(snow_1h);
    """, vals)


def data_config():
    if os.path.exists("var.env"):
        load_dotenv(dotenv_path="var.env")

    USER = os.getenv("DB_USER")
    PASSWORD = os.getenv("DB_PASSWORD")
    PORT = os.getenv("DB_PORT")
    DB = os.getenv("DB_NAME_WEATHER")
    URI = os.getenv("DB_HOST")

    connection_string = "mysql+pymysql://{}:{}@{}:{}/{}".format(USER, PASSWORD, URI, PORT, DB)

    engine = create_engine(connection_string, echo=True)
    return engine

def current_weather_to_db(engine):
    logger.info("Program started")
    try:
        r = requests.get(os.getenv('CURRENT_WEATHER_URI'), params={"lat": os.getenv('LAT'), "lon": os.getenv('LON'),
                                                                   "appid": os.getenv('OPENWEATHER_API_KEY'),
                                                                   "units": "metric"})
        logger.info(r)
        if r.status_code == 200:
            current_to_db(r.text, engine)
            logger.info('Write to DB successfully')
    except:
        logger.info(traceback.format_exc())

# CTRL + Z or CTRL + C to stop it
#if __name__ == "__main__":
