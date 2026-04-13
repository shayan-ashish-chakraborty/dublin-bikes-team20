import math
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import text
from ..config import Config
from ..db import create_engine_for, DbConfig
from sqlalchemy.orm import sessionmaker
 
weather_db_cfg = DbConfig(
    host=Config.DB_HOST,
    port=Config.DB_PORT,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
    db_name=Config.DB_NAME_WEATHER
)
weather_engine = create_engine_for(weather_db_cfg)
WeatherSession = sessionmaker(bind=weather_engine)
 
# 5 mins cooldown for API calls 
_CACHE_TTL_SECONDS = 300
_last_api_call_time: float = 0.0
 
def hourly_forecast_rows_from_db(limit: int = 40) -> list[dict]:
    """
    Same data as GET /api/weather/db/hourly: future rows from MySQL `hourly`.
    Each dict has future_dt (usually naive datetime), temp, humidity, pressure, rain_3h, pop, …
    Returns [] on error or no rows.
    """
    limit = min(max(int(limit), 1), 100)
    try:
        # DB stores Irish time (Europe/Dublin), so compute the cutoff in Dublin time
        # rather than using MySQL's UTC_TIMESTAMP(), which would be 1 hour behind in summer.
        cutoff_dublin = (
            datetime.now(tz=ZoneInfo("Europe/Dublin")) - timedelta(hours=1)
        ).replace(tzinfo=None)
        db_session = WeatherSession()
        result = db_session.execute(
            text(
                """
                SELECT *
                FROM hourly
                WHERE future_dt >= :cutoff
                ORDER BY future_dt ASC
                LIMIT :limit
                """
            ),
            {"cutoff": cutoff_dublin, "limit": limit},
        )
        rows = [dict(row) for row in result.mappings().all()]
        db_session.close()
        return rows
    except Exception:
        return []
 
 
def _fetch_nearest_weather(dt_str: str) -> dict | None:
    """
    DB-first, OpenWeather API fallback.
    Returns the nearest hourly weather record within ±3 h of dt_str, or None.
    dt_str must be "YYYY-MM-DD HH:MM:SS".
    """
    try:
        request_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

    # Try DB
    try:
        dt_low  = request_dt - timedelta(hours=3)
        dt_high = request_dt + timedelta(hours=3)
        db_session = WeatherSession()
        result = db_session.execute(
            text("""
                SELECT *,
                       ABS(TIMESTAMPDIFF(SECOND, future_dt, :dt)) AS diff
                FROM hourly
                WHERE future_dt BETWEEN :dt_low AND :dt_high
                ORDER BY diff ASC
                LIMIT 1
            """),
            {"dt": request_dt, "dt_low": dt_low, "dt_high": dt_high}
        )
        row = result.mappings().fetchone()
        db_session.close()
        if row:
            record = dict(row)
            record.pop("diff", None)
            return record
    except Exception:
        pass

    # Fallback: OpenWeather API
    try:
        cfg = Config()
        r = requests.get(
            cfg.FORECAST_WEATHER_URI,
            params={"appid": cfg.OPENWEATHER_API_KEY, "q": cfg.CITY, "units": "metric"},
            timeout=10,
        )
        r.raise_for_status()
        raw = r.json()

        best_item, best_diff = None, None
        for item in raw.get("list", []):
            item_dt = datetime.strptime(item["dt_txt"], "%Y-%m-%d %H:%M:%S")
            diff = abs((item_dt - request_dt).total_seconds())
            if diff <= 10800 and (best_diff is None or diff < best_diff):
                best_item, best_diff = item, diff

        if best_item is None:
            return None

        now_str = datetime.now(tz=ZoneInfo("Europe/Dublin")).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "dt":         now_str,
            "future_dt":  best_item.get("dt_txt"),
            "feels_like": best_item["main"].get("feels_like"),
            "humidity":   best_item["main"].get("humidity"),
            "pop":        best_item.get("pop"),
            "pressure":   best_item["main"].get("pressure"),
            "temp":       best_item["main"].get("temp"),
            "weather_id": best_item["weather"][0]["id"] if best_item.get("weather") else None,
            "wind_speed": best_item.get("wind", {}).get("speed"),
            "wind_gust":  best_item.get("wind", {}).get("gust"),
            "rain_3h":    best_item.get("rain", {}).get("3h"),
            "snow_3h":    best_item.get("snow", {}).get("3h"),
        }
    except Exception:
        return None
 
 
# Weather forecast
def _openweather_session() -> requests.Session:
    """
    Make a requests session that ignores proxy env vars.
    This avoids surprising failures on localhost dev setups.
    """
    s = requests.Session()
    s.trust_env = False
    return s
 
 
def openweather_current(lat: float, lon: float) -> dict:
    """
    Fetch current conditions.
    Primary: live OpenWeather /data/2.5/weather API.
    Fallback: nearest hourly row from DB (Irish time).
    """
    cfg = Config()
 
    # Primary: live API
    if cfg.OPENWEATHER_API_KEY:
        try:
            s = _openweather_session()
            res = s.get(
                cfg.CURRENT_WEATHER_URI,
                params={"lat": lat, "lon": lon, "appid": cfg.OPENWEATHER_API_KEY, "units": "metric"},
                timeout=12,
            )
            res.raise_for_status()
            data = res.json()
 
            weather0 = (data.get("weather") or [{}])[0] or {}
            main = data.get("main") or {}
            wind = data.get("wind") or {}
            rain = data.get("rain") or {}
 
            return {
                "dt": data.get("dt"),  # unix seconds (UTC)
                "temp": main.get("temp"),
                "feels_like": main.get("feels_like"),
                "humidity": main.get("humidity"),
                "pressure": main.get("pressure"),
                "wind_speed": wind.get("speed"),
                "wind_gust": wind.get("gust"),
                "rain_1h": rain.get("1h"),
                "weather_desc": weather0.get("description"),
            }
        except Exception:
            pass
 
    # Fallback: nearest row from DB (stored in Irish time)
    now_dublin_str = datetime.now(tz=ZoneInfo("Europe/Dublin")).strftime("%Y-%m-%d %H:%M:%S")
    row = _fetch_nearest_weather(now_dublin_str)
    if row is not None:
        return row
 
    raise RuntimeError("openweather_current: API unavailable and no DB fallback found")
 
 
def openweather_forecast_3h_list(lat: float, lon: float, limit: int) -> list[dict]:
    """
    Free tier: GET /data/2.5/forecast (3-hour timesteps).
    Returns normalized rows.
    """
    cfg = Config()
    if not cfg.OPENWEATHER_API_KEY:
        raise ValueError("OPENWEATHER_API_KEY is not set")
 
    limit = min(int(limit), 48)
    s = _openweather_session()
    res = s.get(
        cfg.FORECAST_WEATHER_URI,
        params={"lat": lat, "lon": lon, "appid": cfg.OPENWEATHER_API_KEY, "units": "metric"},
        timeout=12,
    )
    res.raise_for_status()
    data = res.json()
 
    out: list[dict] = []
    for it in (data.get("list") or [])[:limit]:
        main = it.get("main") or {}
        wind = it.get("wind") or {}
        rain = it.get("rain") or {}
        snow = it.get("snow") or {}
        out.append(
            {
                "dt": it.get("dt"),
                "future_dt": it.get("dt"),
                "temp": main.get("temp"),
                "feels_like": main.get("feels_like"),
                "humidity": main.get("humidity"),
                "pressure": main.get("pressure"),
                "wind_speed": wind.get("speed"),
                "wind_gust": wind.get("gust"),
                "pop": it.get("pop"),
                "rain_1h": None,
                "rain_3h": rain.get("3h") if isinstance(rain, dict) else None,
                "snow_3h": snow.get("3h") if isinstance(snow, dict) else None,
            }
        )
    return out
 
 
# use for machine learning
_DUBLIN_LAT = 53.3498
_DUBLIN_LON = -6.2603
_MIN_HOURLY_ROWS = 16
 
 
def hourly_row_time_ms(row: dict) -> float | None:
    """
    Milliseconds since epoch for one forecast row (DB future_dt, OpenWeather unix dt, ISO).
    Same semantics as weather.html rowTimeMs / parseInstant.
    """
    ts = row.get("dt")
    if ts is None:
        ts = row.get("future_dt")
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        v = float(ts)
        if v < 1e11:
            return v * 1000.0
        return v
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=ZoneInfo("Europe/Dublin"))
        return ts.timestamp() * 1000.0
    if isinstance(ts, str):
        s = ts.replace("Z", "+00:00")
        try:
            d = datetime.fromisoformat(s)
            if d.tzinfo is None:
                d = d.replace(tzinfo=ZoneInfo("Europe/Dublin"))
            return d.timestamp() * 1000.0
        except ValueError:
            return None
    return None
 
 
def _filter_future_hourly_rows(rows: list[dict], now_ms: float, limit: int) -> list[dict]:
    """Same as weather.html loadHourly after primary fetch: sort, future-only, slice."""
    skew = 60_000.0
 
    def sort_key(r: dict) -> float:
        t = hourly_row_time_ms(r)
        return t if t is not None and math.isfinite(t) else 0.0
 
    sorted_rows = sorted(rows, key=sort_key)
    out = [
        r
        for r in sorted_rows
        if (t := hourly_row_time_ms(r)) is not None
        and math.isfinite(t)
        and t >= now_ms - skew
    ]
    return out[:limit]
 
 
def _merge_hourly_prefer_db(db_rows: list[dict], api_rows: list[dict], now_ms: float) -> list[dict]:
    """Same as weather.html mergeHourlyPreferDb: 3h slot, DB wins."""
    skew = 60_000.0
    slot_map: dict[int, tuple[dict, bool]] = {}
 
    def put(r: dict, from_db: bool) -> None:
        t = hourly_row_time_ms(r)
        if t is None or not math.isfinite(t) or t < now_ms - skew:
            return
        k = int(t // (3 * 60 * 60 * 1000))
        prev = slot_map.get(k)
        if prev is None:
            slot_map[k] = (r, from_db)
        elif from_db:
            slot_map[k] = (r, True)
 
    for r in api_rows or []:
        put(r, False)
    for r in db_rows or []:
        put(r, True)
 
    merged = [pair[0] for pair in slot_map.values()]
    merged.sort(key=lambda r: hourly_row_time_ms(r) or 0.0)
    return merged
 
 
def hourly_forecast_list_like_weather_page(limit: int = 24) -> list[dict]:
    """
    Single entry point: same pipeline as templates/weather.html loadHourly() —
 
      1) MySQL `hourly` (DB primary),
      2) else OpenWeather 3h forecast (live API fallback, subject to cooldown),
      3) filter to future times,
      4) if fewer than 16 rows, supplement gaps from API (DB rows win per 3h slot).
 
    Returns a list of row dicts (temp, humidity, pressure, rain_3h, pop, dt/future_dt, …).
    Use this anywhere you need the same series the weather UI uses (e.g. bike forecast).
    """
    global _last_api_call_time
 
    limit = min(max(int(limit), 1), 100)
    now_ms = time.time() * 1000.0
 
    # Primary: DB
    rows: list[dict] = hourly_forecast_rows_from_db(limit)
 
    # Fallback: live OpenWeather API
    if not rows:
        if time.time() - _last_api_call_time >= _CACHE_TTL_SECONDS:
            try:
                rows = openweather_forecast_3h_list(_DUBLIN_LAT, _DUBLIN_LON, limit)
                if rows:
                    _last_api_call_time = time.time()
            except Exception:
                rows = []
 
    if not rows:
        return []
 
    rows = _filter_future_hourly_rows(rows, now_ms, limit)
 
    # If DB was sparse, supplement with API rows; DB wins per 3h slot.
    if len(rows) < _MIN_HOURLY_ROWS:
        if time.time() - _last_api_call_time >= _CACHE_TTL_SECONDS:
            try:
                api_rows = openweather_forecast_3h_list(_DUBLIN_LAT, _DUBLIN_LON, limit)
                if api_rows:
                    _last_api_call_time = time.time()
                    rows = _merge_hourly_prefer_db(rows, api_rows, now_ms)
                    rows = _filter_future_hourly_rows(rows, now_ms, limit)
            except Exception:
                pass
 
    return rows

