# Weather API – Get current weather
from flask import Flask, render_template, jsonify
import requests
import os 
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv(dotenv_path="var.env")

#WEATHER_API_KEY = "70fc10d7ab1946ec517456c3876b9e27"
#CITY_NAME = "Dublin,IE"



def get_weather_data():
    #url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY_NAME}&appid={WEATHER_API_KEY}&units=metric"
    #response = requests.get(url)
    #return response.json() if response.status_code == 200 else {}
    r = requests.get(os.getenv('CURRENT_WEATHER_URI'), params={"appid": os.getenv('OPENWEATHER_API_KEY'), "q": os.getenv('CITY'), "units": "metric"})
    return r.json() if r.status_code == 200 else {}

def get_forecast():
    r = requests.get(os.getenv('FORECAST_WEATHER_URI'), params={"appid": os.getenv('OPENWEATHER_API_KEY'), "q": os.getenv('CITY'), "units": "metric"})
    return r.json() if r.status_code == 200 else {}
    

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/weather")
def weather():
    return jsonify(get_weather_data())

@app.route("/api/forecast")
def forecast():
    return jsonify(get_forecast())


if __name__ == "__main__":
    app.run(debug=True)