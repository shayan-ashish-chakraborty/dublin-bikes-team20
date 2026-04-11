from __future__ import annotations

import os

import requests
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text

from ..db import DbConfig, create_engine_for

bikes_bp = Blueprint("bikes", __name__)


@bikes_bp.get("/")
def bikes_index():
    return {
        "endpoints": {
            "stations_external": "/api/bikes/stations",
            "stations_db": "/api/bikes/db/stations",
            "availability_db": "/api/bikes/db/availability",
        }
    }


@bikes_bp.get("/stations")
def stations_external():
    api_key = current_app.config.get("JCDECAUX_API_KEY")
    if not api_key:
        return {"error": "JCDECAUX_API_KEY is not set"}, 500

    city = request.args.get("city") or current_app.config.get("CITY")

    r = requests.get(
        current_app.config["STATIONS_URI"],
        params={"apiKey": api_key, "contract": city},
        timeout=15,
    )
    return jsonify(r.json()), r.status_code


def _bikes_engine():
    cfg = DbConfig(
        host=current_app.config["DB_HOST"],
        port=str(current_app.config["DB_PORT"]),
        user=current_app.config["DB_USER"],
        password=current_app.config["DB_PASSWORD"],
        db_name=current_app.config["DB_NAME_JCDECAUX"],
    )
    echo = os.getenv("SQL_ECHO", "false").lower() == "true"
    return create_engine_for(cfg, echo=echo)


@bikes_bp.get("/db/stations")
def stations_db():
    engine = _bikes_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM station"))
        data = [dict(row._mapping) for row in rows]
    return jsonify({"stations": data})


@bikes_bp.get("/db/availability")
def availability_db():
    engine = _bikes_engine()
    limit = int(request.args.get("limit", 100))
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT * FROM availability
                ORDER BY last_update DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        data = [dict(row._mapping) for row in rows]
    return jsonify({"availability": data})