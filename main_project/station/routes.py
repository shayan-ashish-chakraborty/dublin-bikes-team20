from flask import Blueprint, jsonify, render_template

from main_project.station.services import get_all_stations, format_station

stations_bp = Blueprint("stations", __name__)


@stations_bp.route("/api/stations")
def stations():
    raw = get_all_stations()
    return jsonify([format_station(s) for s in raw])


@stations_bp.route("/stations")
def stations_page():
    """HTML map page; live data from GET /api/stations (stations.stations)."""
    return render_template("stations.html")
