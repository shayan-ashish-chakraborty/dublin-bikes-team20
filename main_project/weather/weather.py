from flask import Blueprint, render_template, jsonify, request
import pathlib
import requests
from datetime import datetime
from ..db import create_engine_for, DbConfig
from ..config import Config
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv
import os 


_BASE      = pathlib.Path(__file__).resolve().parent.parent.parent
_TEMPLATES = _BASE / "main_project" / "templates"
_STATIC    = _BASE / "main_project" / "static"

weather_bp = Blueprint(
    "weather",
    __name__,
    template_folder=str(_TEMPLATES),
    static_folder=str(_STATIC),
    static_url_path="/static",
)


# Database config for weather
weather_db_cfg = DbConfig(
    host=Config.DB_HOST,
    port=Config.DB_PORT,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,  
    db_name=Config.DB_NAME_WEATHER
)

weather_engine = create_engine_for(weather_db_cfg)
WeatherSession = sessionmaker(bind=weather_engine)


# ROUTES 

@weather_bp.get("/")
def weather_page():
    """
    GET /weather
    Weather page — current conditions card, 7-hour hourly strip,
    40-hour temperature Chart.js graph, ML availability placeholder.
    All data is fetched client-side (in the page's JS), not here.
    See weather.html for full details.
    """
    return render_template("weather.html")


@weather_bp.get("/db/current")
def get_current_weather():
    """
    GET /api/weather/db/current
    Returns current weather data from the local database.
    Query parameter: limit (default 1, max 10)
    """
    try:
        limit = min(int(request.args.get('limit', 1)), 10)
        db_session = WeatherSession()
        result = db_session.execute(text("SELECT * FROM current ORDER BY dt DESC LIMIT :limit"), {"limit": limit})
        weather_data = [dict(row) for row in result]
        db_session.close()
        return jsonify(weather=weather_data)
    except Exception as e:
        return jsonify(error=str(e)), 500


@weather_bp.get("/db/hourly")
def get_hourly_weather():
    """
    GET /api/weather/db/hourly
    Returns hourly weather forecast. Tries local DB first; falls back to
    OpenWeather forecast API if DB is unavailable or returns no data.
    Query parameter: limit (default 40, max 100)
    """
    limit = min(int(request.args.get('limit', 40)), 100)

    # 1. Try DB first
    try:
        db_session = WeatherSession()
        result = db_session.execute(
            text("SELECT * FROM hourly ORDER BY dt ASC LIMIT :limit"),
            {"limit": limit}
        )
        hourly_data = [dict(row) for row in result]
        db_session.close()
        if hourly_data:
            return jsonify(hourly=hourly_data)
    except Exception:
        pass

    # 2. Fallback: OpenWeather forecast API
    try:
        cfg = Config()
        r = requests.get(
            cfg.FORECAST_WEATHER_URI,
            params={"appid": cfg.OPENWEATHER_API_KEY, "q": cfg.CITY, "units": "metric"},
            timeout=10,
        )
        r.raise_for_status()
        raw = r.json()

        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        hourly_data = []
        for item in raw.get("list", [])[:limit]:
            hourly_data.append({
                "dt":         now_str,
                "future_dt":  item.get("dt_txt"),
                "feels_like": item["main"].get("feels_like"),
                "humidity":   item["main"].get("humidity"),
                "pop":        item.get("pop"),
                "pressure":   item["main"].get("pressure"),
                "temp":       item["main"].get("temp"),
                "weather_id": item["weather"][0]["id"] if item.get("weather") else None,
                "wind_speed": item.get("wind", {}).get("speed"),
                "wind_gust":  item.get("wind", {}).get("gust"),
                "rain_3h":    item.get("rain", {}).get("3h"),
                "snow_3h":    item.get("snow", {}).get("3h"),
            })
        return jsonify(hourly=hourly_data)
    except Exception as e:
        return jsonify(error=str(e)), 500
