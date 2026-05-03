from flask import Flask, jsonify
from sqlalchemy import create_engine
from dotenv import load_dotenv
import json
import os

app = Flask(__name__)

load_dotenv(dotenv_path="var.env")

USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
PORT = os.getenv("DB_PORT")
DB = os.getenv("DB_NAME_JCDECAUX")
URI = os.getenv("DB_HOST")

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
    app.run(host='0.0.0.0',port=5000)