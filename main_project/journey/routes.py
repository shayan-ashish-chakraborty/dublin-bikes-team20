from flask import Flask, render_template, jsonify, Blueprint
from flask_cors import CORS
from flask import Blueprint, jsonify, request
from ..station.services import get_all_stations, format_station
from ..config import Config
from .services import geocode_address
from .services import find_nearest_station, get_directions


# create a blueprint
_TEMPLATES = "../../../main_project/templates"
_STATIC    = "../../../main_project/static"

journey_bp  = Blueprint(
    "journey", 
    __name__,
    template_folder=str(_TEMPLATES),
    static_folder=str(_STATIC),
    static_url_path="/static",
)


@journey_bp.route("")
def index():
    return render_template("journey.html")

@journey_bp.route("/api/config")
def api_config():
    GOOGLE_MAPS_API_KEY = Config.GOOGLE_MAPS_API_KEY
    return jsonify({"googleMapsApiKey": GOOGLE_MAPS_API_KEY})



@journey_bp.route("/api/availability")
def availability():
    # date and time params are accepted for future ML/prediction use;
    # currently returns live data from the JCDecaux API
    raw = get_all_stations()
    stations = [format_station(s) for s in raw]
    return jsonify(stations)


@journey_bp.route("/api/route", methods=["POST"])
def route():
    body = request.get_json()
    start = body.get("start")
    end = body.get("end")

    if not start or not end:
        return jsonify({"error": "start and end are required"}), 400

    # Geocode addresses
    start_lat, start_lng = geocode_address(start)
    end_lat, end_lng = geocode_address(end)

    # Get all stations
    raw_stations = get_all_stations()
    all_stations = [format_station(s) for s in raw_stations]

    # Find nearest pickup station (needs bikes) and dropoff station (needs stands)
    pickup_candidates = find_nearest_station(start_lat, start_lng, all_stations, require_bikes=True)
    dropoff_candidates = find_nearest_station(end_lat, end_lng, all_stations, require_stands=True)

    if not pickup_candidates:
        return jsonify({"error": "No stations with available bikes found near start"}), 404
    if not dropoff_candidates:
        return jsonify({"error": "No stations with available stands found near end"}), 404

    pickup = pickup_candidates[0]
    dropoff = dropoff_candidates[0]

    # Get route legs
    walk_to_bike = get_directions(start_lat, start_lng, pickup["lat"], pickup["lng"], mode="walking")
    cycle_route = get_directions(pickup["lat"], pickup["lng"], dropoff["lat"], dropoff["lng"], mode="bicycling")
    walk_from_bike = get_directions(dropoff["lat"], dropoff["lng"], end_lat, end_lng, mode="walking")

    return jsonify({
        "start": {"lat": start_lat, "lng": start_lng, "address": start},
        "end": {"lat": end_lat, "lng": end_lng, "address": end},
        "pickup_station": pickup,
        "dropoff_station": dropoff,
        "legs": {
            "walk_to_bike": walk_to_bike,
            "cycle": cycle_route,
            "walk_from_bike": walk_from_bike,
        },
        "summary": {
            "total_distance": (
                walk_to_bike["distance_m"] + cycle_route["distance_m"] + walk_from_bike["distance_m"]
            ),
            "total_duration_s": (
                walk_to_bike["duration_s"] + cycle_route["duration_s"] + walk_from_bike["duration_s"]
            ),
        },
    })
