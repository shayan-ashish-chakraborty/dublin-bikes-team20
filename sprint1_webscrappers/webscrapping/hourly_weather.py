from sprint1_webscrappers.webscrapping.openweather_text_to_db_hourly import data_config, hourly_weather_to_db
import time

while True:
    engine = data_config()
    hourly_weather_to_db(engine)
    time.sleep(5*60)