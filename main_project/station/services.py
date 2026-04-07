import requests
from ..config import Config


JCDECAUX_API_KEY = Config.JCDECAUX_API_KEY
JCDECAUX_CONTRACT = Config.JCDECAUX_CONTRACT
JCDECAUX_BASE_URL = Config.JCDECAUX_BASE_URL


def get_all_stations():
    """Fetch all Dublin Bike stations with live availability."""
    url = f"{JCDECAUX_BASE_URL}/stations"
    params = {
        "contract": JCDECAUX_CONTRACT,
        "apiKey": JCDECAUX_API_KEY,
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def get_station(station_number):
    """Fetch a single station by number."""
    url = f"{JCDECAUX_BASE_URL}/stations/{station_number}"
    params = {
        "contract": JCDECAUX_CONTRACT,
        "apiKey": JCDECAUX_API_KEY,
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def format_station(raw):
    """Normalize a raw JCDecaux station object."""
    return {
        "number": raw.get("number"),
        "name": raw.get("name"),
        "address": raw.get("address"),
        "lat": raw["position"]["lat"],
        "lng": raw["position"]["lng"],
        "status": raw.get("status"),
        "available_bikes": raw.get("available_bikes", 0),
        "available_stands": raw.get("available_bike_stands", 0),
        "total_stands": raw.get("bike_stands", 0),
        "bike_stands": raw.get("bike_stands", 0),
    }
