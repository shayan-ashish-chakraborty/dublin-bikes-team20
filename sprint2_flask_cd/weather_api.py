# Weather API – Get current weather
from flask import Flask, render_template, jsonify
import requests
app = Flask(__name__)
WEATHER_API_KEY = "70fc10d7ab1946ec517456c3876b9e27"
CITY_NAME = "Dublin,IE"

def get_weather_data():
    url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY_NAME}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else {}
    

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/weather")
def weather():
    return jsonify(get_weather_data())


if __name__ == "__main__":
    app.run(debug=True)