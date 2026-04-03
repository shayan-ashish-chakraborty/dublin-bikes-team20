from flask import Blueprint, render_template, jsonify, request
import pathlib
from ..db import create_engine_for, DbConfig
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


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
    host="localhost",
    port=3306,
    user="root",
    password="shayan1664",  # From var.env
    db_name="local_databaseopenweather"
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
    Returns hourly weather forecast from the local database.
    Query parameter: limit (default 40, max 100)
    """
    try:
        limit = min(int(request.args.get('limit', 40)), 100)
        db_session = WeatherSession()
        result = db_session.execute(text("SELECT * FROM hourly ORDER BY dt ASC LIMIT :limit"), {"limit": limit})
        hourly_data = [dict(row) for row in result]
        db_session.close()
        return jsonify(hourly=hourly_data)
    except Exception as e:
        return jsonify(error=str(e)), 500
