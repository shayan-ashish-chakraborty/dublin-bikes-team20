
from flask import jsonify, request
import json
import pathlib
from datetime import datetime, timedelta


_FORECAST_DIR = pathlib.Path(__file__).resolve().parent
_BASE         = _FORECAST_DIR.parent.parent.parent   
_STATIC       = _BASE / "main_project" / "static"
_TEMPLATES    = _BASE / "main_project" / "templates"

# Bike models
_BIKE_MODEL_PATH  = _FORECAST_DIR / "bike_model.pkl"
_DOCK_MODEL_PATH  = _FORECAST_DIR / "docks_model.pkl"

# Weather models
_TEMP_MODEL_PATH  = _FORECAST_DIR / "weather_temp.pkl"
_HUM_MODEL_PATH   = _FORECAST_DIR / "weather_humidity.pkl"
_PRES_MODEL_PATH  = _FORECAST_DIR / "weather_pressure.pkl"
_RAIN_MODEL_PATH  = _FORECAST_DIR / "weather_rain.pkl"

_META_PATH        = _FORECAST_DIR / "model_meta.json"

# Lazy-loaded singletons (loaded once on first request, reused afterward)
_bike_model    = None
_dock_model    = None
_temp_model    = None
_hum_model     = None
_pres_model    = None
_rain_model    = None
_bike_features = None
_wx_features   = None
_hum_std_mean  = None   # dataset mean fallback for humidity_std feature


def _load_models():
    """Load all pkl models and meta once, then cache in module globals."""
    global _bike_model, _dock_model, _temp_model, _hum_model, _pres_model, _rain_model, _bike_features, _wx_features, _hum_std_mean
    if _bike_model is None:
        import pickle

        with open(_BIKE_MODEL_PATH,  "rb") as fh: _bike_model  = pickle.load(fh)
        with open(_DOCK_MODEL_PATH,  "rb") as fh: _dock_model  = pickle.load(fh)
        with open(_TEMP_MODEL_PATH,  "rb") as fh: _temp_model  = pickle.load(fh)
        with open(_HUM_MODEL_PATH,   "rb") as fh: _hum_model   = pickle.load(fh)
        with open(_PRES_MODEL_PATH,  "rb") as fh: _pres_model  = pickle.load(fh)
        with open(_RAIN_MODEL_PATH,  "rb") as fh: _rain_model  = pickle.load(fh)

        with open(_META_PATH, encoding="utf-8") as fh:
            meta = json.load(fh)

        _bike_features = meta["bike_features"]
        _wx_features   = meta["weather_features"]
        _hum_std_mean  = meta.get("humidity_std_mean", 3.49)

    return (_bike_model, _dock_model,
            _temp_model, _hum_model, _pres_model, _rain_model,
            _bike_features, _wx_features, _hum_std_mean)


def _predict_hour(models, station_id, capacity, future_dt,
                  wx_override=None):
    """
    Run the full two-stage pipeline for one hour.

    wx_override : dict with keys avg_temp, avg_humidity, avg_pressure,
                  is_raining — pass live OpenWeather values here to
                  skip the weather model for that hour.

    Returns dict with all predicted values for that hour.
    """
    import pandas as pd

    (bike_m, dock_m, temp_m, hum_m, pres_m, rain_m,
     bike_feat, wx_feat, hum_std) = models

    h = future_dt.hour
    m = future_dt.month

    #  weather 
    if wx_override:
        avg_temp     = round(float(wx_override["avg_temp"]),     1)
        avg_humidity = round(float(wx_override["avg_humidity"]), 1)
        avg_pressure = round(float(wx_override["avg_pressure"]), 1)
        is_raining   = int(wx_override["is_raining"])
    else:
        wx_row       = pd.DataFrame([{"hour": h, "month": m}])[wx_feat]
        avg_temp     = round(float(temp_m.predict(wx_row)[0]), 1)
        avg_humidity = round(float(hum_m.predict(wx_row)[0]),  1)
        avg_pressure = round(float(pres_m.predict(wx_row)[0]), 1)
        is_raining   = int(rain_m.predict(wx_row)[0])

    # bikes + docks
    bk_row = pd.DataFrame([{
        "station_id"  : station_id,
        "capacity"    : capacity,
        "hour"        : h,
        "avg_temp"    : avg_temp,
        "avg_humidity": avg_humidity,
        "avg_pressure": avg_pressure,
        "is_raining"  : is_raining,
        "humidity_std": hum_std,
    }])[bike_feat]

    bikes = round(max(0.0, min(float(capacity), float(bike_m.predict(bk_row)[0]))), 1)
    docks = round(max(0.0, min(float(capacity), float(dock_m.predict(bk_row)[0]))), 1)

    return {
        "time"            : future_dt.strftime("%Y-%m-%d %H:%M"),
        "predicted_bikes" : bikes,
        "predicted_docks" : docks,
        "predicted_temp"  : avg_temp,
        "predicted_humidity": avg_humidity,
        "predicted_pressure": avg_pressure,
        "predicted_rain"  : is_raining,
    }

#create a function to predict bike and dock for a batch of future dates
def _predict_bike_dock_batch(models, station_id, capacity, future_dts, wx_overrides):
    """
    Same bike/dock outputs as _predict_hour(..., wx_override=...), but one matrix
    predict per model (faster than N separate sklearn calls).
    future_dts and wx_overrides must have equal length; each wx dict matches
    _predict_hour wx_override keys.
    """
    import numpy as np
    import pandas as pd

    (bike_m, _, _, _, _, _, bike_feat, _, hum_std) = models
    n = len(future_dts)
    if n != len(wx_overrides):
        raise ValueError("future_dts and wx_overrides must have the same length")
    cap = float(capacity)
    rows = []
    for future_dt, wx in zip(future_dts, wx_overrides):
        avg_temp = round(float(wx["avg_temp"]), 1)
        avg_humidity = round(float(wx["avg_humidity"]), 1)
        avg_pressure = round(float(wx["avg_pressure"]), 1)
        is_raining = int(wx["is_raining"])
        rows.append({
            "station_id": station_id,
            "capacity": capacity,
            "hour": future_dt.hour,
            "avg_temp": avg_temp,
            "avg_humidity": avg_humidity,
            "avg_pressure": avg_pressure,
            "is_raining": is_raining,
            "humidity_std": hum_std,
        })
    bk_df = pd.DataFrame(rows)[bike_feat]
    bikes_raw = np.asarray(bike_m.predict(bk_df), dtype=float).ravel()
    predicted_bikes = [round(max(0.0, min(cap, float(b))), 1) for b in bikes_raw]
    # docks = capacity − bikes so the pair sums to capacity (dock model not used here)
    predicted_docks = [
        round(max(0.0, min(cap, cap - pb)), 1) for pb in predicted_bikes
    ]
    return predicted_bikes, predicted_docks


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


# Local test 
if __name__ == "__main__":
    import pathlib, sys

    # Point directly at the pkl files when running standalone
    _FORECAST_DIR_OVERRIDE = pathlib.Path(__file__).resolve().parent
    globals()["_FORECAST_DIR"] = _FORECAST_DIR_OVERRIDE

    # Reload path constants to pick up the override
    globals()["_BIKE_MODEL_PATH"] = _FORECAST_DIR_OVERRIDE / "bike_model.pkl"
    globals()["_DOCK_MODEL_PATH"] = _FORECAST_DIR_OVERRIDE / "docks_model.pkl"
    globals()["_TEMP_MODEL_PATH"] = _FORECAST_DIR_OVERRIDE / "weather_temp.pkl"
    globals()["_HUM_MODEL_PATH"]  = _FORECAST_DIR_OVERRIDE / "weather_humidity.pkl"
    globals()["_PRES_MODEL_PATH"] = _FORECAST_DIR_OVERRIDE / "weather_pressure.pkl"
    globals()["_RAIN_MODEL_PATH"] = _FORECAST_DIR_OVERRIDE / "weather_rain.pkl"
    globals()["_META_PATH"]       = _FORECAST_DIR_OVERRIDE / "model_meta.json"

    # Test params — change these 
    STATION_ID = 42
    CAPACITY   = 30
    HOURS      = 8

    # Optional: pass live weather to override the weather models
    # Set to None to use the built-in weather prediction
    LIVE_WEATHER = None
    # LIVE_WEATHER = {
    #     "avg_temp": 9.0, "avg_humidity": 82.0,
    #     "avg_pressure": 1010.0, "is_raining": 0
    # }

    models = _load_models()
    now    = datetime.now()

    result = [
        _predict_hour(models, STATION_ID, CAPACITY,
                      now + timedelta(hours=i), LIVE_WEATHER)
        for i in range(HOURS)
    ]

    output = {
        "number"             : STATION_ID,
        "times"              : [r["time"]                for r in result],
        "predicted_bikes"    : [r["predicted_bikes"]     for r in result],
        "predicted_docks"    : [r["predicted_docks"]     for r in result],
        "predicted_temp"     : [r["predicted_temp"]      for r in result],
        "predicted_humidity" : [r["predicted_humidity"]  for r in result],
        "predicted_pressure" : [r["predicted_pressure"]  for r in result],
        "predicted_rain"     : [r["predicted_rain"]      for r in result],
    }
    print(json.dumps(output, indent=2))

    