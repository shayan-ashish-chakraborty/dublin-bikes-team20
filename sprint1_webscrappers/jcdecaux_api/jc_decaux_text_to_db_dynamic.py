import requests
import traceback
import datetime
import time
import os
import dbinfo
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
    USER = "root"
    PASSWORD = "shayan1664"
    PORT = "3306"
    DB = "local_databasejcdecaux"
    URI = "127.0.0.1"

    connection_string = "mysql+pymysql://{}:{}@{}:{}/{}".format(USER, PASSWORD, URI, PORT, DB)

    engine = create_engine(connection_string, echo = True)

    try:
        r = requests.get(dbinfo.STATIONS_URI, params={"apiKey": dbinfo.JCKEY, "contract": dbinfo.NAME})
        stations_to_db(r.text, engine)
        time.sleep(5*60)
    except:
        print(traceback.format_exc())

# CTRL + Z or CTRL + C to stop it
main()   