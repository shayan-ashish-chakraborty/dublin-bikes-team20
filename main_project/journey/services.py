import requests, math
from datetime import datetime
from ..config import Config
from ..weather.services import _fetch_nearest_weather
from ..bike_forecast.models.forecast import _predict_hour

GOOGLE_MAPS_API_KEY = Config.GOOGLE_MAPS_API_KEY


def geocode_address(address):
    """Convert an address string to (lat, lng) using Google Geocoding API."""
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


def haversine(lat1, lng1, lat2, lng2):
    """Calculate distance in meters between two lat/lng points."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearest_station(lat, lng, stations, require_bikes=False, require_stands=False, limit=3):
    """Find the nearest stations to a point, with optional availability filters."""
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
    """
    Fetch weather ONCE, then predict bike availability for all stations.

    stations : list of dicts, each must have "number" and "total_stands"
    time_str : "YYYY-MM-DD HH:MM:SS" or "now"
    models   : preloaded ML models from _load_models()

    Returns (results, weather_warning):
      results         — copies of input dicts with available_bikes / available_stands overwritten
      weather_warning — None on success, descriptive string if weather unavailable
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


def get_directions(origin_lat, origin_lng, dest_lat, dest_lng, mode="bicycling"):
    """Get directions from Google Directions API."""
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