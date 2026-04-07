<<<<<<< HEAD
from flask import Blueprint, render_template, jsonify, request, current_app
import json
=======
from flask import Blueprint, render_template, jsonify, request
>>>>>>> 42adf999172d5a4639c5f4e8773ccd0de0dd36fc
import pathlib
from ..db import create_engine_for, DbConfig
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


<<<<<<< HEAD

=======
>>>>>>> 42adf999172d5a4639c5f4e8773ccd0de0dd36fc
_BASE      = pathlib.Path(__file__).resolve().parent.parent.parent
_TEMPLATES = _BASE / "main_project" / "templates"
_STATIC    = _BASE / "main_project" / "static"

<<<<<<< HEAD
_SPRINT1_WEATHER_DIR = _BASE / "sprint1_webscrappers" / "openweather_api" / "weather_data"

=======
>>>>>>> 42adf999172d5a4639c5f4e8773ccd0de0dd36fc

weather_bp = Blueprint(
    "weather",
    __name__,
    template_folder=str(_TEMPLATES),
    static_folder=str(_STATIC),
    static_url_path="/static",
)


# Database config for weather
<<<<<<< HEAD
def _get_weather_session():
    """Create a new session using the app config (reads .env values)."""
    cfg = DbConfig(
        host=current_app.config["DB_HOST"],
        port=str(current_app.config["DB_PORT"]),
        user=current_app.config["DB_USER"],
        password=current_app.config["DB_PASSWORD"],
        db_name=current_app.config["DB_NAME_WEATHER"],
    )
    engine = create_engine_for(cfg)
    Session = sessionmaker(bind=engine)
    return Session()

def _latest_sprint1_file(pattern: str):
    """Return the most-recently-modified file matching *pattern*, or None."""
    files = sorted(
        _SPRINT1_WEATHER_DIR.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


def _current_from_json() -> list:
    """
    Parse the newest sprint-1 current-weather JSON and return a list with one
    dict shaped like the DB `current` table rows.
    """
    path = _latest_sprint1_file("weather_*.json")
    if not path:
        return []
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return [{
        "dt":         raw.get("dt"),
        "temp":       raw["main"]["temp"],
        "feels_like": raw["main"]["feels_like"],
        "humidity":   raw["main"]["humidity"],
        "wind_speed": raw["wind"]["speed"],
        "rain_1h":    raw.get("rain", {}).get("1h", 0),
    }]


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

=======
weather_db_cfg = DbConfig(
    host="localhost",
    port=3306,
    user="root",
    password="shayan1664",  # From var.env
    db_name="local_databaseopenweather"
)

weather_engine = create_engine_for(weather_db_cfg)
WeatherSession = sessionmaker(bind=weather_engine)


>>>>>>> 42adf999172d5a4639c5f4e8773ccd0de0dd36fc
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
<<<<<<< HEAD
    limit = min(int(request.args.get("limit", 1)), 10)
    try:
        session = _get_weather_session()
        result  = session.execute(
            text("SELECT * FROM current ORDER BY dt DESC LIMIT :limit"),
            {"limit": limit},
        )
        rows = [dict(r._mapping) for r in result]
        session.close()
        if rows:
            return jsonify(weather=rows, source="db")
    except Exception as e:
        print(f"DB query failed: {e}")
        pass  # DB unavailable — fall through to JSON fallback

    # 2. Fallback: sprint-1 JSON
    try:
        rows = _current_from_json()[:limit]
        if rows:
            return jsonify(weather=rows, source="json_fallback")
    except Exception as err:
        return jsonify(error="DB and JSON fallback both failed", detail=str(err)), 500

    return jsonify(error="No weather data available"), 503
=======
    try:
        limit = min(int(request.args.get('limit', 1)), 10)
        db_session = WeatherSession()
        result = db_session.execute(text("SELECT * FROM current ORDER BY dt DESC LIMIT :limit"), {"limit": limit})
        weather_data = [dict(row) for row in result]
        db_session.close()
        return jsonify(weather=weather_data)
    except Exception as e:
        return jsonify(error=str(e)), 500
>>>>>>> 42adf999172d5a4639c5f4e8773ccd0de0dd36fc


@weather_bp.get("/db/hourly")
def get_hourly_weather():
    """
    GET /api/weather/db/hourly
    Returns hourly weather forecast from the local database.
    Query parameter: limit (default 40, max 100)
    """
<<<<<<< HEAD
    limit = min(int(request.args.get("limit", 40)), 100)
    try:
        session = _get_weather_session()
        result  = session.execute(
            text("SELECT * FROM hourly ORDER BY dt ASC LIMIT :limit"),
            {"limit": limit},
        )
        rows = [dict(r._mapping) for r in result]
        session.close()
        if rows:
            return jsonify(hourly=rows, source="db")
    except Exception as e:
        print(f"DB query failed: {e}")
        pass  # DB unavailable — fall through to JSON fallback

    # 2. Fallback: sprint-1 JSON
    try:
        rows = _hourly_from_json(limit)
        if rows:
            return jsonify(hourly=rows, source="json_fallback")
    except Exception as err:
        return jsonify(error="DB and JSON fallback both failed", detail=str(err)), 500

    return jsonify(error="No hourly data available"), 503
=======
    try:
        limit = min(int(request.args.get('limit', 40)), 100)
        db_session = WeatherSession()
        result = db_session.execute(text("SELECT * FROM hourly ORDER BY dt ASC LIMIT :limit"), {"limit": limit})
        hourly_data = [dict(row) for row in result]
        db_session.close()
        return jsonify(hourly=hourly_data)
    except Exception as e:
        return jsonify(error=str(e)), 500
>>>>>>> 42adf999172d5a4639c5f4e8773ccd0de0dd36fc
