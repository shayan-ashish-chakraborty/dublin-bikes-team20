from sprint1_webscrappers.webscrapping.openweather_text_to_db_current import db_connection, current_weather_to_db
import time

engine = db_connection()

while True:
    with engine.begin() as conn:
        current_weather_to_db(engine)
    time.sleep(5*60)