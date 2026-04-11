from flask import Blueprint, render_template, jsonify, request
import pathlib
from datetime import date, datetime
from zoneinfo import ZoneInfo
import requests
from sqlalchemy import text
from .services import (
    _fetch_nearest_weather,
    WeatherSession,
    hourly_forecast_rows_from_db,
    openweather_current,
    openweather_forecast_3h_list,
)


_BASE      = pathlib.Path(__file__).resolve().parent.parent.parent
_TEMPLATES = _BASE / "main_project" / "templates"
_STATIC    = _BASE / "main_project" / "static"

_DUBLIN = ZoneInfo("Europe/Dublin")


def _db_row_for_json(row: dict) -> dict:
    """
    MySQL DATETIME is naive. Our DB stores Dublin wall-clock times.
    Emit ISO-8601 with Europe/Dublin offset so browsers do not treat values as UTC/GMT.
    """
    out = {}
    for k, v in dict(row).items():
        if isinstance(v, datetime):
            aware = v.replace(tzinfo=_DUBLIN) if v.tzinfo is None else v
            out[k] = aware.isoformat()
        elif isinstance(v, date):
            out[k] = v.strftime("%Y-%m-%d")
        else:
            out[k] = v
    return out


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
        result = db_session.execute(
            text("SELECT * FROM current ORDER BY dt DESC LIMIT :limit"),
            {"limit": limit},
        )
        weather_data = [_db_row_for_json(row) for row in result.mappings().all()]
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


@weather_bp.get("/db/hourly")
def db_hourly_weather():
    """
    GET /api/weather/db/hourly
    Returns hourly weather forecast from the local database.
    Query parameter: limit (default 40, max 100)
    """
    try:
        limit = min(int(request.args.get("limit", 40)), 100)
        hourly_data = [
            _db_row_for_json(row) for row in hourly_forecast_rows_from_db(limit)
        ]
        return jsonify(hourly=hourly_data)
    except Exception as e:
        return jsonify(error=str(e)), 500


def _jsonify_openweather_http_error(exc: requests.HTTPError):
    try:
        return (
            jsonify(error="OpenWeather request failed", details=exc.response.json()),
            exc.response.status_code,
        )
    except Exception:
        return jsonify(error="OpenWeather request failed"), 502


@weather_bp.get("/openweather/current")
def api_current_weather():
    """
    GET /api/weather/openweather/current
    Free current conditions via OpenWeather /data/2.5/weather (API key required).
    Query params:
      - lat (default Dublin)
      - lon (default Dublin)
    """
    try:
        lat = float(request.args.get("lat", 53.3498))
        lon = float(request.args.get("lon", -6.2603))
        payload = openweather_current(lat, lon)
        return jsonify(source="openweather", weather=payload)
    except ValueError as e:
        return jsonify(error=str(e)), 500
    except requests.HTTPError as e:
        return _jsonify_openweather_http_error(e)
    except Exception:
        return jsonify(error="OpenWeather request failed"), 500


@weather_bp.get("/openweather/hourly")
@weather_bp.get("/openweather/forecast3h")
def api_forecast_weather():
    """
    GET /api/weather/openweather/hourly
    GET /api/weather/openweather/forecast3h
    Free /data/2.5/forecast (3-hour steps). Path /hourly is legacy naming.
    Query params:
      - lat (default Dublin)
      - lon (default Dublin)
      - limit (default 40, max 48)
    """
    try:
        lat = float(request.args.get("lat", 53.3498))
        lon = float(request.args.get("lon", -6.2603))
        limit = int(request.args.get("limit", 40))
        hourly = openweather_forecast_3h_list(lat, lon, limit)
        src = (
            "openweather"
            if request.path.rstrip("/").endswith("forecast3h")
            else "openweather_3h"
        )
        return jsonify(source=src, hourly=hourly)
    except ValueError as e:
        return jsonify(error=str(e)), 500
    except requests.HTTPError as e:
        return _jsonify_openweather_http_error(e)
    except Exception:
        return jsonify(error="OpenWeather request failed"), 500


