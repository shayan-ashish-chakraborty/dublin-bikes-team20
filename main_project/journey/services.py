import requests, math
from datetime import datetime
from ..config import Config
from ..weather.services import _fetch_nearest_weather
from ..bike_forecast.models.forecast import _predict_hour

GOOGLE_MAPS_API_KEY = Config.GOOGLE_MAPS_API_KEY


def geocode_address(address) -> tuple:
    """Convert a free-text address to latitude/longitude using the Google Geocoding API.

    The query is scoped to Dublin, Ireland.

    Args:
        address: A free-text address string (e.g. ``"O'Connell Street"``).

    Returns:
        A ``(lat, lng)`` tuple of floats.

    Raises:
        requests.HTTPError: If the API returns a non-2xx status code.
        ValueError: If the geocoding result status is not ``"OK"`` or no
            results are returned.
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": f"{address}, Dublin, Ireland",
        "key": GOOGLE_MAPS_API_KEY,
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if data["status"] != "OK" or not data["results"]:
        raise ValueError(f"Could not geocode address: {address}")

    location = data["results"][0]["geometry"]["location"]
    return location["lat"], location["lng"]


def haversine(lat1, lng1, lat2, lng2) -> float:
    """Calculate the great-circle distance in metres between two coordinates.

    Args:
        lat1: Latitude of the first point in decimal degrees.
        lng1: Longitude of the first point in decimal degrees.
        lat2: Latitude of the second point in decimal degrees.
        lng2: Longitude of the second point in decimal degrees.

    Returns:
        Distance in metres as a float.
    """
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearest_station(lat, lng, stations, require_bikes=False, require_stands=False, limit=3) -> list:
    """Find the nearest bike stations to a point, with optional availability filters.

    Uses:
        - :func:`~main_project.journey.services.haversine` — computes the great-circle distance
          between the reference point and each candidate station.

    Args:
        lat: Latitude of the reference point.
        lng: Longitude of the reference point.
        stations: List of formatted station dicts (must include ``lat``, ``lng``,
            ``available_bikes``, and ``available_stands``).
        require_bikes: If ``True``, exclude stations with no available bikes.
            Defaults to ``False``.
        require_stands: If ``True``, exclude stations with no available docks.
            Defaults to ``False``.
        limit: Maximum number of stations to return. Defaults to ``3``.

    Returns:
        A list of up to ``limit`` station dicts sorted by distance ascending,
        each augmented with a ``distance_m`` key (int, metres).
    """
    candidates = []
    for s in stations:
        if require_bikes and s["available_bikes"] == 0:
            continue
        if require_stands and s["available_stands"] == 0:
            continue
        dist = haversine(lat, lng, s["lat"], s["lng"])
        candidates.append({**s, "distance_m": round(dist)})
    candidates.sort(key=lambda x: x["distance_m"])
    return candidates[:limit]

def predict_stations_availability(
    stations: list[dict],
    time_str: str,
    models,
) -> tuple[list[dict], str | None]:
    """Predict bike and dock availability for a list of stations at a given time.

    Logic:

    1. Parse ``time_str`` into a target ``datetime``.
    2. Fetch the nearest hourly weather record **once** for the target time
       using :func:`~main_project.weather.services._fetch_nearest_weather`.
       If weather is available, build a ``wx_override`` dict with
       ``avg_temp``, ``avg_humidity``, ``avg_pressure``, and ``is_raining``
       (derived from ``rain_3h > 0.01`` or ``pop >= 0.5``).
    3. For each station, run the two-stage ML pipeline via
       :func:`~main_project.bike_forecast.models.forecast._predict_hour`,
       passing the shared ``wx_override`` so weather is not re-fetched
       per station.
    4. Clamp predictions to ``[0, capacity]`` and compute
       ``available_stands = capacity − predicted_bikes``.

    If weather data is unavailable (DB empty and API failed), ``wx_override``
    is ``None`` and the internal weather model predicts conditions from
    hour/month alone — a ``weather_warning`` string is returned to inform
    the caller.

    Args:
        stations: List of formatted station dicts; each must have ``number``
            and ``total_stands``.
        time_str: Target datetime as ``"YYYY-MM-DD HH:MM:SS"``, or ``"now"``
            for the current time.
        models: Pre-loaded ML model tuple from
            :func:`~main_project.bike_forecast.models.forecast._load_models`.

    Returns:
        A tuple ``(results, weather_warning)`` where:

        - ``results`` is a copy of ``stations`` with ``available_bikes`` and
          ``available_stands`` overwritten by ML predictions.
        - ``weather_warning`` is ``None`` on success, or a descriptive string
          if weather data was unavailable and the internal weather model was
          used instead.
    """
    target_dt = datetime.now() if time_str == "now" else datetime.fromisoformat(time_str)

    # Fetch weather once for all stations
    weather = _fetch_nearest_weather(time_str) if time_str != "now" else None
    if weather:
        is_raining = 1 if (weather.get("rain_3h") or 0) > 0 or (weather.get("pop") or 0) >= 0.5 else 0
        wx_override = {
            "avg_temp"    : weather.get("temp"),
            "avg_humidity": weather.get("humidity"),
            "avg_pressure": weather.get("pressure"),
            "is_raining"  : is_raining,
        }
        weather_warning = None
    else:
        wx_override     = None
        weather_warning = "Could not fetch weather data; prediction used internal weather model"

    results = []
    for s in stations:
        capacity = s.get("total_stands", 0)
        pred = _predict_hour(models, s["number"], capacity, target_dt, wx_override)
        available_bikes  = max(0, min(capacity, round(pred["predicted_bikes"])))
        available_stands = capacity - available_bikes
        results.append({
            **s,
            "available_bikes" : available_bikes,
            "available_stands": available_stands,
        })

    return results, weather_warning


def get_directions(origin_lat, origin_lng, dest_lat, dest_lng, mode="bicycling") -> dict:
    """Fetch turn-by-turn directions between two coordinates via the Google Directions API.

    Args:
        origin_lat: Latitude of the origin.
        origin_lng: Longitude of the origin.
        dest_lat: Latitude of the destination.
        dest_lng: Longitude of the destination.
        mode: Travel mode — ``"bicycling"``, ``"walking"``, or ``"driving"``.
            Defaults to ``"bicycling"``.

    Returns:
        A dict with keys: ``distance_text``, ``distance_m``, ``duration_text``,
        ``duration_s``, ``polyline`` (encoded), and ``steps`` (list of dicts
        with ``instruction``, ``distance``, ``duration``).

    Raises:
        requests.HTTPError: If the API returns a non-2xx status code.
        ValueError: If the API returns no route.
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin_lat},{origin_lng}",
        "destination": f"{dest_lat},{dest_lng}",
        "mode": mode,
        "key": GOOGLE_MAPS_API_KEY,
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if data["status"] != "OK" or not data["routes"]:
        raise ValueError(f"No route found (status: {data['status']})")

    route = data["routes"][0]["legs"][0]
    return {
        "distance_text": route["distance"]["text"],
        "distance_m": route["distance"]["value"],
        "duration_text": route["duration"]["text"],
        "duration_s": route["duration"]["value"],
        "polyline": data["routes"][0]["overview_polyline"]["points"],
        "steps": [
            {
                "instruction": s["html_instructions"],
                "distance": s["distance"]["text"],
                "duration": s["duration"]["text"],
            }
            for s in route["steps"]
        ],
    }