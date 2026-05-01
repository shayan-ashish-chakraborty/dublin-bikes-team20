import requests
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from flask import Request

from ..config import Config
from ..weather.services import hourly_forecast_list_like_weather_page, hourly_row_time_ms


JCDECAUX_API_KEY = Config.JCDECAUX_API_KEY
JCDECAUX_CONTRACT = Config.JCDECAUX_CONTRACT
JCDECAUX_BASE_URL = Config.JCDECAUX_BASE_URL


def _forecast_row_unix_ts(row: Dict[str, Any]) -> Optional[float]:
    """Unix seconds; aligned with weather.html rowTimeMs via hourly_row_time_ms."""
    ms = hourly_row_time_ms(row)
    if ms is None:
        return None
    return ms / 1000.0


def _forecast_series_start_on_the_hour(now: datetime) -> datetime:
    """
    First timestep on a clock hour. If local time is already past :00
    (e.g. 16:14), start at the next hour (17:00), not the current hour floor (16:00).
    """
    base = now.replace(minute=0, second=0, microsecond=0)
    if now > base:
        return base + timedelta(hours=1)
    return base


def _mean_of_row_key(rows: List[Dict[str, Any]], key: str) -> Optional[float]:
    vals: List[float] = []
    for r in rows:
        v = r.get(key)
        if v is None:
            continue
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            continue
    if not vals:
        return None
    return sum(vals) / len(vals)


def _infer_is_raining_from_row(row: Dict[str, Any]) -> Optional[int]:
    """0/1 from rain_3h/pop; None only if both missing."""
    rain3 = row.get("rain_3h")
    pop = row.get("pop")
    if rain3 is not None and float(rain3) > 0.01:
        return 1
    if pop is not None and float(pop) >= 0.5:
        return 1
    if rain3 is not None or pop is not None:
        return 0
    return None


def _hourly_rows_fallback_means(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    mt = _mean_of_row_key(rows, "temp")
    mh = _mean_of_row_key(rows, "humidity")
    mp = _mean_of_row_key(rows, "pressure")
    rain_flags = [x for r in rows if (x := _infer_is_raining_from_row(r)) is not None]
    if rain_flags:
        is_rain_fb = 1 if (sum(rain_flags) / len(rain_flags)) >= 0.5 else 0
    else:
        is_rain_fb = 0
    return {
        "avg_temp": round(mt, 1) if mt is not None else 10.0,
        "avg_humidity": round(mh, 1) if mh is not None else 70.0,
        "avg_pressure": round(mp, 1) if mp is not None else 1013.0,
        "is_raining": is_rain_fb,
    }


# convert to the db/openweather formate
def _openweather_row_to_model_wx(
    row: Dict[str, Any], fallback: Dict[str, Any]
) -> Dict[str, Any]:
    """Map hourly row → model wx; null temp/humidity/pressure use series means in `fallback`."""
    t = row.get("temp")
    h = row.get("humidity")
    p = row.get("pressure")
    rain3 = row.get("rain_3h")
    pop = row.get("pop")
    if rain3 is not None and float(rain3) > 0.01:
        is_rain = 1
    elif pop is not None and float(pop) >= 0.5:
        is_rain = 1
    elif rain3 is not None or pop is not None:
        is_rain = 0
    else:
        is_rain = int(fallback["is_raining"])
    return {
        "avg_temp": round(float(t), 1) if t is not None else fallback["avg_temp"],
        "avg_humidity": round(float(h), 1) if h is not None else fallback["avg_humidity"],
        "avg_pressure": round(float(p), 1) if p is not None else fallback["avg_pressure"],
        "is_raining": int(is_rain),
    }

# convert to every 1 hour
def _pick_nearest_forecast_row(
    rows: List[Dict[str, Any]], target: datetime
) -> Optional[Dict[str, Any]]:
    target_ts = target.timestamp()
    best: Optional[Dict[str, Any]] = None
    best_d: Optional[float] = None
    for r in rows:
        ts = _forecast_row_unix_ts(r)
        if ts is None:
            continue
        d = abs(ts - target_ts)
        if best_d is None or d < best_d:
            best_d = d
            best = r
    return best

#return the weather list
def _weather_forecast_list_from_openweather(
    hours: int, now: datetime
) -> Optional[List[Dict[str, Any]]]:
    """
    Uses hourly_forecast_list_like_weather_page() — same list as the weather UI loadHourly().
    Timesteps are clock hours: from next :00 if past the hour, then +1h each.
    """
    limit = min(100, max(24, hours))
    rows = hourly_forecast_list_like_weather_page(limit=limit)
    if not rows:
        return None

    fb = _hourly_rows_fallback_means(rows)
    base = _forecast_series_start_on_the_hour(now)
    out: List[Dict[str, Any]] = []
    for i in range(hours):
        target = base + timedelta(hours=i)
        best = _pick_nearest_forecast_row(rows, target)
        if best is None:
            return None
        wx = _openweather_row_to_model_wx(best, fb)
        wx["time"] = target.strftime("%Y-%m-%d %H:%M")
        out.append(wx)
    return out


def get_all_stations() -> list:
    """Fetch all Dublin Bikes stations with live availability from the JCDecaux API.

    Returns:
        A list of raw station dicts as returned by the JCDecaux VLS v1 API.

    Raises:
        requests.HTTPError: If the API returns a non-2xx status code.
    """
    url = f"{JCDECAUX_BASE_URL}/stations"
    params = {
        "contract": JCDECAUX_CONTRACT,
        "apiKey": JCDECAUX_API_KEY,
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def get_station(station_number) -> dict:
    """Fetch a single Dublin Bikes station by its station number.

    Args:
        station_number: The integer station identifier used by JCDecaux.

    Returns:
        A raw station dict as returned by the JCDecaux VLS v1 API.

    Raises:
        requests.HTTPError: If the API returns a non-2xx status code.
    """
    url = f"{JCDECAUX_BASE_URL}/stations/{station_number}"
    params = {
        "contract": JCDECAUX_CONTRACT,
        "apiKey": JCDECAUX_API_KEY,
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def format_station(raw) -> dict:
    """Normalise a raw JCDecaux station dict into the app's station schema.

    Args:
        raw: A station dict as returned directly by the JCDecaux API,
             including a nested ``position`` key with ``lat`` and ``lng``.

    Returns:
        A dict with keys: ``number``, ``name``, ``address``, ``lat``, ``lng``,
        ``status``, ``available_bikes``, ``available_stands``, ``total_stands``.
    """
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
    }

def station_predict_from_request(request: Request) -> dict:
    """Run a multi-hour bike and dock availability prediction for one station.

    Reads query parameters from the Flask request, fetches live station data,
    builds an hourly weather series, and runs the two-stage ML pipeline in
    batch mode.

    Args:
        request: The Flask ``Request`` object. Expected query parameters:

            - ``number`` (int, required): JCDecaux station ID.
            - ``hours`` (int, optional): Forecast horizon in hours.
              Clamped to ``[1, 48]``. Defaults to ``48``.

    Returns:
        A dict with keys:

        - ``number`` (int): Station ID.
        - ``times`` (list[str]): ISO-formatted forecast timestamps.
        - ``predicted_bikes`` (list[float]): Predicted available bikes per hour.
        - ``predicted_docks`` (list[float]): Predicted available docks per hour.
        - ``predicted_temp`` (list[float]): Predicted temperature (°C).
        - ``predicted_humidity`` (list[float]): Predicted relative humidity (%).
        - ``predicted_pressure`` (list[float]): Predicted pressure (hPa).
        - ``predicted_rain`` (list[int]): Binary rain flag per hour.

    Raises:
        ValueError: If ``number`` is missing or invalid, station capacity is
            unavailable, ML models cannot be loaded, or weather data is
            unavailable.
    """
    from ..bike_forecast.models.forecast import _load_models, _predict_bike_dock_batch

    try:
        station_no = int(request.args.get("number", -1))
    except ValueError as exc:
        raise ValueError("invalid number") from exc
    if station_no < 0:
        raise ValueError("number is required")

    try:
        hours = min(max(int(request.args.get("hours", 48)), 1), 48)
    except ValueError:
        hours = 48

    raw = get_station(station_no)
    formatted = format_station(raw)
    capacity = int(formatted.get("total_stands") or 0)
    if capacity <= 0:
        raise ValueError("station capacity unavailable")

    try:
        models = _load_models()
    except Exception as exc:
        raise ValueError(f"Models could not be loaded: {exc}") from exc

    now = datetime.now()
    series_start = _forecast_series_start_on_the_hour(now)
    weather_list = _weather_forecast_list_from_openweather(hours, now)
    if weather_list is None:
        raise ValueError(
            "Weather forecast unavailable: hourly_forecast_list_like_weather_page returned "
            "no data (DB empty and OpenWeather failed — check OPENWEATHER_API_KEY / network)."
        )
    future_dts = [series_start + timedelta(hours=i) for i in range(hours)]
    wx_overrides = [
        {
            "avg_temp": weather_list[i]["avg_temp"],
            "avg_humidity": weather_list[i]["avg_humidity"],
            "avg_pressure": weather_list[i]["avg_pressure"],
            "is_raining": weather_list[i]["is_raining"],
        }
        for i in range(hours)
    ]
    predicted_bikes, predicted_docks = _predict_bike_dock_batch(
        models, station_no, capacity, future_dts, wx_overrides
    )

    out = {
        "number": station_no,
        "times": [w["time"] for w in weather_list],
        "predicted_bikes": predicted_bikes,
        "predicted_docks": predicted_docks,
        "predicted_temp": [w["avg_temp"] for w in weather_list],
        "predicted_humidity": [w["avg_humidity"] for w in weather_list],
        "predicted_pressure": [w["avg_pressure"] for w in weather_list],
        "predicted_rain": [w["is_raining"] for w in weather_list],
    }
    return out
