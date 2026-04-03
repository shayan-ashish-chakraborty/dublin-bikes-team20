from flask import Blueprint, jsonify
from main_project.station.services import get_all_stations, format_station

stations_bp = Blueprint("stations", __name__)


@stations_bp.route("")
def stations():
    raw = get_all_stations()
    return jsonify([format_station(s) for s in raw])
