from __future__ import annotations

import os

import requests
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text

from ..db import DbConfig, create_engine_for

weather_bp = Blueprint("weather", __name__)


def _get_city() -> str:
    # allow overriding per-request: /api/weather/current?city=...
    return request.args.get("city") or current_app.config.get("CITY")  # type: ignore[return-value]


@weather_bp.get("/")
def weather_index():
    return {
        "endpoints": {
            "current_external": "/api/weather/current",
            "forecast_external": "/api/weather/forecast",
            "current_db": "/api/weather/db/current",
            "hourly_db": "/api/weather/db/hourly",
        }
    }


@weather_bp.get("/current")
def current_weather_external():
    api_key = current_app.config.get("OPENWEATHER_API_KEY")
    if not api_key:
        return {"error": "OPENWEATHER_API_KEY is not set"}, 500

    r = requests.get(
        current_app.config["CURRENT_WEATHER_URI"],
        params={"appid": api_key, "q": _get_city(), "units": "metric"},
        timeout=15,
    )
    return jsonify(r.json()), r.status_code


@weather_bp.get("/forecast")
def forecast_weather_external():
    api_key = current_app.config.get("OPENWEATHER_API_KEY")
    if not api_key:
        return {"error": "OPENWEATHER_API_KEY is not set"}, 500

    r = requests.get(
        current_app.config["FORECAST_WEATHER_URI"],
        params={"appid": api_key, "q": _get_city(), "units": "metric"},
        timeout=15,
    )
    return jsonify(r.json()), r.status_code


def _weather_engine():
    cfg = DbConfig(
        host=current_app.config["DB_HOST"],
        port=str(current_app.config["DB_PORT"]),
        user=current_app.config["DB_USER"],
        password=current_app.config["DB_PASSWORD"],
        db_name=current_app.config["DB_NAME_WEATHER"],
    )
    echo = os.getenv("SQL_ECHO", "false").lower() == "true"
    return create_engine_for(cfg, echo=echo)


@weather_bp.get("/db/current")
def current_weather_db():
    engine = _weather_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM current ORDER BY dt DESC LIMIT :limit"), {"limit": int(request.args.get("limit", 200))})
        data = [dict(row._mapping) for row in rows]
    return jsonify({"weather": data})


@weather_bp.get("/db/hourly")
def hourly_weather_db():
    engine = _weather_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM hourly ORDER BY dt DESC, future_dt DESC LIMIT :limit"), {"limit": int(request.args.get("limit", 200))})
        data = [dict(row._mapping) for row in rows]
    return jsonify({"hourly": data})

