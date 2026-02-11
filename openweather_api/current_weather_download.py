import requests
import traceback
import datetime
import time
import os
import dbinfo

"""
Data are in dbinfo.py

WEATHER_KEY = "your_key"
LAT = 53.3498
LON = -6.2603
CURRENT_WEATHER_URI = "https://api.openweathermap.org/data/2.5/weather"
"""

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
            r = requests.get(
                dbinfo.CURRENT_WEATHER_URI,
                params={
                    "lat": dbinfo.LAT,
                    "lon": dbinfo.LON,
                    "units": "metric",
                    "appid": dbinfo.WEATHER_KEY
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
