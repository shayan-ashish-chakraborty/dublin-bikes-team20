from flask import Blueprint, render_template, jsonify, request
import pathlib
from datetime import datetime, timedelta
from ..db import create_engine_for, DbConfig
from ..config import Config
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from .services import _fetch_nearest_weather, WeatherSession
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


# WeatherSession is imported from .services


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


@weather_bp.get("/db/hourly/nearest")
def get_nearest_hourly_weather():
    """
    GET /api/weather/db/hourly/nearest?dt=YYYY-MM-DD HH:MM:SS
    Returns the single hourly forecast record whose future_dt is closest to
    the requested datetime, within a ±3-hour window.
    Tries the local DB first; falls back to the OpenWeather forecast API.
    """
    dt_str = request.args.get("dt")
    if not dt_str:
        return jsonify(error="Missing required query param: dt"), 400

    record = _fetch_nearest_weather(dt_str)

    if record is None:
        return jsonify(error=f"No forecast data found within 3 hours of {dt_str}"), 404

    return jsonify(record)
