import requests
import json
import traceback
from sqlalchemy import create_engine
from datetime import datetime
import dbinfo
import time

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

def main():
    USER = "root"
    PASSWORD = "shayan1664"
    PORT = "3306"
    DB = "local_databaseopenweather"
    URI = "127.0.0.1"

    connection_string = "mysql+pymysql://{}:{}@{}:{}/{}".format(USER, PASSWORD, URI, PORT, DB)

    engine = create_engine(connection_string, echo = True)

    try:
        r = requests.get(dbinfo.CURRENT_WEATHER_URI, params={"lat": dbinfo.LAT, "lon": dbinfo.LON, "appid": dbinfo.WEATHER_KEY, "units": "metric"})
        print(r)

        if r.status_code == 200:
            current_to_db(r.text, engine)
        else:
            print(r.text)

        time.sleep(5*60)
    except:
        print(traceback.format_exc())

# CTRL + Z or CTRL + C to stop it
main()   