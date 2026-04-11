from flask import Blueprint, jsonify, render_template, request

from main_project.station.services import (
    get_all_stations,
    format_station,
    station_predict_from_request,
)

stations_bp = Blueprint("stations", __name__)


@stations_bp.route("/api/stations")
def stations():
    raw = get_all_stations()
    return jsonify([format_station(s) for s in raw])


@stations_bp.route("/api/stations/predict")
def stations_predict():
    """
    GET /api/stations/predict?number=<id>&hours=48

    Query parsing + ML in station_predict_from_request (weather list, then _predict_hour per hour).
    """
    try:
        return jsonify(station_predict_from_request(request))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error=f"prediction failed: {exc}"), 503


@stations_bp.route("/stations")
def stations_page():
    """HTML map page; live data from GET /api/stations (stations.stations)."""
    return render_template("stations.html")
