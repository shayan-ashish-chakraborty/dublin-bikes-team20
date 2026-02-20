from flask import Flask, g, render_template, jsonify
import json
from sqlalchemy.engine.create import create_engine

USER = "root"
PASSWORD = "shayan1664"
PORT = "3306"
DB = "local_databaseopenweather"   
URI = "127.0.0.1"

app = Flask(__name__, static_url_path='')

#Connect to the database
def connect_to_db():
    connection_string = "mysql+pymysql://{}:{}@{}:{}/{}".format(USER, PASSWORD, URI, PORT, DB)
    engine = create_engine(connection_string, echo = True)
    
    return engine

# Create the engine variable and store it in the global Flask variable 'g'
def get_db():
    db_engine = getattr(g, '_database', None)
    if db_engine is None:
        db_engine = g._database = connect_to_db()
    return db_engine

# Show all weather in json
@app.route('/weather')
def get_weather():
    engine = get_db()
    
    weather = []
    rows = engine.execute("SELECT * from current;") #current is the name of your table in the database
    
    for row in rows:
        weather.append(dict(row))
    
    return jsonify(weather=weather)

#Show hourly in json
@app.route('/hourly')
def get_hourly():
    engine = get_db()
    
    hourly = []
    rows = engine.execute("SELECT * from hourly;") #hourly is the name of your table in the database
    
    for row in rows:
        hourly.append(dict(row))
    
    return jsonify(hourly=hourly)


if __name__ == "__main__":
    app.run(debug=True)