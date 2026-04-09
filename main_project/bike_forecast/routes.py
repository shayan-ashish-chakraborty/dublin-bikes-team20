
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
    """
    GET /forecast/station
    Runs the two-stage pipeline (weather model → bike model) and returns
    hourly predictions for bikes, docks, and all weather parameters.

    Query parameters

    number = station_id                        (required)
    capacity = total docks at the station        (required)
    hours = future hours to forecast (default 8, max 48)
    avg_temp = override weather model °C         (optional)
    avg_humidity = override weather model %          (optional)
    avg_pressure = override weather model hPa        (optional)
    is_raining = override rain flag 0/1            (optional)

    Response JSON
    
    {
      "number": 42,
      "times":               ["2026-04-08 12:47", ...],
      "predicted_bikes":     [9.8, 8.5, ...],
      "predicted_docks":     [20.4, 21.4, ...],
      "predicted_temp":      [9.0, 9.0, ...],
      "predicted_humidity":  [81.3, 80.0, ...],
      "predicted_pressure":  [1014.9, 1014.6, ...],
      "predicted_rain":      [0, 0, ...]
    }
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
    """
    GET /forecast/station/hourly
    Predict bikes and docks for a single specific hour.
    Weather params are optional — if omitted, the weather model predicts them.

    Query parameters
    number       = station_id                  (required)
    capacity     = total docks at the station  (required)
    time         = datetime string             (required, e.g. "2026-04-09 12:31:11")
    avg_temp     = temperature °C              (optional)
    avg_humidity = humidity %                  (optional)
    avg_pressure = pressure hPa               (optional)
    is_raining   = rain flag 0 or 1           (optional)

    Response JSON
    {
      "time":             "2026-04-09 14:00",
      "predicted_bikes":  9.8,
      "predicted_docks":  20.4
    }
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
