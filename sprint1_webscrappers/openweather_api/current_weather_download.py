import requests
import traceback
import datetime
import time
import os
from dotenv import load_dotenv


# Data are in dbinfo.py


# Will be used to store text in a file
def write_to_file(text):

    # Create folder weather_data if it doesn't exist
    if not os.path.exists('weather_data'):
        os.mkdir('weather_data')
        print("Folder 'weather_data' created!")
    else:
        print("Folder 'weather_data' already exists.")

    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    with open(f"weather_data/weather_{now}.json", "w") as f:
        f.write(text)


# Empty for now 
def write_to_db(text):
    return 0


def main():
    while True:
        try:
            if os.path.exists("var.env"):
                load_dotenv(dotenv_path="var.env")
            r = requests.get(
                os.getenv('CURRENT_WEATHER_URI'),
                params={
                    "lat": os.get('LAT'),
                    "lon": os.get('LON'),
                    "units": "metric",
                    "appid": os.get('OPENWEATHER_API_KEY')
                }
            )

            print(r)
            write_to_file(r.text)

            # Sleep 5 minutes (weather doesn't change fast)
            time.sleep(5 * 60)

        except:
            print(traceback.format_exc())


# CTRL + Z to stop it
main()
