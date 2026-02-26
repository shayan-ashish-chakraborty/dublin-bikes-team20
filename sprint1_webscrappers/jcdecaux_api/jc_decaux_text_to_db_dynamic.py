import requests
import traceback
import datetime
import time
import os
import json
import sqlalchemy as sqla
from sqlalchemy import create_engine
import traceback
import glob
import os
from pprint import pprint
import simplejson as json
import requests
import time
from IPython.display import display
from datetime import datetime
from dotenv import load_dotenv


def stations_to_db(text, in_engine):
    # let us load the stations from the text received from jcdecaux
    stations = json.loads(text)

    # print type of the stations object, and number of stations
    print(type(stations), len(stations))
    
    # let us print the type of the object stations (a dictionary) and load the content
    for station in stations:
        print(type(station))

        # let us load only the parts that we have included in our db:
        # address VARCHAR(256), 
        # banking INTEGER,
        # bikestands INTEGER,
        # name VARCHAR(256),
        # status VARCHAR(256))
        
        # let us extract the relevant info from the dictionary
        vals = (
                int(station.get('number')),
                int(station.get('available_bikes')),
                int(station.get('available_bike_stands')),
                datetime.fromtimestamp(station.get("last_update")/1000),
                station.get('status')
                )

        
        # now let us use the engine to insert into the stations
        in_engine.execute("""
                            INSERT INTO availability
                            (number, available_bikes, available_bike_stands, last_update, status)
                            VALUES (%s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                            available_bikes = VALUES(available_bikes),
                            available_bike_stands = VALUES(available_bike_stands),
                            status = VALUES(status);
                            """, vals)



def main():
    if os.path.exists("var.env"):
        load_dotenv(dotenv_path="var.env")

    USER = os.getenv("DB_USER")
    PASSWORD = os.getenv("DB_PASSWORD")
    PORT = os.getenv("DB_PORT")
    DB = os.getenv("DB_NAME_JCDECAUX")
    URI = os.getenv("DB_HOST")

    connection_string = "mysql+pymysql://{}:{}@{}:{}/{}".format(USER, PASSWORD, URI, PORT, DB)

    engine = create_engine(connection_string, echo = True)

    try:
        r = requests.get(os.getenv('STATIONS_URI'), params={"apiKey": os.getenv('JCDECAUX_API_KEY'), "contract": os.getenv('CITY')})
        stations_to_db(r.text, engine)
        time.sleep(5*60)
    except:
        print(traceback.format_exc())

# CTRL + Z or CTRL + C to stop it
main()   