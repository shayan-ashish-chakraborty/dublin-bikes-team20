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
    """Render the weather dashboard page.

    All data (current conditions, hourly strip, temperature chart) is fetched
    client-side by the page's JavaScript. This route only serves the HTML shell.

    Returns:
        Rendered ``weather.html`` template.
    """
    return render_template("weather.html")


@weather_bp.get("/db/current")
def get_current_weather():
    """Return the most recent current weather record from the local database.

    Args:
        limit: Maximum number of records to return. Defaults to ``1``, max ``10``.

    Returns:
        JSON with key ``weather`` containing a list of current weather dicts.
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
    """Return the hourly forecast record closest to a requested datetime.

    Searches within a ±3-hour window. Tries the local DB first, then falls
    back to the OpenWeather forecast API.

    Args:
        dt: Target datetime string in ``"YYYY-MM-DD HH:MM:SS"`` format (query param, required).

    Returns:
        JSON weather row dict, or a 404 error if no match is found.
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
    """Return hourly weather forecast rows from the local database.

    Args:
        limit: Maximum number of rows to return. Defaults to ``40``, max ``100``.

    Returns:
        JSON with key ``hourly`` containing a list of forecast row dicts.
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
    """Fetch current weather conditions via the OpenWeatherMap API.

    Args:
        lat: Latitude of the target location. Defaults to Dublin (``53.3498``).
        lon: Longitude of the target location. Defaults to Dublin (``-6.2603``).

    Returns:
        JSON with keys ``source`` and ``weather`` (current conditions dict).
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
    """Fetch a 3-hour interval weather forecast from the OpenWeatherMap API.

    Available at both ``/openweather/hourly`` (legacy) and ``/openweather/forecast3h``.

    Args:
        lat: Latitude of the target location. Defaults to Dublin (``53.3498``).
        lon: Longitude of the target location. Defaults to Dublin (``-6.2603``).
        limit: Maximum number of timesteps to return. Defaults to ``40``, max ``48``.

    Returns:
        JSON with keys ``source`` and ``hourly`` (list of forecast row dicts).
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


