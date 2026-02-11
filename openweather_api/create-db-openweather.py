import sqlalchemy as sqla
from sqlalchemy import create_engine

USER = "root"
PASSWORD = "shayan1664"
PORT = "3306"
DB = "local_databaseopenweather"   
URI = "127.0.0.1"

connection_string = "mysql+pymysql://{}:{}@{}:{}/{}".format(
    USER, PASSWORD, URI, PORT, DB
)

engine = create_engine(connection_string, echo=True)


for res in engine.execute("SHOW VARIABLES;"):
    print(res)


sql = '''
CREATE TABLE IF NOT EXISTS current (
    dt DATETIME NOT NULL,
    feels_like FLOAT,
    humidity INTEGER,
    pressure INTEGER,
    sunrise DATETIME,
    sunset DATETIME,
    temp FLOAT,
    weather_id INTEGER,
    wind_speed FLOAT,
    wind_gust FLOAT,
    rain_1h FLOAT,
    snow_1h FLOAT,
    PRIMARY KEY (dt)
);
'''

engine.execute(sql)


tab_structure = engine.execute("SHOW COLUMNS FROM current;")
columns = tab_structure.fetchall()
print("current structure:")
print(columns)



sql = '''
CREATE TABLE IF NOT EXISTS hourly (
    dt DATETIME NOT NULL,
    future_dt DATETIME NOT NULL,
    feels_like FLOAT,
    humidity INTEGER,
    pop FLOAT,
    pressure INTEGER,
    temp FLOAT,
    weather_id INTEGER,
    wind_speed FLOAT,
    wind_gust FLOAT,
    rain_3h FLOAT,
    snow_3h FLOAT,
    PRIMARY KEY (dt, future_dt)
);
'''

engine.execute(sql)


tab_structure = engine.execute("SHOW COLUMNS FROM hourly;")
columns = tab_structure.fetchall()
print("hourly structure:")
print(columns)
