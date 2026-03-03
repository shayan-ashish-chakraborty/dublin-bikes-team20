from sprint1_webscrappers.webscrapping.openweather_text_to_db_hourly import db_connection, hourly_weather_to_db
import time
engine = db_connection()

while True:
    with engine.begin() as conn:
        hourly_weather_to_db(engine)
    time.sleep(5*60)

