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
        # number INTEGER NOT NULL PRIMARY KEY,
        # address VARCHAR(256), 
        # banking INTEGER,
        # bikestands INTEGER,
        # name VARCHAR(256),
        # position_lat FLOAT,
        # position_lng FLOAT,
        # status VARCHAR(256))
        
        # let us extract the relevant info from the dictionary
        vals = (int(station.get('number')), station.get('address'), int(station.get('banking')), int(station.get('bike_stands')), 
                station.get('name'), float(station.get('position').get('lat')), float(station.get('position').get('lng')), station.get('status'))
        
        # now let us use the engine to insert into the stations
        in_engine.execute("""
                          INSERT INTO station (number, address, banking, bike_stands, name, position_lat, position_lng, status) 
                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                          """, vals)


def main():
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