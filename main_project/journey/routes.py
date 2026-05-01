from flask import Flask, render_template, jsonify, Blueprint
from flask_cors import CORS
from flask import Blueprint, jsonify, request
from datetime import datetime
from ..station.services import get_all_stations, format_station, get_station
from ..config import Config
from .services import geocode_address, find_nearest_station, get_directions, predict_stations_availability
from ..bike_forecast.models.forecast import _load_models

try:
    _models = _load_models()
except Exception:
    _models = None


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
    return render_template("Journey.html")

@journey_bp.route("/api/config")
def api_config():
    GOOGLE_MAPS_API_KEY = Config.GOOGLE_MAPS_API_KEY
    return jsonify({"googleMapsApiKey": GOOGLE_MAPS_API_KEY})



@journey_bp.route("/api/availability")
def availability():
    """``GET /journey/api/availability`` — Return live availability for all Dublin Bikes stations.

    Fetches raw station data from the JCDecaux API and normalises each entry.
    Date/time query parameters are accepted but currently unused — this route
    always returns live data. ML-based availability is handled by
    :func:`predict_availability` instead.

    Uses:
        - :func:`~main_project.station.services.get_all_stations` — fetches all stations from JCDecaux.
        - :func:`~main_project.station.services.format_station` — normalises each raw station dict.

    Returns:
        JSON list of formatted station dicts with live ``available_bikes``
        and ``available_stands``.
    """
    # date and time params are accepted for future ML/prediction use;
    # currently returns live data from the JCDecaux API
    raw = get_all_stations()
    stations = [format_station(s) for s in raw]
    return jsonify(stations)


@journey_bp.route("/api/route", methods=["POST"])
def route():
    """``POST /journey/api/route`` — Plan a live cycling route between two addresses using current station availability.

    Logic:

    1. Geocode ``start`` and ``end`` addresses to coordinates.
    2. Fetch all live stations from JCDecaux.
    3. Find the nearest pickup station with available bikes.
    4. Find the nearest dropoff station with available docks.
    5. Fetch three route legs from Google Directions API.

    Uses:
        - :func:`~main_project.journey.services.geocode_address` — converts addresses to coordinates.
        - :func:`~main_project.station.services.get_all_stations` — fetches live station data.
        - :func:`~main_project.station.services.format_station` — normalises station dicts.
        - :func:`~main_project.journey.services.find_nearest_station` — finds closest stations with availability filters.
        - :func:`~main_project.journey.services.get_directions` — fetches walking and cycling legs.

    Args:
        start: Origin address string (JSON body, required).
        end: Destination address string (JSON body, required).

    Returns:
        JSON with ``start``, ``end``, ``pickup_station``, ``dropoff_station``,
        ``legs`` (walk_to_bike, cycle, walk_from_bike), and ``summary``
        (total distance and duration).
    """
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


@journey_bp.route("/api/predict/availability")
def predict_availability():
    """``GET /journey/api/predict/availability`` — Predict bike and dock availability at a single station for a future datetime.

    Logic:

    1. Validate ``stand_no`` and ``time`` query parameters.
    2. Fetch live station data to obtain capacity (``total_stands``).
    3. Run the ML pipeline for the single station at the requested time.

    Uses:
        - :func:`~main_project.station.services.get_station` — fetches live station data from JCDecaux.
        - :func:`~main_project.station.services.format_station` — normalises the station dict.
        - :func:`~main_project.journey.services.predict_stations_availability` — runs the two-stage ML pipeline (weather + bike model).

    Args:
        stand_no: JCDecaux station number (query param, required).
        time: Target datetime as ``"YYYY-MM-DD HH:MM:SS"`` (query param, required).

    Returns:
        JSON with keys ``stand_no``, ``time``, ``predicted_bikes``,
        ``predicted_docks``, and ``weather_warning`` (``null`` on success,
        or a message string if weather data was unavailable).
    """
    if _models is None:
        return jsonify(error="Prediction models could not be loaded"), 500

    stand_no_str = request.args.get("stand_no")
    time_str     = request.args.get("time")

    if not stand_no_str or not time_str:
        return jsonify(error="stand_no and time are required"), 400

    try:
        stand_no = int(stand_no_str)
    except ValueError:
        return jsonify(error="stand_no must be an integer"), 400

    try:
        datetime.fromisoformat(time_str)
    except ValueError:
        return jsonify(error="Invalid time format, expected e.g. '2026-04-09 12:31:11'"), 400

    # Get station capacity from JCDecaux
    try:
        station   = get_station(stand_no)
        formatted = format_station(station)
    except Exception as e:
        return jsonify(error=f"Could not fetch station data: {e}"), 503

    results, weather_warning = predict_stations_availability([formatted], time_str, _models)
    r = results[0]

    return jsonify(
        stand_no        = stand_no,
        time            = time_str,
        predicted_bikes = r["available_bikes"],
        predicted_docks = r["available_stands"],
        weather_warning = weather_warning,
    )


@journey_bp.route("/api/route/predict", methods=["POST"])
def route_predict():
    """``POST /journey/api/route/predict`` — Plan a cycling route using predicted station availability at a future time.

    Logic:

    1. Geocode ``start`` and ``end`` addresses to coordinates.
    2. Fetch all live stations for coordinates and capacity data.
    3. Find the 5 nearest candidate stations for pickup and dropoff.
    4. Deduplicate candidates and run the ML pipeline **once** for all of them
       (weather is fetched only once and reused across all stations).
    5. Filter to stations with predicted bikes/docks available.
    6. Fetch three route legs from Google Directions API.

    Uses:
        - :func:`~main_project.journey.services.geocode_address` — converts addresses to coordinates.
        - :func:`~main_project.station.services.get_all_stations` — fetches live station data.
        - :func:`~main_project.station.services.format_station` — normalises station dicts.
        - :func:`~main_project.journey.services.find_nearest_station` — finds nearest candidate stations.
        - :func:`~main_project.journey.services.predict_stations_availability` — runs batch ML prediction (weather fetched once).
        - :func:`~main_project.journey.services.get_directions` — fetches walking and cycling route legs.

    Args:
        start: Origin address string (JSON body, required).
        end: Destination address string (JSON body, required).
        time: Target datetime as ``"YYYY-MM-DD HH:MM:SS"``, or ``"now"`` (JSON body, required).

    Returns:
        JSON with the same shape as ``/api/route``, plus ``prediction_mode: true``
        and ``weather_warning`` (``null`` on success, or a message string).
        ``available_bikes`` and ``available_stands`` reflect predicted values.
    """
    if _models is None:
        return jsonify({"error": "Prediction models could not be loaded"}), 500

    body     = request.get_json()
    start    = body.get("start")
    end      = body.get("end")
    time_str = body.get("time")

    if not start or not end or not time_str:
        return jsonify({"error": "start, end and time are required"}), 400

    if time_str != "now":
        try:
            datetime.fromisoformat(time_str)
        except ValueError:
            return jsonify({"error": "Invalid time format, expected e.g. '2026-04-09 15:00:00'"}), 400

    # Geocode addresses
    start_lat, start_lng = geocode_address(start)
    end_lat, end_lng     = geocode_address(end)

    # Live station data for lat/lng + capacity
    raw_stations = get_all_stations()
    all_stations = [format_station(s) for s in raw_stations]

    # Top 5 nearest candidates by distance only (no live availability filter)
    CANDIDATE_LIMIT = 5
    pickup_near  = find_nearest_station(start_lat, start_lng, all_stations, limit=CANDIDATE_LIMIT)
    dropoff_near = find_nearest_station(end_lat,   end_lng,   all_stations, limit=CANDIDATE_LIMIT)

    # Deduplicate by station number, predict in one call (weather fetched once)
    seen     = set()
    combined = []
    for s in pickup_near + dropoff_near:
        if s["number"] not in seen:
            seen.add(s["number"])
            combined.append(s)

    predicted, weather_warning = predict_stations_availability(combined, time_str, _models)

    # Build lookup by station number
    lookup = {s["number"]: s for s in predicted}

    # Restore ordered candidate lists with predicted availability
    pickup_candidates  = [lookup[s["number"]] for s in pickup_near  if lookup[s["number"]]["available_bikes"]  > 0]
    dropoff_candidates = [lookup[s["number"]] for s in dropoff_near if lookup[s["number"]]["available_stands"] > 0]

    if not pickup_candidates:
        return jsonify({"error": "No stations with predicted available bikes found near start"}), 404
    if not dropoff_candidates:
        return jsonify({"error": "No stations with predicted available stands found near end"}), 404

    pickup  = pickup_candidates[0]
    dropoff = dropoff_candidates[0]

    # Get route legs
    walk_to_bike   = get_directions(start_lat, start_lng, pickup["lat"],  pickup["lng"],  mode="walking")
    cycle_route    = get_directions(pickup["lat"],  pickup["lng"],  dropoff["lat"], dropoff["lng"], mode="bicycling")
    walk_from_bike = get_directions(dropoff["lat"], dropoff["lng"], end_lat,        end_lng,        mode="walking")

    return jsonify({
        "start"           : {"lat": start_lat, "lng": start_lng, "address": start},
        "end"             : {"lat": end_lat,   "lng": end_lng,   "address": end},
        "pickup_station"  : pickup,
        "dropoff_station" : dropoff,
        "prediction_mode" : True,
        "weather_warning" : weather_warning,
        "legs": {
            "walk_to_bike"  : walk_to_bike,
            "cycle"         : cycle_route,
            "walk_from_bike": walk_from_bike,
        },
        "summary": {
            "total_distance"  : walk_to_bike["distance_m"]  + cycle_route["distance_m"]  + walk_from_bike["distance_m"],
            "total_duration_s": walk_to_bike["duration_s"]  + cycle_route["duration_s"]  + walk_from_bike["duration_s"],
        },
    })
