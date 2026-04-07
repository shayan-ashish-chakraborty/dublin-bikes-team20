from flask import Blueprint, jsonify, request, current_app
import json
import pathlib


_BASE = pathlib.Path(__file__).resolve().parent.parent.parent
_STATIC = _BASE / "main_project" / "static"
_TEMPLATES = _BASE / "main_project" / "templates"

_SPRINT1_WEATHER_DIR = _BASE / "sprint1_webscrappers" / "openweather_api" / "weather_data"

# ML model paths
_MODEL_PATH = pathlib.Path(__file__).resolve().parent.parent / "bike_forecast" / "bike_model.pkl"
_META_PATH = _MODEL_PATH.with_name("model_meta.json")

# Lazy-loaded singletons (loaded once on first request, reused afterward)
_model = None
_model_features = None  # ordered list of feature names from model_meta.json


def _load_model():
    """Load the pkl model and feature list once, then cache in module globals."""
    global _model, _model_features
    if _model is None:
        import pickle
        with open(_MODEL_PATH, "rb") as fh:
            _model = pickle.load(fh)
        with open(_META_PATH, encoding="utf-8") as fh:
            meta = json.load(fh)
        _model_features = meta["features"]   # e.g. ["station_id","capacity",...]
    return _model, _model_features


def _latest_sprint1_file(pattern: str):
    """Return the most-recently-modified file matching *pattern*, or None."""
    files = sorted(
        _SPRINT1_WEATHER_DIR.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


def _hourly_from_json(limit: int = 40) -> list:
    """
    Parse the newest sprint-1 forecast JSON and return a list of dicts shaped
    like the DB `hourly` table rows.
    """
    path = _latest_sprint1_file("forecast_*.json")
    if not path:
        return []
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    rows = []
    for item in raw.get("list", [])[:limit]:
        rows.append({
            "dt":         item.get("dt"),
            "future_dt":  item.get("dt_txt"),
            "temp":       item["main"]["temp"],
            "feels_like": item["main"]["feels_like"],
            "humidity":   item["main"]["humidity"],
            "wind_speed": item["wind"]["speed"],
            "rain_3h":    item.get("rain", {}).get("3h", 0),
        })
    return rows


# Blueprint 

forecast_bp = Blueprint(
    "bike_forecast",
    __name__,
    template_folder=str(_TEMPLATES),
    static_folder=str(_STATIC),
    static_url_path="/static",
)


# ROUTES 

@forecast_bp.get("/")
def ml_forecast():
    """
    GET /
    Run the trained RandomForest (bike_model.pkl) to predict bike availability.

    Query parameters

    stations - URL-encoded JSON array of station objects, each with:
               { station_id: int, capacity: int, name: str }
                Example: [{"station_id":10,"capacity":16,"name":"O'Connell St"}]
    hour - hour of day 0-23 (default: current hour in Dublin)
    avg_temp - temperature in °C  (default: 12.0)
    avg_humidity - relative humidity % (default: 80.0)
    avg_pressure -barometric pressure hPa (default: 1013.0)

    Response JSON
    
    {
      "predictions": [
        { "station_id": 10, "name": "...", "capacity": 16,
          "predicted_bikes": 7, "pct": 44 }
      ],
      "hour": 9,
      "model": "RandomForest",
      "mae": 1.4342,
      "r2": 0.9319
    }
    """
    import pandas as pd
    from datetime import datetime

    # Load model (cached after first call) 
    try:
        model, features = _load_model()
    except Exception as exc:
        return jsonify(error=f"Model could not be loaded: {exc}"), 500

    #  Parse weather query params 
    try:
        hour         = int(request.args.get("hour", datetime.now().hour))
        avg_temp     = float(request.args.get("avg_temp",     12.0))
        avg_humidity = float(request.args.get("avg_humidity", 80.0))
        avg_pressure = float(request.args.get("avg_pressure", 1013.0))
    except ValueError as exc:
        return jsonify(error=f"Invalid numeric parameter: {exc}"), 400

    # Parse station list 
    try:
        stations = json.loads(request.args.get("stations", "[]"))
        if not isinstance(stations, list):
            raise ValueError("stations must be a JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        return jsonify(error=f"Invalid stations JSON: {exc}"), 400

    if not stations:
        return jsonify(error="No stations provided"), 400

    # Run model for each station 
    predictions = []
    for st in stations:
        try:
            sid  = int(st["station_id"])
            cap  = int(st["capacity"])
            name = str(st.get("name", f"Station {sid}"))
        except (KeyError, ValueError) as exc:
            return jsonify(error=f"Bad station entry {st}: {exc}"), 400

        # Build one-row DataFrame in the exact feature order the model expects
        row = {
            "station_id"  : sid,
            "capacity"    : cap,
            "hour"        : hour,
            "avg_temp"    : avg_temp,
            "avg_humidity": avg_humidity,
            "avg_pressure": avg_pressure,
        }
        df   = pd.DataFrame([row])[features]          # reorder to match training
        pred = float(model.predict(df)[0])
        pred = max(0, min(cap, round(pred)))           # clamp to [0, capacity]
        pct  = round(pred / cap * 100) if cap > 0 else 0

        predictions.append({
            "station_id"      : sid,
            "name"            : name,
            "capacity"        : cap,
            "predicted_bikes" : pred,
            "pct"             : pct,
        })

    #  Return 
    try:
        with open(_META_PATH, encoding="utf-8") as fh:
            meta = json.load(fh)
    except Exception:
        meta = {}

    return jsonify(
        predictions=predictions,
        hour=hour,
        model=meta.get("best_model", "unknown"),
        mae=meta.get("mae"),
        r2=meta.get("r2"),
    )
