# Weather Forecast API (5-day / 3-hour forecast)
from flask import Flask, jsonify, render_template
import requests

app = Flask(__name__)

WEATHER_API_KEY = "70fc10d7ab1946ec517456c3876b9e27"   # API key
CITY_NAME = "Dublin,IE"                                  # city name


@app.route("/api/forecast")
def get_forecast():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CITY_NAME}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    return jsonify(response.json())

@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5001)