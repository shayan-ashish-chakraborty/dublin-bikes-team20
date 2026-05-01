
from flask import Blueprint, jsonify, request, current_app
import pathlib
from .models.forecast import _load_models, _predict_hour
from datetime import datetime, timedelta


_BASE = pathlib.Path(__file__).resolve().parent.parent.parent
_STATIC = _BASE / "main_project" / "static"
_TEMPLATES = _BASE / "main_project" / "templates"
_FORECAST_DIR = _BASE / "main_project" / "bike_forecast" / "models"


# Blueprint 

forecast_bp = Blueprint(
    "bike_forecast",
    __name__,
    template_folder=str(_TEMPLATES),
    static_folder=str(_STATIC),
    static_url_path="/static",
)


# ROUTES 

@forecast_bp.get("/station")
def station_forecast():
    """Return multi-hour bike and dock predictions for a station.

    Runs the two-stage ML pipeline (weather model → bike model) for each
    requested future hour.

    Args (query parameters):
        number: Station ID (required).
        capacity: Total docks at the station (required).
        hours: Future hours to forecast, max 48. Defaults to 8.
        avg_temp: Override weather model temperature in °C (optional).
        avg_humidity: Override weather model humidity in % (optional).
        avg_pressure: Override weather model pressure in hPa (optional).
        is_raining: Override rain flag, ``0`` or ``1`` (optional).

    Returns:
        JSON with keys ``number``, ``times``, ``predicted_bikes``,
        ``predicted_docks``, ``predicted_temp``, ``predicted_humidity``,
        ``predicted_pressure``, ``predicted_rain``.
    """
    try:
        models = _load_models()
    except Exception as exc:
        return jsonify(error=f"Models could not be loaded: {exc}"), 500

    # Parse params 
    try:
        station_id = int(request.args.get("number",   -1))
        capacity   = int(request.args.get("capacity", -1))
        hours      = min(int(request.args.get("hours", 8)), 48)
    except ValueError as exc:
        return jsonify(error=f"Invalid parameter: {exc}"), 400

    if station_id < 0:
        return jsonify(error="'number' (station_id) is required"), 400
    if capacity < 0:
        return jsonify(error="'capacity' is required"), 400

    # Optional live weather override 
    wx_keys = ("avg_temp", "avg_humidity", "avg_pressure", "is_raining")
    if all(k in request.args for k in wx_keys):
        try:
            wx_override = {
                "avg_temp"    : float(request.args["avg_temp"]),
                "avg_humidity": float(request.args["avg_humidity"]),
                "avg_pressure": float(request.args["avg_pressure"]),
                "is_raining"  : int(request.args["is_raining"]),
            }
        except ValueError as exc:
            return jsonify(error=f"Invalid weather override param: {exc}"), 400
    else:
        wx_override = None   # use weather models

    # Run pipeline for each future hour 
    now    = datetime.now()
    result = [
        _predict_hour(models, station_id, capacity,
                      now + timedelta(hours=offset), wx_override)
        for offset in range(hours)
    ]

    return jsonify(
        number             = station_id,
        times              = [r["time"]                for r in result],
        predicted_bikes    = [r["predicted_bikes"]     for r in result],
        predicted_docks    = [r["predicted_docks"]     for r in result],
        predicted_temp     = [r["predicted_temp"]      for r in result],
        predicted_humidity = [r["predicted_humidity"]  for r in result],
        predicted_pressure = [r["predicted_pressure"]  for r in result],
        predicted_rain     = [r["predicted_rain"]      for r in result],
    )

# for hourly prediction purpose
@forecast_bp.get("/station/hourly")
def hourly_station_forecast():
    """Predict bike and dock availability for a single future hour.

    Weather parameters are optional — if omitted, the weather model predicts them.

    Args (query parameters):
        number: Station ID (required).
        capacity: Total docks at the station (required).
        time: Target datetime string, e.g. ``"2026-04-09 12:31:11"`` (required).
        avg_temp: Temperature in °C (optional).
        avg_humidity: Humidity in % (optional).
        avg_pressure: Pressure in hPa (optional).
        is_raining: Rain flag, ``0`` or ``1`` (optional).

    Returns:
        JSON with keys ``time``, ``predicted_bikes``, ``predicted_docks``.
    """
    try:
        models = _load_models()
    except Exception as exc:
        return jsonify(error=f"Models could not be loaded: {exc}"), 500

    try:
        station_id = int(request.args.get("number",   -1))
        capacity   = int(request.args.get("capacity", -1))
    except ValueError as exc:
        return jsonify(error=f"Invalid parameter: {exc}"), 400

    if station_id < 0:
        return jsonify(error="'number' (station_id) is required"), 400
    if capacity < 0:
        return jsonify(error="'capacity' is required"), 400

    time_str = request.args.get("time")
    if not time_str:
        return jsonify(error="'time' is required"), 400

    try:
        target_dt = datetime.fromisoformat(time_str)
    except ValueError:
        return jsonify(error="Invalid 'time' format, expected e.g. '2026-04-09 12:31:11'"), 400

    # Optional weather override — only applied if all four params are present
    wx_keys = ("avg_temp", "avg_humidity", "avg_pressure", "is_raining")
    if all(k in request.args for k in wx_keys):
        try:
            wx_override = {
                "avg_temp"    : float(request.args["avg_temp"]),
                "avg_humidity": float(request.args["avg_humidity"]),
                "avg_pressure": float(request.args["avg_pressure"]),
                "is_raining"  : int(request.args["is_raining"]),
            }
        except ValueError as exc:
            return jsonify(error=f"Invalid weather parameter: {exc}"), 400
    else:
        wx_override = None  # let the weather model predict

    result = _predict_hour(models, station_id, capacity, target_dt, wx_override)

    return jsonify(
        time             = result["time"],
        predicted_bikes  = result["predicted_bikes"],
        predicted_docks  = result["predicted_docks"],
    )
