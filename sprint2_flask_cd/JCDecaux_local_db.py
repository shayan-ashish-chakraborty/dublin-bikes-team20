from flask import Flask, jsonify
from sqlalchemy import create_engine
import json

app = Flask(__name__)

USER = "root"
PASSWORD = "shayan1664"
PORT = "3306"
DB = "local_databasejcdecaux"
URI = "127.0.0.1"

connection_string = f"mysql+pymysql://{USER}:{PASSWORD}@{URI}:{PORT}/{DB}"
engine = create_engine(connection_string)

@app.route("/stations")
def get_stations():
    conn = engine.connect()

    result = conn.execute("SELECT * FROM station;")

    stations = []
    for row in result:
        stations.append(dict(row))

    conn.close()

    return jsonify(stations)

@app.route("/availability")
def get_availability():
    conn = engine.connect()

    result = conn.execute("""
        SELECT * FROM availability
        ORDER BY last_update DESC
        LIMIT 100;
    """)

    availability = []
    for row in result:
        availability.append(dict(row))

    conn.close()

    return jsonify(availability)


if __name__ == "__main__":
    app.run(debug=True)